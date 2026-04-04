"""
Ver carritos abandonados de Shopify — PRAIE
Consulta la API directamente sin necesitar el servidor corriendo.

Uso:
    python tools/ver_carritos.py              ← últimas 48 horas
    python tools/ver_carritos.py --horas 24   ← últimas 24 horas
    python tools/ver_carritos.py --verificar  ← solo verifica credenciales
"""

import asyncio
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from agent.shopify import verificar_credenciales, obtener_checkouts_shopify


async def main():
    parser = argparse.ArgumentParser(description="Ver carritos abandonados de Shopify")
    parser.add_argument("--horas", type=int, default=48, help="Horas hacia atrás (default: 48)")
    parser.add_argument("--verificar", action="store_true", help="Solo verificar credenciales")
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  PRAIE — Carritos Abandonados Shopify")
    print("=" * 60)

    # Verificar credenciales
    print("\n  Verificando conexión con Shopify...")
    creds = await verificar_credenciales()

    if not creds["ok"]:
        print(f"\n  ❌ Error de autenticación: {creds.get('error')}")
        print(f"\n  Revisa SHOPIFY_ACCESS_TOKEN en tu .env")
        print(f"  Tienda configurada: {os.getenv('SHOPIFY_STORE_URL', 'no configurada')}")
        print(f"\n  El token debe ser de una app privada (empieza con shpat_)")
        print(f"  Shopify Admin → Apps → Develop apps → Create an app")
        return

    print(f"  ✅ Conectado a: {creds['tienda']} ({creds['dominio']})")
    print(f"     Plan: {creds['plan']}")

    if args.verificar:
        return

    # Obtener carritos abandonados
    print(f"\n  Buscando carritos abandonados (últimas {args.horas}h)...\n")
    carritos = await obtener_checkouts_shopify(horas_atras=args.horas)

    if not carritos:
        print(f"  No hay carritos abandonados con teléfono en las últimas {args.horas}h.")
        print(f"\n  Nota: Solo se muestran checkouts con número de teléfono registrado.")
        return

    print(f"  Encontrados: {len(carritos)} carritos con teléfono\n")
    print(f"  {'-'*58}")

    for i, c in enumerate(carritos, 1):
        print(f"\n  [{i}] ID: {c['checkout_id']}")
        print(f"      Nombre:    {c['nombre']}")
        print(f"      Teléfono:  {c['telefono']}")
        print(f"      Productos: {c['productos']}")
        print(f"      Total:     {c['total']}")
        print(f"      URL:       {c['url_carrito']}")

    print(f"\n  {'-'*58}")
    print(f"\n  Para sincronizar a la base de datos y activar el scheduler,")
    print(f"  levanta el servidor: uvicorn agent.main:app --reload\n")


if __name__ == "__main__":
    asyncio.run(main())
