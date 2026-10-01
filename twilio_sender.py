import json
import re
import time

import requests

from models import Evento, Invitado, Session

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"
DELAY_SECONDS = 2


def normalize_phone_mx(raw_phone: str, country_code: str = "52") -> str:
    phone = re.sub(r"\D", "", str(raw_phone))
    if not phone:
        raise ValueError("teléfono vacío")

    if not phone.startswith(country_code) and len(phone) <= 10:
        phone = f"{country_code}{phone}"

    # WhatsApp (a diferencia de la telefonía normal) requiere un "1" extra
    # después del código de país 52 para celulares de México.
    if country_code == "52" and phone.startswith("52") and not phone.startswith("521"):
        phone = f"521{phone[2:]}"

    return phone


def build_twilio_payload(from_number: str, phone_e164: str, name: str, link: str, content_sid: str) -> dict:
    payload = {"From": from_number, "To": f"whatsapp:{phone_e164}"}
    if content_sid:
        payload["ContentSid"] = content_sid
        payload["ContentVariables"] = json.dumps({"1": name, "2": link})
    else:
        payload["Body"] = f"Hola {name}, por favor confirma tu asistencia aquí: {link}"
    return payload


def enviar_invitaciones_evento(evento_id: int, confirmation_base_url: str) -> None:
    """Corre en un hilo de fondo: manda WhatsApp a los invitados pendientes de un evento."""
    session = Session()
    try:
        evento = session.get(Evento, evento_id)
        if not evento:
            return
        organizacion = evento.organizacion

        account_sid = organizacion.twilio_account_sid
        auth_token = organizacion.twilio_auth_token
        from_number = organizacion.twilio_whatsapp_from
        content_sid = organizacion.twilio_content_sid

        if not (account_sid and auth_token and from_number):
            return

        url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/Messages.json"

        pendientes = (
            session.query(Invitado)
            .filter(Invitado.evento_id == evento_id, Invitado.mensaje_enviado != "Si")
            .all()
        )

        for invitado in pendientes:
            try:
                telefono = normalize_phone_mx(invitado.telefono)
                link = f"{confirmation_base_url}?id={invitado.uuid}"
                payload = build_twilio_payload(
                    from_number, telefono, invitado.nombre or "Invitado", link, content_sid
                )
                response = requests.post(url, data=payload, auth=(account_sid, auth_token), timeout=30)
                if response.ok:
                    invitado.mensaje_enviado = "Si"
                    session.commit()
                else:
                    session.rollback()
            except Exception:
                session.rollback()
            finally:
                time.sleep(DELAY_SECONDS)
    finally:
        session.close()
