import os
import yaml
import logging
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("agentkit")

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TOOLS = [
    {
        "name": "buscar_productos",
        "description": (
            "Busca productos disponibles en el catálogo de PRAIE en Shopify. "
            "Úsala cuando la clienta pregunte por un tipo de vestido, talla, color, "
            "nueva colección, o pida recomendaciones. Siempre busca antes de recomendar. "
            "Nunca inventes nombres de productos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Término de búsqueda. Ej: 'enterizo control abdomen', "
                        "'bikini talla grande', 'nueva colección', 'trikini'"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Máximo de productos a retornar (1-5). Default: 2.",
                    "default": 2,
                },
            },
            "required": ["query"],
        },
    }
]


def _cargar_prompts() -> dict:
    try:
        with open("config/prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/prompts.yaml no encontrado")
        return {}


def cargar_system_prompt() -> str:
    return _cargar_prompts().get("system_prompt", "Eres Laura, asistente de PRAIE. Responde en español.")


def obtener_mensaje_error() -> str:
    return _cargar_prompts().get("error_message", "Lo siento, estoy teniendo problemas técnicos. Intenta de nuevo en unos minutos.")


def obtener_mensaje_fallback() -> str:
    return _cargar_prompts().get("fallback_message", "Disculpa, no entendí tu mensaje. ¿Puedes reformularlo?")


async def _ejecutar_herramienta(nombre: str, parametros: dict) -> str:
    if nombre == "buscar_productos":
        from agent.shopify import buscar_productos_shopify
        query = parametros.get("query", "")
        limit = parametros.get("limit", 2)
        productos = await buscar_productos_shopify(query, limit)
        if not productos:
            return "No encontré productos que coincidan con esa búsqueda en este momento."
        lineas = []
        for p in productos:
            tallas_str = ", ".join(p["tallas"]) if p["tallas"] else "consultar disponibilidad"
            lineas.append(
                f"• {p['titulo']}\n"
                f"  Precio: {p['precio']}\n"
                f"  Tallas disponibles: {tallas_str}\n"
                f"  Link: {p['url']}"
            )
        return "\n\n".join(lineas)
    return f"Herramienta '{nombre}' no reconocida."


async def generar_respuesta(mensaje: str, historial: list[dict]) -> str:
    if not mensaje or len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback()

    mensajes = [{"role": m["role"], "content": m["content"]} for m in historial]
    mensajes.append({"role": "user", "content": mensaje})

    try:
        for _ in range(5):  # máximo 5 rondas de tool_use
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=cargar_system_prompt(),
                messages=mensajes,
                tools=TOOLS,
            )

            if response.stop_reason == "end_turn":
                texto = next(
                    (b.text for b in response.content if hasattr(b, "text")),
                    obtener_mensaje_fallback(),
                )
                logger.info(f"Tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
                return texto

            if response.stop_reason == "tool_use":
                mensajes.append({"role": "assistant", "content": response.content})
                resultados = []
                for bloque in response.content:
                    if bloque.type == "tool_use":
                        logger.info(f"Tool call: {bloque.name}({bloque.input})")
                        resultado = await _ejecutar_herramienta(bloque.name, bloque.input)
                        resultados.append({
                            "type": "tool_result",
                            "tool_use_id": bloque.id,
                            "content": resultado,
                        })
                mensajes.append({"role": "user", "content": resultados})
                continue

            break  # stop_reason inesperado

        return obtener_mensaje_fallback()

    except Exception as e:
        logger.error(f"Error Claude API: {e}")
        return obtener_mensaje_error()
