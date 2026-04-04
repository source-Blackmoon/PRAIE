import os
import yaml
import logging
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("agentkit")

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


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


async def generar_respuesta(mensaje: str, historial: list[dict]) -> str:
    if not mensaje or len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback()

    mensajes = [{"role": m["role"], "content": m["content"]} for m in historial]
    mensajes.append({"role": "user", "content": mensaje})

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=cargar_system_prompt(),
            messages=mensajes,
        )
        respuesta = response.content[0].text
        logger.info(f"Tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
        return respuesta
    except Exception as e:
        logger.error(f"Error Claude API: {e}")
        return obtener_mensaje_error()
