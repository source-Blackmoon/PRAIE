"""
Módulo de recuperación de carritos abandonados — PRAIE
Recibe webhooks de Shopify y envía mensajes WhatsApp proactivos via Whapi.
"""

import os
import logging
import asyncio
import hashlib
import hmac
import base64
from datetime import datetime

import httpx
from fastapi import Request, HTTPException

from agent.memory import (
    guardar_checkout, obtener_checkouts_pendientes,
    marcar_mensaje_enviado, marcar_checkout_completado,
    tuvo_conversacion_reciente, registrar_conversion,
)
from agent.providers import obtener_proveedor

logger = logging.getLogger("agentkit.carrito")

MINUTOS_ESPERA = int(os.getenv("CARRITO_ESPERA_MINUTOS", "60"))
SHOPIFY_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")


# ── Verificación HMAC de Shopify ───────────────────────────
def verificar_shopify_hmac(body: bytes, hmac_header: str) -> bool:
    if not SHOPIFY_SECRET:
        if os.getenv("ENVIRONMENT", "development") == "production":
            logger.warning("SHOPIFY_WEBHOOK_SECRET no configurado — verificación HMAC desactivada en producción")
        return True  # Sin secret configurado → aceptar en desarrollo
    digest = hmac.new(
        SHOPIFY_SECRET.encode("utf-8"), body, hashlib.sha256
    ).digest()
    calculado = base64.b64encode(digest).decode()
    return hmac.compare_digest(calculado, hmac_header or "")


# ── Parsear checkout de Shopify ────────────────────────────
def extraer_datos_checkout(payload: dict) -> dict | None:
    """Extrae los datos relevantes del payload de Shopify."""
    checkout = payload.get("checkout", payload)  # checkouts/create envuelve en "checkout"

    # Teléfono — intentar varios campos
    telefono = (
        checkout.get("phone") or
        checkout.get("billing_address", {}).get("phone") or
        checkout.get("shipping_address", {}).get("phone") or
        (checkout.get("customer") or {}).get("phone") or ""
    )

    if not telefono:
        logger.info("Checkout sin teléfono — no se puede enviar WhatsApp")
        return None

    # Limpiar teléfono: solo dígitos, agregar código Colombia si falta
    telefono_limpio = "".join(filter(str.isdigit, telefono))
    if len(telefono_limpio) == 10 and telefono_limpio.startswith("3"):
        telefono_limpio = "57" + telefono_limpio  # Agregar código de Colombia

    # Nombre del cliente
    nombre = (
        checkout.get("customer", {}).get("first_name") or
        checkout.get("billing_address", {}).get("first_name") or
        "amiga"
    )

    # Productos
    items = checkout.get("line_items", [])
    productos = ", ".join(
        f"{item.get('title', 'producto')} (x{item.get('quantity', 1)})"
        for item in items[:3]
    )
    if not productos:
        productos = "tu vestido de baño"

    # Total
    total = checkout.get("total_price", "")
    if total:
        try:
            total = f"${float(total):,.0f} COP"
        except Exception:
            pass

    # URL del carrito
    url_carrito = checkout.get("abandoned_checkout_url") or checkout.get("cart_token", "")
    if not url_carrito.startswith("http"):
        url_carrito = f"https://praie.co/checkout"

    return {
        "checkout_id": str(checkout.get("id", checkout.get("token", ""))),
        "telefono": telefono_limpio,
        "nombre": nombre,
        "productos": productos,
        "total": total,
        "url_carrito": url_carrito,
    }


# ── Construir el mensaje de recuperación ──────────────────
def construir_mensaje(nombre: str, productos: str, total: str, url_carrito: str) -> str:
    nombre_str = nombre.capitalize() if nombre != "amiga" else "amiga"
    total_str = f" por {total}" if total else ""

    return (
        f"¡Hola {nombre_str}! 👋\n\n"
        f"Vimos que dejaste {productos} en tu carrito de PRAIE{total_str} ♡\n\n"
        f"¿Tienes alguna duda sobre la talla, el color o el envío? "
        f"Aquí estoy para ayudarte 😊\n\n"
        f"👉 Completa tu compra aquí:\n{url_carrito}\n\n"
        f"Recuerda que puedes pagar contraentrega — "
        f"recibes primero y pagas cuando llegue ♡"
    )


