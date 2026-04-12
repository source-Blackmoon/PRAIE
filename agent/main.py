import os
import asyncio
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import (
    inicializar_db, guardar_mensaje, obtener_historial,
    obtener_checkouts_pendientes, marcar_mensaje_enviado,
    CheckoutAbandonado, Mensaje, Conversion, Escalacion, async_session,
    obtener_conversiones, obtener_config, guardar_config,
    registrar_evento_funnel, TipoEventoFunnel, MetadataEvento,
    obtener_funnel, crear_escalacion, obtener_escalaciones, resolver_escalacion,
    obtener_tests_ab, crear_test_ab, pausar_test_ab, obtener_resultados_ab,
)
from agent.providers import obtener_proveedor
from agent.carrito import (
    recibir_checkout, recibir_orden_completada,
    scheduler_carritos, construir_mensaje,
    TEMPLATE_CARRITO_KEY, TEMPLATE_CARRITO_DEFAULT,
)
from agent.shopify import (
    sincronizar_checkouts, verificar_credenciales,
    listar_webhooks, registrar_webhooks, eliminar_webhook,
)
from sqlalchemy import select

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
AUTO_RESPONDER = os.getenv("AUTO_RESPONDER", "true").lower() == "true"
API_KEY = os.getenv("API_KEY", "")


def verificar_api_key(x_api_key: str = Header(default="")):
    """Protege los endpoints de administración con una API key."""
    if not API_KEY:
        if ENVIRONMENT == "production":
            raise HTTPException(status_code=500, detail="API_KEY no configurada en producción")
        return  # En desarrollo se acepta sin key
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")

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
    # Advertencias de configuración en producción
    if ENVIRONMENT == "production":
        db_url = os.getenv("DATABASE_URL", "")
        if "sqlite" in db_url or not db_url:
            logger.warning(
                "ADVERTENCIA: Usando SQLite en producción. "
                "Los datos se perderán al redesplegar. "
                "Configura DATABASE_URL con PostgreSQL en Railway."
            )
        if not API_KEY:
            logger.warning(
                "ADVERTENCIA: API_KEY no configurada. "
                "Los endpoints de administración están desprotegidos."
            )
        if not os.getenv("ANTHROPIC_API_KEY"):
            logger.error("ANTHROPIC_API_KEY no configurada — el agente no puede responder.")
    yield


app = FastAPI(title="Agente WhatsApp PRAIE — Laura", version="1.0.0", lifespan=lifespan)

CORS_ORIGINS = [
    "http://localhost:4001",
    "http://localhost:4000",
    "https://praie-front-production.up.railway.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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


async def _procesar_mensaje(telefono: str, texto: str, historial: list):
    """Procesa el mensaje y envía la respuesta en background."""
    try:
        await guardar_mensaje(telefono, "user", texto)
        # Funnel: registrar mensaje recibido
        await registrar_evento_funnel(telefono, TipoEventoFunnel.MENSAJE_RECIBIDO)
        respuesta = await generar_respuesta(texto, historial, telefono)
        await guardar_mensaje(telefono, "assistant", respuesta)
        ok = await proveedor.enviar_mensaje(telefono, respuesta)
        if ok:
            logger.info(f"Respuesta enviada a {telefono}: {respuesta[:80]}...")
        else:
            logger.error(f"Fallo al enviar respuesta a {telefono}")
    except Exception as e:
        logger.error(f"Error procesando mensaje de {telefono}: {e}")


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
            # Retornar 200 a Twilio/Whapi inmediatamente y procesar en background
            # Evita timeout del proveedor cuando el tool_use toma >5s
            asyncio.create_task(_procesar_mensaje(msg.telefono, msg.texto, historial))
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Shopify OAuth ─────────────────────────────────────────
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "")
SHOPIFY_OAUTH_SCOPES = "read_products,read_orders,write_webhooks,read_webhooks"
SHOPIFY_REDIRECT_URI = "https://praie-production.up.railway.app/shopify/oauth/callback"


@app.get("/shopify/oauth/install")
async def shopify_oauth_install(shop: str = "f0315f.myshopify.com"):
    """Inicia el flujo OAuth — abre esto en el browser para obtener un token nuevo."""
    from fastapi.responses import RedirectResponse
    url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={SHOPIFY_CLIENT_ID}"
        f"&scope={SHOPIFY_OAUTH_SCOPES}"
        f"&redirect_uri={SHOPIFY_REDIRECT_URI}"
        f"&state=praie-oauth"
    )
    return RedirectResponse(url)


@app.get("/shopify/oauth/callback")
async def shopify_oauth_callback(code: str, shop: str, state: str = ""):
    """Recibe el código OAuth y lo intercambia por un access token."""
    import httpx
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": SHOPIFY_CLIENT_ID,
                "client_secret": SHOPIFY_CLIENT_SECRET,
                "code": code,
            },
        )
    data = r.json()
    token = data.get("access_token", "")
    scope = data.get("scope", "")
    logger.info(f"OAuth Shopify — nuevo token obtenido, scopes: {scope}")
    return {
        "instruccion": "Copia este token en Railway como SHOPIFY_ACCESS_TOKEN",
        "access_token": token,
        "scope": scope,
        "shop": shop,
    }


