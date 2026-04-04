"""
Simulador de webhooks de Shopify — Desarrollo local
Simula un carrito abandonado sin necesitar cuenta de Shopify.

Uso:
    python tools/simular_shopify.py                        ← crea carrito abandonado
    python tools/simular_shopify.py --telefono 573001234567
    python tools/simular_shopify.py --orden               ← simula orden completada
    python tools/simular_shopify.py --enviar-ahora        ← fuerza envío sin esperar 1h
"""

import asyncio
import sys
import os
import argparse
import json
import httpx
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SERVER_URL = "http://localhost:8000"

CHECKOUT_SIMULADO = {
    "checkout": {
        "id": 99991234,
        "token": "test-checkout-praie-001",
        "abandoned_checkout_url": "https://praie.co/checkout/recover/test-token-001",
        "phone": None,           # Se reemplaza con --telefono
        "customer": {
            "first_name": "Ana",
            "last_name": "García",
            "phone": None,        # Se reemplaza con --telefono
            "email": "ana@test.com",
        },
        "billing_address": {
            "first_name": "Ana",
            "phone": None,
        },
        "line_items": [
            {
                "title": "Enterizo Control Abdomen Negro",
                "quantity": 1,
                "price": "174900.00",
                "variant_title": "Talla M",
            }
        ],
        "total_price": "174900.00",
        "currency": "COP",
        "created_at": datetime.utcnow().isoformat(),
    }
}

ORDEN_SIMULADA = {
    "checkout_token": "test-checkout-praie-001",
    "order": {
        "id": 88881234,
        "checkout_token": "test-checkout-praie-001",
        "total_price": "174900.00",
    }
}


async def simular_checkout_abandonado(telefono: str):
    payload = json.loads(json.dumps(CHECKOUT_SIMULADO))
    payload["checkout"]["phone"] = telefono
    payload["checkout"]["customer"]["phone"] = telefono
    payload["checkout"]["billing_address"]["phone"] = telefono

    print(f"\n{'='*55}")
    print("  Simulando checkout abandonado de Shopify...")
    print(f"  Teléfono: {telefono}")
    print(f"  Producto: Enterizo Control Abdomen Negro — Talla M")
    print(f"  Total:    $174.900 COP")
    print(f"{'='*55}")

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{SERVER_URL}/shopify/checkout",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

    if r.status_code == 200:
        data = r.json()
        print(f"\n  ✅ Checkout guardado en la base de datos")
        print(f"  ID: {data.get('checkout_id', 'N/A')}")
        print(f"\n  ⏱️  El mensaje se enviará en {os.getenv('CARRITO_ESPERA_MINUTOS', 60)} minutos.")
        print(f"  Para enviarlo AHORA ejecuta:")
        print(f"  python tools/simular_shopify.py --enviar-ahora --telefono {telefono}")
    else:
        print(f"\n  ❌ Error {r.status_code}: {r.text}")


async def simular_orden_completada():
    print(f"\n{'='*55}")
    print("  Simulando orden completada (pago recibido)...")
    print(f"{'='*55}")

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{SERVER_URL}/shopify/orden",
            json=ORDEN_SIMULADA,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

    if r.status_code == 200:
        print(f"\n  ✅ Checkout marcado como completado")
        print(f"  Laura NO enviará mensaje de recuperación para este carrito.")
    else:
        print(f"\n  ❌ Error {r.status_code}: {r.text}")


async def enviar_ahora(telefono: str):
    """Fuerza el envío inmediato sin esperar la hora."""
    from dotenv import load_dotenv
    load_dotenv()

    from agent.memory import (
        inicializar_db, guardar_checkout,
        obtener_checkouts_pendientes, marcar_mensaje_enviado,
    )
    from agent.carrito import construir_mensaje
    from agent.providers import obtener_proveedor

    await inicializar_db()

    # Guardar el checkout con timestamp en el pasado (hace 2 horas)
    from datetime import timedelta
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import update
    from agent.memory import CheckoutAbandonado, engine, async_session

    checkout_id = "test-checkout-praie-001"

    await guardar_checkout(
        checkout_id=checkout_id,
        telefono=telefono,
        nombre="Ana",
        productos="Enterizo Control Abdomen Negro (x1)",
        total="$174.900 COP",
        url_carrito="https://praie.co/checkout/recover/test-token-001",
    )

    # Retrasar el timestamp para que el scheduler lo detecte
    async with async_session() as session:
        await session.execute(
            update(CheckoutAbandonado)
            .where(CheckoutAbandonado.checkout_id == checkout_id)
            .values(timestamp=datetime.utcnow() - timedelta(hours=2))
        )
        await session.commit()

    pendientes = await obtener_checkouts_pendientes(minutos_espera=1)
    checkout = next((c for c in pendientes if c.checkout_id == checkout_id), None)

    if not checkout:
        print("\n  ❌ No se encontró el checkout. Verifica que el ID sea correcto.")
        return

    mensaje = construir_mensaje(
        checkout.nombre, checkout.productos,
        checkout.total, checkout.url_carrito,
    )

    print(f"\n{'='*55}")
    print("  Enviando mensaje de recuperación AHORA...")
    print(f"  Teléfono: {telefono}")
    print(f"\n  Mensaje que recibirá la clienta:")
    print(f"  {'-'*40}")
    print(f"  {mensaje}")
    print(f"  {'-'*40}")

    proveedor = obtener_proveedor()
    enviado = await proveedor.enviar_mensaje(telefono, mensaje)

    if enviado:
        await marcar_mensaje_enviado(checkout_id)
        print(f"\n  ✅ Mensaje enviado exitosamente por WhatsApp")
    else:
        print(f"\n  ❌ Error al enviar. Verifica WHAPI_TOKEN y que el número esté conectado.")


async def main():
    parser = argparse.ArgumentParser(description="Simulador de Shopify — PRAIE")
    parser.add_argument("--telefono", default="573001234567",
                        help="Número de teléfono (con código de país, ej: 573001234567)")
    parser.add_argument("--orden", action="store_true",
                        help="Simular orden completada (cliente pagó)")
    parser.add_argument("--enviar-ahora", action="store_true",
                        help="Enviar mensaje de recuperación inmediatamente")
    args = parser.parse_args()

    if args.orden:
        await simular_orden_completada()
    elif args.enviar_ahora:
        await enviar_ahora(args.telefono)
    else:
        await simular_checkout_abandonado(args.telefono)


if __name__ == "__main__":
    asyncio.run(main())
