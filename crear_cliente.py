"""Da de alta una empresa cliente (organización) nueva, con sus usuarios (planners).

Uso: python crear_cliente.py
"""

from getpass import getpass

from models import Evento, Organizacion, Session, Usuario, init_db


def main():
    init_db()
    db = Session()

    print("=== Nueva organización (empresa cliente) ===")
    nombre_empresa = input("Nombre de la empresa: ").strip()

    print("\n--- Credenciales de Twilio de esta empresa ---")
    twilio_sid = input("Twilio Account SID: ").strip()
    twilio_token = getpass("Twilio Auth Token (no se muestra al escribir): ").strip()
    twilio_from = input("Twilio WhatsApp From (ej. whatsapp:+14155238886): ").strip()
    twilio_content_sid = input("Twilio Content SID (opcional, Enter para dejar vacío): ").strip()

    organizacion = Organizacion(
        nombre=nombre_empresa,
        twilio_account_sid=twilio_sid,
        twilio_whatsapp_from=twilio_from,
        twilio_content_sid=twilio_content_sid,
    )
    organizacion.twilio_auth_token = twilio_token
    db.add(organizacion)
    db.flush()
    print(f"\nOrganización '{nombre_empresa}' creada (id={organizacion.id}).")

    print("\n--- Usuarios (planners) ---")
    print("Agrega uno o más. Deja el correo vacío para terminar.\n")

    primer_usuario = None
    while True:
        email = input("Correo del planner (Enter para terminar): ").strip().lower()
        if not email:
            break
        password = getpass(f"Contraseña para {email}: ").strip()
        es_admin = input("¿Es admin de la empresa (ve todos los eventos)? (s/N): ").strip().lower() == "s"

        usuario = Usuario(organizacion_id=organizacion.id, email=email, es_admin=es_admin)
        usuario.set_password(password)
        db.add(usuario)
        db.flush()
        print(f"  -> usuario {email} creado (id={usuario.id})\n")
        if primer_usuario is None:
            primer_usuario = usuario

    if primer_usuario is None:
        print("No se creó ningún usuario; no podrás iniciar sesión todavía.")
    else:
        crear_evento = input("\n¿Crear un primer evento de ejemplo? (s/N): ").strip().lower() == "s"
        if crear_evento:
            nombre_evento = input("Nombre del evento: ").strip() or "Mi primer evento"
            evento = Evento(
                organizacion_id=organizacion.id,
                creado_por_id=primer_usuario.id,
                nombre=nombre_evento,
            )
            db.add(evento)

    db.commit()
    db.close()
    print("\nListo. La organización y sus usuarios ya pueden iniciar sesión en /login.")


if __name__ == "__main__":
    main()