# ── Shopify webhooks ───────────────────────────────────────
@app.post("/shopify/checkout")
async def shopify_checkout(request: Request):
    return await recibir_checkout(request)


@app.post("/shopify/orden")
async def shopify_orden(request: Request):
    return await recibir_orden_completada(request)


# ── API de carritos para el dashboard ─────────────────────
@app.get("/api/carritos")
async def listar_carritos(_: None = Depends(verificar_api_key)):
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
async def sync_shopify(_: None = Depends(verificar_api_key)):
    """Sincroniza carritos abandonados directamente desde Shopify Admin API."""
    resumen = await sincronizar_checkouts()
    return {"status": "ok", **resumen}


@app.get("/api/shopify/status")
async def shopify_status(_: None = Depends(verificar_api_key)):
    """Verifica que las credenciales de Shopify sean válidas."""
    return await verificar_credenciales()


@app.get("/api/shopify/test-productos")
async def test_productos(q: str = "", _: None = Depends(verificar_api_key)):
    """Prueba búsqueda de productos en Shopify. Sin q= trae los primeros 5."""
    from agent.shopify import buscar_productos_shopify
    productos = await buscar_productos_shopify(q, limit=5)
    return {"query": q, "total": len(productos), "productos": productos}


@app.get("/api/shopify/webhooks")
async def get_webhooks(_: None = Depends(verificar_api_key)):
    """Lista los webhooks registrados en Shopify."""
    webhooks = await listar_webhooks()
    return {"webhooks": webhooks}


@app.post("/api/shopify/webhooks/registrar")
async def post_registrar_webhooks(request: Request, _: None = Depends(verificar_api_key)):
    """Registra los webhooks necesarios apuntando a base_url."""
    body = await request.json()
    base_url = body.get("base_url", "").strip()
    if not base_url:
        raise HTTPException(status_code=400, detail="Se requiere base_url")
    resultado = await registrar_webhooks(base_url)
    return {"status": "ok", **resultado}


