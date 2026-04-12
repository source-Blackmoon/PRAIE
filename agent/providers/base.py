from abc import ABC, abstractmethod
from dataclasses import dataclass
from fastapi import Request


@dataclass
class MensajeEntrante:
    telefono: str
    texto: str
    mensaje_id: str
    es_propio: bool


class ProveedorWhatsApp(ABC):

    @abstractmethod
    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        ...

    @abstractmethod
    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        ...

    async def enviar_mensaje_interactivo(
        self, telefono: str, cuerpo: str, productos: list[dict],
    ) -> bool:
        """
        Envía un mensaje con productos en formato interactivo (list message).
        Si el proveedor no lo soporta, hace fallback a texto plano.
        productos: lista de dicts con titulo, precio, url (max 10).
        """
        return await self.enviar_mensaje(telefono, cuerpo)

    async def validar_webhook(self, request: Request) -> dict | int | None:
        return None
