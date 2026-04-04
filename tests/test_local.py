import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, limpiar_historial

TELEFONO_TEST = "test-praie-local"


async def main():
    await inicializar_db()
    print()
    print("=" * 50)
    print("   Laura — Agente WhatsApp PRAIE (Test Local)")
    print("=" * 50)
    print("  'limpiar' → borra historial  |  'salir' → termina")
    print("-" * 50)
    print()

    while True:
        try:
            mensaje = input("Tu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTest finalizado.")
            break

        if not mensaje:
            continue
        if mensaje.lower() == "salir":
            print("Test finalizado.")
            break
        if mensaje.lower() == "limpiar":
            await limpiar_historial(TELEFONO_TEST)
            print("[Historial borrado]\n")
            continue

        historial = await obtener_historial(TELEFONO_TEST)
        print("\nLaura: ", end="", flush=True)
        respuesta = await generar_respuesta(mensaje, historial)
        print(respuesta)
        print()

        await guardar_mensaje(TELEFONO_TEST, "user", mensaje)
        await guardar_mensaje(TELEFONO_TEST, "assistant", respuesta)


if __name__ == "__main__":
    asyncio.run(main())
