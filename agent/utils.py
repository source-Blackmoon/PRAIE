"""Utilidades compartidas del agente."""
import re


def normalizar_telefono_e164(raw: str) -> str:
    """
    Normaliza un número de teléfono al formato E.164 para Colombia (+57XXXXXXXXXX).

    Maneja formatos de entrada:
      - +573001234567 (ya E.164)
      - 573001234567 (sin +)
      - 3001234567 (local colombiano)
      - whatsapp:+573001234567 (formato Twilio)
    """
    telefono = raw.strip()
    telefono = telefono.replace("whatsapp:", "").strip()
    telefono = re.sub(r"[\s\-\(\)]+", "", telefono)

    if not telefono:
        return ""

    if telefono.startswith("+"):
        return telefono

    if telefono.startswith("57") and len(telefono) == 12:
        return f"+{telefono}"

    if len(telefono) == 10 and telefono[0] == "3":
        return f"+57{telefono}"

    return f"+{telefono}"
