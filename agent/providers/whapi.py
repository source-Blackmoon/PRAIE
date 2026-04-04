import os
import logging
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante

logger = logging.getLogger("agentkit")


class ProveedorWhapi(ProveedorWhatsApp):

    def __init__(self):
        self.token = os.getenv("WHAPI_TOKEN")
        self.api_url = os.getenv("WHAPI_API_URL", "https://gate.whapi.cloud/")
        self.url_envio = f"{self.api_url.rstrip('/')}/messages/text"

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        body = await request.json()
        mensajes = []
        for msg in body.get("messages", []):
            if msg.get("type") != "text":
                continue
            mensajes.append(MensajeEntrante(
                telefono=msg.get("chat_id", ""),
                texto=msg.get("text", {}).get("body", ""),
                mensaje_id=msg.get("id", ""),
                es_propio=msg.get("from_me", False),
            ))
        return mensajes

    def _formatear_telefono(self, telefono: str) -> str:
        """Whapi acepta: 573001234567@s.whatsapp.net o solo 573001234567"""
        limpio = "".join(filter(str.isdigit, telefono.split("@")[0]))
        return f"{limpio}@s.whatsapp.net"

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        if not self.token:
            logger.warning("WHAPI_TOKEN no configurado")
            return False
        destino = self._formatear_telefono(telefono)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    self.url_envio,
                    json={"to": destino, "body": mensaje},
                    headers=headers,
                )
                if r.status_code not in (200, 201):
                    logger.error(f"Error Whapi {r.status_code}: {r.text}")
                return r.status_code in (200, 201)
        except httpx.TimeoutException:
            logger.error("Timeout al enviar mensaje por Whapi")
            return False
        except Exception as e:
            logger.error(f"Error inesperado Whapi: {e}")
            return False