# ── Handler del webhook de Shopify ────────────────────────
async def recibir_checkout(request: Request):
    """Endpoint POST /shopify/checkout — recibe checkouts de Shopify."""
    body = await request.body()

    # Verificar HMAC solo en producción
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    environment = os.getenv("ENVIRONMENT", "development")
    if SHOPIFY_SECRET and environment == "production" and not verificar_shopify_hmac(body, hmac_header):
        raise HTTPException(status_code=401, detail="HMAC inválido")

    payload = await request.json() if not body else __import__("json").loads(body)
    datos = extraer_datos_checkout(payload)

    if not datos:
        return {"status": "sin_telefono"}

    await guardar_checkout(**datos)
    logger.info(f"Checkout guardado: {datos['checkout_id']} — {datos['telefono']}")
    return {"status": "ok", "checkout_id": datos["checkout_id"]}


async def recibir_orden_completada(request: Request):
    """Endpoint POST /shopify/orden — marca checkout como completado y registra conversión."""
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    environment = os.getenv("ENVIRONMENT", "development")
    if SHOPIFY_SECRET and environment == "production" and not verificar_shopify_hmac(body, hmac_header):
        raise HTTPException(status_code=401, detail="HMAC inválido")

    payload = __import__("json").loads(body)

    # Marcar el carrito abandonado como completado
    checkout_token = (
        payload.get("checkout_token") or
        payload.get("order", {}).get("checkout_token", "")
    )
    if checkout_token:
        await marcar_checkout_completado(checkout_token)
        logger.info(f"Orden completada — checkout {checkout_token} marcado")

    # Extraer datos de la orden para rastrear conversión
    order = payload if "line_items" in payload else payload.get("order", payload)
    order_id = str(order.get("id", ""))

    telefono = (
        order.get("phone") or
        (order.get("billing_address") or {}).get("phone") or
        (order.get("shipping_address") or {}).get("phone") or
        (order.get("customer") or {}).get("phone") or ""
    )
    telefono = "".join(filter(str.isdigit, telefono))
    if len(telefono) == 10 and telefono.startswith("3"):
        telefono = "57" + telefono

    if order_id and telefono:
        # Verificar si hubo conversación con Laura en los últimos 7 días
        dias = await tuvo_conversacion_reciente(telefono, dias=7)
        tuvo_carrito = bool(checkout_token)
        fuente = "ambos" if (dias >= 0 and tuvo_carrito) else ("chat" if dias >= 0 else "carrito")

        if dias >= 0 or tuvo_carrito:
            items = order.get("line_items", [])
            productos = ", ".join(
                f"{it.get('title', 'producto')} (x{it.get('quantity', 1)})"
                for it in items[:3]
            )
            total = order.get("total_price", "")
            try:
                total = f"${float(total):,.0f} COP".replace(",", ".")
            except Exception:
                pass

            await registrar_conversion(
                telefono=telefono,
                order_id=order_id,
                order_total=total,
                productos=productos,
                fuente=fuente,
                dias_desde_chat=max(dias, 0),
            )
            logger.info(f"Conversión registrada — orden {order_id} | teléfono {telefono} | fuente: {fuente}")

    return {"status": "ok"}


# ── Scheduler: revisar carritos cada 15 minutos ───────────
async def scheduler_carritos():
    """Tarea de fondo que revisa y envía mensajes de recuperación."""
    proveedor = obtener_proveedor()
    logger.info("Scheduler de carritos abandonados iniciado")

    while True:
        try:
            pendientes = await obtener_checkouts_pendientes(MINUTOS_ESPERA)
            if pendientes:
                logger.info(f"Carritos abandonados a procesar: {len(pendientes)}")

            for checkout in pendientes:
                mensaje = construir_mensaje(
                    checkout.nombre, checkout.productos,
                    checkout.total, checkout.url_carrito,
                )
                enviado = await proveedor.enviar_mensaje(checkout.telefono, mensaje)

                if enviado:
                    await marcar_mensaje_enviado(checkout.checkout_id)
                    logger.info(f"Mensaje carrito enviado a {checkout.telefono}")
                else:
                    logger.error(f"Fallo al enviar a {checkout.telefono}")

        except Exception as e:
            logger.error(f"Error en scheduler de carritos: {e}")
        await asyncio.sleep(15 * 60)  # Esperar 15 minutos antes del siguiente ciclo
