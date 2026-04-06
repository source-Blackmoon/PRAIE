import os
import time
import yaml
import logging
from pathlib import Path
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
            "nueva colección, o pida recomendaciones. También úsala cuando pregunte "
            "por ofertas, descuentos, promociones o productos en rebaja — busca con "
            "el término 'sale' o 'descuento'. Siempre busca antes de recomendar. "
            "Nunca inventes nombres de productos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Término de búsqueda. Ej: 'enterizo control abdomen', "
                        "'bikini talla grande', 'nueva colección', 'trikini', "
                        "'sale', 'descuento'"
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
    },
    {
        "name": "buscar_ofertas",
        "description": (
            "Busca productos que tienen precio rebajado (en oferta o descuento) en el catálogo de PRAIE. "
            "Úsala cuando la clienta pregunte por ofertas, descuentos, promociones, rebajas o precios especiales. "
            "Retorna productos con precio actual y precio original para mostrar el ahorro."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Máximo de productos en oferta a retornar (1-5). Default: 3.",
                    "default": 3,
                },
            },
            "required": [],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Transfiere la conversación a una asesora humana de PRAIE. "
            "Úsala cuando la clienta tenga: problemas con un pedido existente, "
            "solicitudes de devolución o cambio, quejas, o cualquier situación "
            "que no puedas resolver como agente. NUNCA intentes resolver "
            "temas de logística, devoluciones o cobros — siempre escala."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "motivo": {
                    "type": "string",
                    "description": (
                        "Razón del escalamiento. Ej: 'pedido no llegó', "
                        "'producto defectuoso', 'quiere devolución'"
                    ),
                },
                "resumen": {
                    "type": "string",
                    "description": "Breve resumen del problema para que la asesora tenga contexto.",
                },
            },
            "required": ["motivo"],
        },
    },
]


def _cargar_prompts() -> dict:
    try:
        with open("config/prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/prompts.yaml no encontrado")
        return {}


def _cargar_knowledge() -> str:
    """Carga todos los archivos .txt de /knowledge y los concatena."""
    knowledge_dir = Path("knowledge")
    if not knowledge_dir.exists():
        return ""
    secciones = []
    for archivo in sorted(knowledge_dir.glob("*.txt")):
        try:
            contenido = archivo.read_text(encoding="utf-8").strip()
            if contenido:
                secciones.append(f"## {archivo.stem.replace('_', ' ').title()}\n{contenido}")
        except Exception as e:
            logger.warning(f"No se pudo leer {archivo.name}: {e}")
    return "\n\n".join(secciones)


_prompt_cache: tuple[str, float] | None = None
_PROMPT_TTL = 60  # segundos — permite ver cambios del dashboard sin reiniciar


def cargar_system_prompt() -> str:
    global _prompt_cache
    now = time.time()
    if _prompt_cache is None or now - _prompt_cache[1] > _PROMPT_TTL:
        base = _cargar_prompts().get("system_prompt", "Eres Laura, asistente de PRAIE. Responde en español.")
        knowledge = _cargar_knowledge()
        content = f"{base}\n\n# INFORMACIÓN ADICIONAL DEL NEGOCIO\n{knowledge}" if knowledge else base
        _prompt_cache = (content, now)
    return _prompt_cache[0]


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
    if nombre == "buscar_ofertas":
        from agent.shopify import buscar_ofertas_shopify
        limit = parametros.get("limit", 3)
        productos = await buscar_ofertas_shopify(limit)
        if not productos:
            return "No encontré productos en oferta en este momento."
        lineas = []
        for p in productos:
            tallas_str = ", ".join(p["tallas"]) if p["tallas"] else "consultar disponibilidad"
            descuento = f"  ~~{p['precio_antes']}~~ → {p['precio']}" if p.get("precio_antes") else f"  Precio: {p['precio']}"
            lineas.append(
                f"• {p['titulo']}\n"
                f"{descuento}\n"
                f"  Tallas disponibles: {tallas_str}\n"
                f"  Link: {p['url']}"
            )
        return "\n\n".join(lineas)
    if nombre == "escalate_to_human":
        motivo = parametros.get("motivo", "motivo no especificado")
        resumen = parametros.get("resumen", "")
        logger.warning(f"ESCALAMIENTO A HUMANO — motivo: {motivo} | resumen: {resumen}")
        # Aquí se puede agregar integración con CRM, Slack, email, etc.
        # Por ahora registra el evento en logs para que el equipo lo vea
        return "ESCALAMIENTO_REGISTRADO"
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

            logger.info(f"Claude stop_reason={response.stop_reason} | tokens={response.usage.input_tokens}in/{response.usage.output_tokens}out")

            if response.stop_reason == "end_turn":
                texto = next(
                    (b.text for b in response.content if hasattr(b, "text")),
                    obtener_mensaje_fallback(),
                )
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
