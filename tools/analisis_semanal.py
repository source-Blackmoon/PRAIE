"""
Análisis semanal automático — Laura (PRAIE)
Claude revisa todas las conversaciones de la semana y sugiere mejoras concretas.

Uso:
    python tools/analisis_semanal.py
    python tools/analisis_semanal.py --dias 14
    python tools/analisis_semanal.py --aplicar   ← aplica mejoras automáticamente
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from agent.memory import Mensaje, inicializar_db
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentkit.db")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
REPORTS_DIR = Path("tools/reportes")


async def obtener_conversaciones(dias: int) -> dict:
    desde = datetime.utcnow() - timedelta(days=dias)
    async with async_session() as session:
        query = (
            select(Mensaje)
            .where(Mensaje.timestamp >= desde)
            .order_by(Mensaje.telefono, Mensaje.timestamp)
        )
        result = await session.execute(query)
        mensajes = result.scalars().all()

    conversaciones = {}
    for m in mensajes:
        if m.telefono not in conversaciones:
            conversaciones[m.telefono] = []
        conversaciones[m.telefono].append({
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.strftime("%d/%m/%Y %H:%M"),
        })
    return conversaciones


def formatear_conversaciones(conversaciones: dict) -> str:
    if not conversaciones:
        return "No hay conversaciones en el período."

    texto = []
    for i, (telefono, mensajes) in enumerate(conversaciones.items(), 1):
        texto.append(f"\n--- CONVERSACIÓN {i} ---")
        texto.append(f"Fecha: {mensajes[0]['timestamp']}")
        for m in mensajes:
            rol = "CLIENTA" if m["role"] == "user" else "LAURA"
            texto.append(f"{rol}: {m['content']}")
    return "\n".join(texto)


def leer_knowledge_actual() -> str:
    knowledge_dir = Path("knowledge")
    contenido = []
    for archivo in sorted(knowledge_dir.glob("*.txt")):
        contenido.append(f"\n=== {archivo.name} ===")
        contenido.append(archivo.read_text(encoding="utf-8"))
    return "\n".join(contenido)


async def analizar_con_claude(conversaciones_texto: str, knowledge_actual: str, dias: int) -> str:
    prompt = f"""Eres un experto en optimización de agentes de ventas para e-commerce colombiano.

Analiza las siguientes conversaciones reales del agente de WhatsApp "Laura" de PRAIE (marca de vestidos de baño colombiana) de los últimos {dias} días.

## CONVERSACIONES REALES:
{conversaciones_texto}

## KNOWLEDGE BASE ACTUAL (lo que Laura ya sabe):
{knowledge_actual}

## TU TAREA:

Analiza las conversaciones y entrega un reporte con estas secciones EXACTAS:

### 1. RESUMEN EJECUTIVO
(2-3 líneas: qué tan bien está funcionando Laura, tasa de respuestas problemáticas)

### 2. PREGUNTAS SIN RESPUESTA ADECUADA
Lista de preguntas que Laura no supo responder bien o evadió.
Para cada una, escribe la respuesta correcta que debería dar.
Formato:
- Pregunta: "..."
  Respuesta sugerida: "..."

### 3. TEMAS MÁS FRECUENTES
Los 5 temas que más preguntan las clientas. Ordenados de mayor a menor frecuencia.

### 4. MEJORAS AL TONO
Casos donde Laura fue demasiado formal, muy larga, o perdió el tono colombiano cercano.
Muestra el texto real y cómo debería ser.

### 5. NUEVAS ENTRADAS PARA knowledge/preguntas_reales.txt
Escribe exactamente el texto listo para copiar y pegar en el archivo.
Formato del archivo:
PREGUNTA → RESPUESTA

### 6. CAMBIOS SUGERIDOS AL PROMPT (config/prompts.yaml)
Cambios específicos y concretos. No generales.

### 7. PRIORIDAD DE ACCIÓN
Las 3 mejoras más importantes a implementar esta semana, ordenadas por impacto en ventas.