@app.delete("/api/shopify/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: int, _: None = Depends(verificar_api_key)):
    """Elimina un webhook por ID."""
    ok = await eliminar_webhook(webhook_id)
    if not ok:
        raise HTTPException(status_code=500, detail="No se pudo eliminar el webhook")
    return {"status": "ok"}


@app.post("/api/carritos/{checkout_id}/enviar")
async def enviar_carrito_manual(checkout_id: str, _: None = Depends(verificar_api_key)):
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

    mensaje = await construir_mensaje(
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


# ── Mensaje de carrito abandonado ─────────────────────────
@app.get("/api/carritos/mensaje")
async def get_mensaje_carrito(_: None = Depends(verificar_api_key)):
    """Devuelve el template del mensaje de carrito abandonado y un preview de ejemplo."""
    template = await obtener_config(TEMPLATE_CARRITO_KEY, TEMPLATE_CARRITO_DEFAULT)
    preview = template.format(
        nombre="María",
        productos="Vestido de baño talla M (x1)",
        total="$150.000 COP",
        total_str=" por $150.000 COP",
        url_carrito="https://praie.co/checkout/abc123",
    )
    return {
        "template": template,
        "preview": preview,
        "variables": ["{nombre}", "{productos}", "{total}", "{total_str}", "{url_carrito}"],
        "descripcion_variables": {
            "{nombre}": "Nombre del cliente (ej: María)",
            "{productos}": "Productos dejados en el carrito",
            "{total}": "Total del carrito (ej: $150.000 COP) — vacío si no hay",
            "{total_str}": "Total con prefijo ' por ' (ej: ' por $150.000 COP') — vacío si no hay",
            "{url_carrito}": "Enlace para completar la compra",
        },
    }


@app.put("/api/carritos/mensaje")
async def update_mensaje_carrito(request: Request, _: None = Depends(verificar_api_key)):
    """Actualiza el template del mensaje de carrito abandonado."""
    body = await request.json()
    template = body.get("template", "").strip()
    if not template:
        raise HTTPException(status_code=400, detail="El template no puede estar vacío")
    if "{url_carrito}" not in template:
        raise HTTPException(status_code=400, detail="El template debe contener {url_carrito}")
    # Validar que el template no tenga variables desconocidas (format_map con SafeDict)
    try:
        template.format(
            nombre="test", productos="test", total="test",
            total_str="test", url_carrito="test",
        )
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Variable desconocida en el template: {e}")
    await guardar_config(TEMPLATE_CARRITO_KEY, template)
    preview = template.format(
        nombre="María",
        productos="Vestido de baño talla M (x1)",
        total="$150.000 COP",
        total_str=" por $150.000 COP",
        url_carrito="https://praie.co/checkout/abc123",
    )
    return {"status": "ok", "preview": preview}


# ── API del dashboard Next.js ──────────────────────────────

SEÑALES_PROBLEMA = [
    "no tengo esa información", "déjame consultarlo",
    "no entendí", "problemas técnicos", "no sé", "disculpa",
]


@app.get("/api/metricas")
async def get_metricas(dias: int = 7, _: None = Depends(verificar_api_key)):
    """Métricas del dashboard: KPIs, mensajes por día, alertas y conversión de carritos."""
    limite = datetime.utcnow() - timedelta(days=dias)
    async with async_session() as session:
        result = await session.execute(
            select(Mensaje).where(Mensaje.timestamp >= limite)
        )
        mensajes = result.scalars().all()

        result_carritos = await session.execute(select(CheckoutAbandonado))
        carritos = result_carritos.scalars().all()

        result_conv = await session.execute(
            select(Conversion).where(Conversion.timestamp >= limite)
        )
        conversiones = result_conv.scalars().all()

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

    ventas_por_chat = sum(1 for c in conversiones if c.fuente in ("chat", "ambos"))
    ventas_por_carrito = sum(1 for c in conversiones if c.fuente in ("carrito", "ambos"))

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
        "ventas_cerradas_total": len(conversiones),
        "ventas_por_chat": ventas_por_chat,
        "ventas_por_carrito": ventas_por_carrito,
    }


@app.get("/api/conversaciones")
async def get_conversaciones(dias: int = 7, _: None = Depends(verificar_api_key)):
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
async def get_mensajes_conversacion(telefono: str, _: None = Depends(verificar_api_key)):
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


@app.get("/api/conversiones")
async def get_conversiones(dias: int = 30, _: None = Depends(verificar_api_key)):
    """Lista de ventas cerradas atribuidas a conversaciones con Laura."""
    conversiones = await obtener_conversiones(dias)
    return [
        {
            "id": c.id,
            "telefono": c.telefono,
            "order_id": c.order_id,
            "order_total": c.order_total,
            "productos": c.productos,
            "fuente": c.fuente,
            "dias_desde_chat": c.dias_desde_chat,
            "timestamp": c.timestamp.isoformat(),
        }
        for c in conversiones
    ]


# ── API Funnel Analytics ──────────────────────────────────
@app.get("/api/funnel")
async def get_funnel(dias: int = 7, _: None = Depends(verificar_api_key)):
    """Retorna el funnel de conversion: mensajes → productos → carritos → compras."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    funnel = await obtener_funnel(fecha_inicio, fecha_fin)
    return funnel


# ── API Escalaciones ─────────────────────────────────────
@app.get("/api/escalaciones")
async def get_escalaciones(estado: str | None = None, _: None = Depends(verificar_api_key)):
    """Lista escalaciones, opcionalmente filtradas por estado (pendiente/resuelta)."""
    escalaciones = await obtener_escalaciones(estado)
    return [
        {
            "id": e.id,
            "telefono": e.telefono,
            "razon": e.razon,
            "resumen": e.resumen,
            "estado": e.estado,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in escalaciones
    ]


@app.put("/api/escalaciones/{escalacion_id}/resolver")
async def put_resolver_escalacion(escalacion_id: int, _: None = Depends(verificar_api_key)):
    """Marca una escalacion como resuelta."""
    ok = await resolver_escalacion(escalacion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Escalacion no encontrada")
    return {"status": "ok"}


# ── A/B Testing ──────────────────────────────────────────

@app.get("/api/ab-tests")
async def get_ab_tests(_: None = Depends(verificar_api_key)):
    """Lista todos los tests A/B."""
    tests = await obtener_tests_ab()
    resultado = []
    for t in tests:
        stats = await obtener_resultados_ab(t.id)
        resultado.append({
            "id": t.id,
            "nombre": t.nombre,
            "variante_a": t.variante_a,
            "variante_b": t.variante_b,
            "activo": t.activo,
            "fecha_inicio": t.fecha_inicio.isoformat(),
            **stats,
        })
    return resultado


@app.post("/api/ab-tests")
async def post_crear_ab_test(request: Request, _: None = Depends(verificar_api_key)):
    """Crea un nuevo test A/B. Desactiva el test activo previo."""
    body = await request.json()
    nombre = body.get("nombre", "")
    variante_a = body.get("variante_a", "")
    variante_b = body.get("variante_b", "")
    if not nombre or not variante_a or not variante_b:
        raise HTTPException(status_code=400, detail="nombre, variante_a y variante_b son requeridos")
    test = await crear_test_ab(nombre, variante_a, variante_b)
    return {"status": "ok", "id": test.id}


@app.put("/api/ab-tests/{test_id}/pausar")
async def put_pausar_ab_test(test_id: int, _: None = Depends(verificar_api_key)):
    """Pausa un test A/B activo."""
    ok = await pausar_test_ab(test_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Test no encontrado")
    return {"status": "ok"}


@app.get("/api/knowledge")
async def list_knowledge(_: None = Depends(verificar_api_key)):
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
async def update_knowledge(filename: str, request: Request, _: None = Depends(verificar_api_key)):
    """Actualiza el contenido de un archivo del knowledge base."""
    body = await request.json()
    content = body.get("content", "")
    for candidate in [Path("knowledge") / filename, Path("config") / filename]:
        if candidate.exists():
            candidate.write_text(content, encoding="utf-8")
            return {"status": "ok", "file": filename}
    raise HTTPException(status_code=404, detail="Archivo no encontrado")
