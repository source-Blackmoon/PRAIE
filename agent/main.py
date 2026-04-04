import os
import asyncio
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import (
    inicializar_db, guardar_mensaje, obtener_historial,
    obtener_checkouts_pendientes, marcar_mensaje_enviado,
    CheckoutAbandonado, Mensaje, async_session,
)
from agent.providers import obtener_proveedor
from agent.carrito import (
    recibir_checkout, recibir_orden_completada,
    scheduler_carritos, construir_mensaje,
)
from agent.shopify import (
    sincronizar_checkouts, verificar_credenciales,
    listar_webhooks, registrar_webhooks, eliminar_webhook,
)
from sqlalchemy import select

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
AUTO_RESPONDER = os.getenv("AUTO_RESPONDER", "true").lower() == "true"

logging.basicConfig(level=logging.DEBUG if ENVIRONMENT == "development" else logging.INFO)
logger = logging.getLogger("agentkit")

proveedor = obtener_proveedor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await inicializar_db()
    asyncio.create_task(scheduler_carritos())
    logger.info(f"AgentKit listo — proveedor: {proveedor.__class__.__name__}")
    logger.info(f"Auto-respuesta WhatsApp: {'ACTIVA' if AUTO_RESPONDER else 'DESACTIVADA'}")
    logger.info("Scheduler de carritos abandonados activo")
    yield


app = FastAPI(title="Agente WhatsApp PRAIE — Laura", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4001", "http://localhost:4000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "agente": "Laura — PRAIE",
        "auto_responder": AUTO_RESPONDER,
    }


# ── WhatsApp webhook ───────────────────────────────────────
@app.get("/webhook")
async def webhook_verificacion(request: Request):
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    if not AUTO_RESPONDER:
        logger.debug("Auto-respuesta desactivada — mensaje ignorado")
        return {"status": "ok", "auto_responder": "disabled"}
    try:
        mensajes = await proveedor.parsear_webhook(request)
        for msg in mensajes:
            if msg.es_propio or not msg.texto:
                continue
            logger.info(f"Mensaje de {msg.telefono}: {msg.texto}")
            historial = await obtener_historial(msg.telefono)
            respuesta = await generar_respuesta(msg.texto, historial)
            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)
            await proveedor.enviar_mensaje(msg.telefono, respuesta)
            logger.info(f"Respuesta a {msg.telefono}: {respuesta[:80]}...")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Shopify webhooks ───────────────────────────────────────
@app.post("/shopify/checkout")
async def shopify_checkout(request: Request):
    return await recibir_checkout(request)


@app.post("/shopify/orden")
async def shopify_orden(request: Request):
    return await recibir_orden_completada(request)


# ── API de carritos para el dashboard ─────────────────────
@app.get("/api/carritos")
async def listar_carritos():
    """Devuelve todos los carritos para el dashboard."""
    async with async_session() as session:
        result = await session.execute(
            select(CheckoutAbandonado).order_by(CheckoutAbandonado.timestamp.desc())
        )
        carritos = result.scalars().all()
        return [
            {
                "id": c.id,
                "checkout_id": c.checkout_id,
                "telefono": c.telefono,
                "nombre": c.nombre,
                "productos": c.productos,
                "total": c.total,
                "url_carrito": c.url_carrito,
                "mensaje_enviado": c.mensaje_enviado,
                "completado": c.completado,
                "timestamp": c.timestamp.isoformat(),
            }
            for c in carritos
        ]


@app.post("/api/shopify/sync")
async def sync_shopify():
    """Sincroniza carritos abandonados directamente desde Shopify Admin API."""
    resumen = await sincronizar_checkouts()
    return {"status": "ok", **resumen}


@app.get("/api/shopify/status")
async def shopify_status():
    """Verifica que las credenciales de Shopify sean válidas."""
    return await verificar_credenciales()


@app.get("/api/shopify/webhooks")
async def get_webhooks():
    """Lista los webhooks registrados en Shopify."""
    webhooks = await listar_webhooks()
    return {"webhooks": webhooks}


@app.post("/api/shopify/webhooks/registrar")
async def post_registrar_webhooks(request: Request):
    """Registra los webhooks necesarios apuntando a base_url."""
    body = await request.json()
    base_url = body.get("base_url", "").strip()
    if not base_url:
        raise HTTPException(status_code=400, detail="Se requiere base_url")
    resultado = await registrar_webhooks(base_url)
    return {"status": "ok", **resultado}


