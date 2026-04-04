"""
Herramienta de revisión semanal — Laura (PRAIE)
Muestra las conversaciones reales para identificar qué mejorar.

Uso:
    python tools/revisar_conversaciones.py
    python tools/revisar_conversaciones.py --dias 3
    python tools/revisar_conversaciones.py --buscar "talla"
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text
from agent.memory import Mensaje, inicializar_db
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentkit.db")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

SEÑALES_DE_PROBLEMA = [
    "no tengo esa información",
    "déjame consultarlo",
    "no entendí",
    "problemas técnicos",
    "no sé",
    "no puedo",
    "disculpa",
]


async def obtener_todos_los_mensajes(dias: int = 7):
    desde = datetime.utcnow() - timedelta(days=dias)
    async with async_session() as session:
        query = (
            select(Mensaje)
            .where(Mensaje.timestamp >= desde)
            .order_by(Mensaje.telefono, Mensaje.timestamp)
        )
        result = await session.execute(query)
        return result.scalars().all()


def agrupar_por_conversacion(mensajes):
    conversaciones = {}
    for m in mensajes:
        if m.telefono not in conversaciones:
            conversaciones[m.telefono] = []
        conversaciones[m.telefono].append(m)
    return conversaciones


def detectar_problemas(respuesta: str) -> bool:
    respuesta_lower = respuesta.lower()
    return any(señal in respuesta_lower for señal in SEÑALES_DE_PROBLEMA)


def mostrar_conversacion(telefono: str, mensajes: list):
    print(f"\n{'='*60}")
    print(f"  Número: {telefono[-6:]}****  |  Mensajes: {len(mensajes)}")
    print(f"  Fecha: {mensajes[0].timestamp.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}")

    tiene_problema = False
    for m in mensajes:
        if m.role == "user":
            print(f"\n  Clienta: {m.content}")
        else:
            tiene_problema = detectar_problemas(m.content)
            marca = " ⚠️  REVISAR" if tiene_problema else ""
            print(f"  Laura:   {m.content[:200]}{'...' if len(m.content) > 200 else ''}{marca}")


async def mostrar_resumen(conversaciones: dict, dias: int):
    total_mensajes = sum(len(v) for v in conversaciones.values())
    mensajes_usuario = []
    respuestas_problema = []

    for telefono, mensajes in conversaciones.items():
        for m in mensajes:
            if m.role == "user":
                mensajes_usuario.append(m.content.lower())
            elif m.role == "assistant" and detectar_problemas(m.content):
                respuestas_problema.append(m.content[:100])

    # Palabras más buscadas
    palabras = []
    for msg in mensajes_usuario:
        palabras.extend(msg.split())

    stopwords = {"que", "de", "el", "la", "en", "un", "una", "me", "si", "no",
                 "se", "con", "por", "mi", "es", "y", "a", "los", "las", "le",
                 "su", "al", "del", "hola", "buenas", "gracias", "ok", "bien"}
    palabras_limpias = [p for p in palabras if len(p) > 3 and p not in stopwords]
    top_palabras = Counter(palabras_limpias).most_common(10)

    print(f"\n{'='*60}")
    print(f"  RESUMEN — últimos {dias} días")
    print(f"{'='*60}")
    print(f"  Conversaciones:     {len(conversaciones)}")
    print(f"  Mensajes totales:   {total_mensajes}")
    print(f"  Preguntas de clientas: {len(mensajes_usuario)}")
    print(f"  Respuestas a revisar:  {len(respuestas_problema)} ⚠️")

    if top_palabras:
        print(f"\n  Temas más preguntados:")
        for palabra, count in top_palabras:
            print(f"    → '{palabra}' ({count} veces)")

    if respuestas_problema:
        print(f"\n  Respuestas que necesitan mejora:")
        for r in respuestas_problema[:5]:
            print(f"    ⚠️  {r}...")

    print(f"\n{'='*60}")
    print(f"  ACCIÓN: Agrega las preguntas frecuentes a:")
    print(f"  knowledge/preguntas_reales.txt")
    print(f"{'='*60}\n")


async def buscar_en_conversaciones(termino: str):
    async with async_session() as session:
        query = select(Mensaje).order_by(Mensaje.telefono, Mensaje.timestamp)
        result = await session.execute(query)
        mensajes = result.scalars().all()

    encontrados = [m for m in mensajes if termino.lower() in m.content.lower()]
    print(f"\n  Encontré {len(encontrados)} mensajes con '{termino}':\n")
    for m in encontrados:
        rol = "Clienta" if m.role == "user" else "Laura  "
        print(f"  [{m.timestamp.strftime('%d/%m %H:%M')}] {rol}: {m.content[:150]}")


async def main():
    parser = argparse.ArgumentParser(description="Revisar conversaciones de Laura")
    parser.add_argument("--dias", type=int, default=7, help="Días a revisar (default: 7)")
    parser.add_argument("--buscar", type=str, help="Buscar un término en las conversaciones")
    parser.add_argument("--todo", action="store_true", help="Mostrar todas las conversaciones completas")
    args = parser.parse_args()

    await inicializar_db()

    print("\n" + "="*60)
    print("   Laura — Revisor de Conversaciones PRAIE")
    print("="*60)

    if args.buscar:
        await buscar_en_conversaciones(args.buscar)
        return

    mensajes = await obtener_todos_los_mensajes(args.dias)

    if not mensajes:
        print(f"\n  No hay conversaciones en los últimos {args.dias} días.")
        print("  Prueba con: python tools/revisar_conversaciones.py --dias 30\n")
        return

    conversaciones = agrupar_por_conversacion(mensajes)
    await mostrar_resumen(conversaciones, args.dias)

    if args.todo:
        for telefono, msgs in conversaciones.items():
            mostrar_conversacion(telefono, msgs)
    else:
        # Mostrar solo las que tienen problemas
        con_problemas = {}
        for telefono, msgs in conversaciones.items():
            for m in msgs:
                if m.role == "assistant" and detectar_problemas(m.content):
                    con_problemas[telefono] = msgs
                    break

        if con_problemas:
            print(f"  Conversaciones con posibles problemas ({len(con_problemas)}):")
            for telefono, msgs in con_problemas.items():
                mostrar_conversacion(telefono, msgs)
        else:
            print("  No se detectaron problemas en las respuestas de Laura.")
            print("  Usa --todo para ver todas las conversaciones.\n")


if __name__ == "__main__":
    asyncio.run(main())
