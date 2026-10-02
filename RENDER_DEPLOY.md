# AutoConfirm en Render

## Recursos necesarios
- Un **Web Service** (Python) apuntando a este repo.
- Una base de datos **Postgres** (el plan gratis de Render se borra a los 90 días de inactividad — usar un plan de pago desde el inicio).

## Build y start command
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`

## Variables de entorno obligatorias
- `DATABASE_URL` → connection string de la base Postgres (interna, si Web Service y base están en la misma región).
- `SECRET_KEY` → firma las sesiones de login. Generar con:
  `python -c "import secrets; print(secrets.token_hex(32))"`
- `ENCRYPTION_KEY` → cifra las credenciales de Twilio guardadas por organización. Generar con:
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
  (si se pierde o se cambia, las credenciales de Twilio ya guardadas quedan ilegibles).

Sin `SECRET_KEY` o `ENCRYPTION_KEY`, el servicio no arranca (falla rápido con un error claro en los logs).

## Después del primer deploy
1. Correr `crear_cliente.py` (localmente, apuntando `AUTOCONFIRM_DATABASE_URL` a la base de producción) para dar de alta la primera organización y su usuario.
2. Iniciar sesión en `https://<tu-dominio>.onrender.com/login`.
3. Cada organización configura sus propias credenciales de Twilio desde `/configuracion` dentro del dashboard — ya no se editan en ningún archivo.

## Nota sobre el plan del Web Service
Mientras no haya clientes reales pagando, el Web Service puede quedarse en el plan gratis (solo implica ~50s de espera tras inactividad, no hay riesgo de pérdida de datos). Subir a un plan pagado (Starter) cuando el tiempo de espera inicial empiece a afectar a un cliente real.