@app.delete("/api/shopify/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: int):
    """Elimina un webhook por ID."""
    ok = await eliminar_webhook(webhook_id)
    if not ok:
        raise HTTPException(status_code=500, detail="No se pudo eliminar el webhook")
    return {"status": "ok"}


@app.post("/api/carritos/{checkout_id}/enviar")
async def enviar_carrito_manual(checkout_id: str):
    """Envía el mensaje de recuperación manualmente desde el dashboard."""
    async with async_session() as session:
        result = await session.execute(
            select(CheckoutAbandonado).where(CheckoutAbandonado.checkout_id == checkout_id)
        )
        checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(status_code=404, detail="Carrito no encontrado")

    if checkout.completado:
        raise HTTPException(status_code=400, detail="El carrito ya fue completado (cliente pagó)")

    mensaje = construir_mensaje(
        checkout.nombre, checkout.productos,
        checkout.total, checkout.url_carrito,
    )
    enviado = await proveedor.enviar_mensaje(checkout.telefono, mensaje)

    if enviado:
        await marcar_mensaje_enviado(checkout_id)
        logger.info(f"Mensaje manual enviado a {checkout.telefono}")
        return {"status": "ok", "mensaje": mensaje}
    else:
        raise HTTPException(status_code=500, detail="Error al enviar el mensaje por WhatsApp")


# ── API del dashboard Next.js ──────────────────────────────

SEÑALES_PROBLEMA = [
    "no tengo esa información", "déjame consultarlo",
    "no entendí", "problemas técnicos", "no sé", "disculpa",
]


@app.get("/api/metricas")
async def get_metricas(dias: int = 7):
    """Métricas del dashboard: KPIs, mensajes por día, alertas y conversión de carritos."""
    limite = datetime.utcnow() - timedelta(days=dias)
    async with async_session() as session:
        result = await session.execute(
            select(Mensaje).where(Mensaje.timestamp >= limite)
        )
        mensajes = result.scalars().all()

        result_carritos = await session.execute(select(CheckoutAbandonado))
        carritos = result_carritos.scalars().all()

    # Métricas de mensajes
    if not mensajes:
        conversaciones = 0
        clientas = 0
        total_mensajes = 0
        tasa_problema = 0
        mensajes_por_dia: list = []
        alertas: list = []
    else:
        asistente = [m for m in mensajes if m.role == "assistant"]
        problemas = [m for m in asistente if any(s in m.content.lower() for s in SEÑALES_PROBLEMA)]
        tasa_problema = round(len(problemas) / len(asistente) * 100) if asistente else 0
        por_dia: dict = defaultdict(int)
        for m in mensajes:
            por_dia[m.timestamp.strftime("%Y-%m-%d")] += 1
        conversaciones = len({f"{m.telefono}-{m.timestamp.date()}" for m in mensajes})
        clientas = len({m.telefono for m in mensajes})
        total_mensajes = len(mensajes)
        mensajes_por_dia = [{"fecha": k, "mensajes": v} for k, v in sorted(por_dia.items())]
        alertas = [
            {"timestamp": m.timestamp.isoformat(), "content": m.content[:200]}
            for m in sorted(problemas, key=lambda x: x.timestamp, reverse=True)[:5]
        ]

    # Métricas de conversión de carritos
    carritos_enviados = sum(1 for c in carritos if c.mensaje_enviado)
    carritos_recuperados = sum(1 for c in carritos if c.completado)
    tasa_recuperacion = round(carritos_recuperados / carritos_enviados * 100) if carritos_enviados else 0

    def _parse_total(t: str) -> float:
        try:
            return float(t.replace("$", "").replace(".", "").replace(",", ".").split()[0])
        except Exception:
            return 0.0

    valor_recuperado = sum(_parse_total(c.total) for c in carritos if c.completado)
    valor_pendiente = sum(_parse_total(c.total) for c in carritos if c.mensaje_enviado and not c.completado)

    return {
        "conversaciones": conversaciones,
        "clientas": clientas,
        "mensajes": total_mensajes,
        "tasa_problema": tasa_problema,
        "mensajes_por_dia": mensajes_por_dia,
        "alertas": alertas,
        "carritos_enviados": carritos_enviados,
        "carritos_recuperados": carritos_recuperados,
        "tasa_recuperacion": tasa_recuperacion,
        "valor_recuperado": valor_recuperado,
        "valor_pendiente": valor_pendiente,
    }


@app.get("/api/conversaciones")
async def get_conversaciones(dias: int = 7):
    """Lista de conversaciones con preview para el panel izquierdo."""
    limite = datetime.utcnow() - timedelta(days=dias)
    async with async_session() as session:
        result = await session.execute(
            select(Mensaje).where(Mensaje.timestamp >= limite).order_by(Mensaje.timestamp)
        )
        mensajes = result.scalars().all()

    conv: dict = defaultdict(list)
    for m in mensajes:
        conv[m.telefono].append(m)

    conversaciones = [
        {
            "telefono": telefono,
            "mensajes": len(msgs),
            "ultimo": max(m.timestamp for m in msgs).isoformat(),
            "preview": next((m.content for m in msgs if m.role == "user"), "")[:80],
        }
        for telefono, msgs in conv.items()
    ]
    return sorted(conversaciones, key=lambda x: x["ultimo"], reverse=True)


@app.get("/api/conversaciones/{telefono}")
async def get_mensajes_conversacion(telefono: str):
    """Todos los mensajes de una conversación específica."""
    async with async_session() as session:
        result = await session.execute(
            select(Mensaje).where(Mensaje.telefono == telefono).order_by(Mensaje.timestamp)
        )
        mensajes = result.scalars().all()

    return [
        {"id": m.id, "role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
        for m in mensajes
    ]


@app.get("/api/knowledge")
async def list_knowledge():
    """Lista archivos del knowledge base con su contenido."""
    knowledge_dir = Path("knowledge")
    files = []
    for f in sorted(knowledge_dir.glob("*.txt")):
        files.append({
            "name": f.name, "path": str(f),
            "size": f.stat().st_size, "content": f.read_text(encoding="utf-8"),
        })
    prompts = Path("config/prompts.yaml")
    if prompts.exists():
        files.append({
            "name": prompts.name, "path": str(prompts),
            "size": prompts.stat().st_size, "content": prompts.read_text(encoding="utf-8"),
        })
    return files


@app.put("/api/knowledge/{filename}")
async def update_knowledge(filename: str, request: Request):
    """Actualiza el contenido de un archivo del knowledge base."""
    body = await request.json()
    content = body.get("content", "")
    for candidate in [Path("knowledge") / filename, Path("config") / filename]:
        if candidate.exists():
            candidate.write_text(content, encoding="utf-8")
            return {"status": "ok", "file": filename}
    raise HTTPException(status_code=404, detail="Archivo no encontrado")