Sé específico y accionable. Usa ejemplos reales de las conversaciones."""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


async def aplicar_mejoras_automaticas(analisis: str):
    """Extrae las nuevas entradas del análisis y las agrega al knowledge base."""
    prompt = f"""Del siguiente análisis, extrae SOLO las nuevas entradas para knowledge/preguntas_reales.txt.
Devuelve ÚNICAMENTE el texto plano para agregar al archivo, sin explicaciones adicionales.
Formato: PREGUNTA → RESPUESTA (una por línea)

ANÁLISIS:
{analisis}"""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    nuevas_entradas = response.content[0].text.strip()
    if not nuevas_entradas:
        return False

    archivo = Path("knowledge/preguntas_reales.txt")
    contenido_actual = archivo.read_text(encoding="utf-8")

    fecha = datetime.now().strftime("%d/%m/%Y")
    bloque_nuevo = f"\n\n=== AGREGADO AUTOMÁTICAMENTE — {fecha} ===\n{nuevas_entradas}"

    archivo.write_text(contenido_actual + bloque_nuevo, encoding="utf-8")
    return True


async def main():
    parser = argparse.ArgumentParser(description="Análisis semanal con Claude — Laura PRAIE")
    parser.add_argument("--dias", type=int, default=7, help="Días a analizar (default: 7)")
    parser.add_argument("--aplicar", action="store_true", help="Aplicar mejoras automáticamente al knowledge base")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(exist_ok=True)
    await inicializar_db()

    print("\n" + "="*60)
    print("   Análisis Semanal — Laura (PRAIE)")
    print("="*60)
    print(f"\n  Analizando conversaciones de los últimos {args.dias} días...")

    conversaciones = await obtener_conversaciones(args.dias)

    if not conversaciones:
        print(f"\n  No hay conversaciones en los últimos {args.dias} días.")
        print("  Empieza a recibir mensajes en WhatsApp y vuelve a ejecutar.\n")
        return

    print(f"  Conversaciones encontradas: {len(conversaciones)}")
    total_mensajes = sum(len(v) for v in conversaciones.values())
    print(f"  Mensajes totales: {total_mensajes}")
    print(f"\n  Enviando a Claude para análisis...")

    conversaciones_texto = formatear_conversaciones(conversaciones)
    knowledge_actual = leer_knowledge_actual()

    analisis = await analizar_con_claude(conversaciones_texto, knowledge_actual, args.dias)

    # Guardar reporte
    fecha_archivo = datetime.now().strftime("%Y-%m-%d")
    ruta_reporte = REPORTS_DIR / f"reporte_{fecha_archivo}.md"
    ruta_reporte.write_text(
        f"# Reporte de Análisis — Laura (PRAIE)\n"
        f"**Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        f"**Período:** últimos {args.dias} días\n"
        f"**Conversaciones:** {len(conversaciones)} | **Mensajes:** {total_mensajes}\n\n"
        f"---\n\n{analisis}",
        encoding="utf-8"
    )

    print("\n" + "="*60)
    print(analisis)
    print("="*60)
    print(f"\n  Reporte guardado en: {ruta_reporte}")

    if args.aplicar:
        print("\n  Aplicando mejoras al knowledge base...")
        aplicado = await aplicar_mejoras_automaticas(analisis)
        if aplicado:
            print("  ✅ Nuevas preguntas agregadas a knowledge/preguntas_reales.txt")
            print("  Reinicia el servidor para que Laura las use:")
            print("  kill $(lsof -ti:8000) && .venv/bin/uvicorn agent.main:app --port 8000 &")
        else:
            print("  No se encontraron nuevas entradas para agregar.")
    else:
        print("\n  Para aplicar las mejoras automáticamente:")
        print("  python tools/analisis_semanal.py --aplicar\n")


if __name__ == "__main__":
    asyncio.run(main())
