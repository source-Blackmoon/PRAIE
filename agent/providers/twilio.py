# agent/providers/twilio.py — Adaptador para Twilio WhatsApp Sandbox
import os
import hmac
import hashlib
import base64
import logging
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante

logger = logging.getLogger("agentkit")


class ProveedorTwilio(ProveedorWhatsApp):
    """
    Proveedor de WhatsApp usando Twilio Sandbox.

    Sandbox: los mensajes vienen como form-encoded (no JSON).
    Número de sandbox de Twilio: whatsapp:+14155238886
    Para unirse: enviar "join <palabra>-<palabra>" a ese número.
    """

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        # En sandbox usa el número de Twilio; en producción, el tuyo asignado
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER", "whatsapp:+14155238886")
        self.url_envio = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

    def _auth_header(self) -> str:
        credenciales = f"{self.account_sid}:{self.auth_token}"
        return "Basic " + base64.b64encode(credenciales.encode()).decode()

    def _validar_firma(self, url: str, params: dict, firma_recibida: str) -> bool:
        """
        Verifica la firma X-Twilio-Signature para confirmar que el webhook
        viene realmente de Twilio (seguridad).
        """
        if not self.auth_token:
            return True  # Sin token configurado, se omite la validación
        # Twilio firma: HMAC-SHA1 sobre url + params ordenados alfabéticamente
        mensaje = url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
        firma_esperada = base64.b64encode(
            hmac.new(self.auth_token.encode(), mensaje.encode(), hashlib.sha1).digest()
        ).decode()
        return hmac.compare_digest(firma_esperada, firma_recibida)

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """
        Twilio envía los mensajes como form-encoded (application/x-www-form-urlencoded).
        Formato clave:
          Body    → texto del mensaje
          From    → whatsapp:+573001234567
          To      → whatsapp:+14155238886
          MessageSid → ID único
        """
        form = await request.form()
        params = dict(form)

        # Validar firma de Twilio si auth_token esta configurado
        if self.auth_token:
            firma = request.headers.get("X-Twilio-Signature", "")
            # Usar WEBHOOK_BASE_URL si Railway/proxy cambia la URL interna
            base_url = os.getenv("WEBHOOK_BASE_URL", "")
            if base_url:
                url = f"{base_url.rstrip('/')}/webhook"
            else:
                url = str(request.url)
            if not self._validar_firma(url, params, firma):
                logger.warning(f"Firma Twilio invalida — posible webhook falso")
                return []  # Rechazar silenciosamente

        texto = params.get("Body", "").strip()
        from_raw = params.get("From", "")
        mensaje_id = params.get("MessageSid", "")

        # Normalizar número: quitar "whatsapp:" del prefijo
        telefono = from_raw.replace("whatsapp:", "").strip()

        if not texto or not telefono:
            return []

        return [MensajeEntrante(
            telefono=telefono,
            texto=texto,
            mensaje_id=mensaje_id,
            es_propio=False,
        )]

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """
        Envía un mensaje via Twilio. El número destino se normaliza
        al formato whatsapp:+573001234567 que Twilio espera.
        """
        if not self.account_sid or not self.auth_token:
            logger.warning("TWILIO_ACCOUNT_SID o TWILIO_AUTH_TOKEN no configurados")
            return False

        # Normalizar números al formato whatsapp:+XXXXXXXXXX
        to_number = telefono if telefono.startswith("whatsapp:") else f"whatsapp:{telefono}"
        from_number = self.from_number if self.from_number.startswith("whatsapp:") else f"whatsapp:{self.from_number}"

        headers = {"Authorization": self._auth_header()}

        async with httpx.AsyncClient() as client:
            r = await client.post(self.url_envio, data={
                "From": from_number,
                "To": to_number,
                "Body": mensaje,
            }, headers=headers)
            if r.status_code not in (200, 201):
                logger.error(f"Error Twilio {r.status_code}: {r.text[:200]}")
                return False
            logger.info(f"Mensaje enviado via Twilio a {to_number}")
            return True

    async def enviar_mensaje_interactivo(
        self, telefono: str, cuerpo: str, productos: list[dict],
    ) -> bool:
        """
        Envía productos usando Twilio Content Templates (ContentSid) si está configurado.
        Fallback: texto formateado con productos.

        Para usar templates interactivos:
        1. Crear template tipo list-picker en Twilio Content Editor
        2. Esperar aprobacion de Meta (24-48h primera vez)
        3. Configurar TWILIO_CATALOGO_CONTENT_SID en .env
        """
        content_sid = os.getenv("TWILIO_CATALOGO_CONTENT_SID", "")

        if content_sid and self.account_sid and self.auth_token:
            to_number = telefono if telefono.startswith("whatsapp:") else f"whatsapp:{telefono}"
            from_number = self.from_number if self.from_number.startswith("whatsapp:") else f"whatsapp:{self.from_number}"

            # Construir variables para el template
            import json
            variables = {}
            for i, p in enumerate(productos[:10]):
                variables[f"{i+1}"] = p.get("titulo", "Producto")
            content_variables = json.dumps(variables)

            headers = {"Authorization": self._auth_header()}
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.post(self.url_envio, data={
                        "From": from_number,
                        "To": to_number,
                        "ContentSid": content_sid,
                        "ContentVariables": content_variables,
                    }, headers=headers)
                    if r.status_code in (200, 201):
                        logger.info(f"Mensaje interactivo enviado via Twilio a {to_number}")
                        return True
                    logger.warning(f"Template interactivo falló ({r.status_code}), usando texto fallback")
            except Exception as e:
                logger.warning(f"Error enviando interactivo: {e}, usando texto fallback")

        # Fallback: texto formateado
        return await self.enviar_mensaje(telefono, cuerpo)
