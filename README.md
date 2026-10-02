# AutoConfirm

Aplicación multi-tenant para que empresas (ej. wedding planners) gestionen invitaciones por WhatsApp y confirmaciones de asistencia a sus eventos.

## Archivos principales

- `app.py` → dashboard web (Flask): login, eventos, carga de invitados, envío de WhatsApp, página pública de confirmación.
- `models.py` → modelo de datos: Organización → Usuario / Evento → Invitado, con credenciales de Twilio cifradas por organización.
- `twilio_sender.py` → lógica de envío por la API de Twilio (WhatsApp).
- `crear_cliente.py` → script para dar de alta una empresa cliente nueva con sus usuarios (no hay registro público).

## Estructura

- `assets/` → iconos y recursos visuales.
- `data/` → Excel de ejemplo y base SQLite local de desarrollo.
- `legacy/` → código viejo que ya no se usa, pero se conserva (incluye las apps de escritorio originales: `main_app.py`, `main_app_meta_test.py`, `main_apptwilio.py`).
- `packaging/` → archivos `.spec` e instalador de las apps de escritorio legacy.
- `release/` → compilados y material de venta de la versión anterior (escritorio).
- `demo_mañana/` → copia de trabajo de una demo de ventas (no versionada en git).

## Notas

- La versión actual es 100% web: el envío de WhatsApp vive en el servidor (`app.py` + `twilio_sender.py`), usando Twilio como BSP. Cada organización cliente guarda sus propias credenciales desde `/configuracion`.
- Las apps de escritorio en `legacy/` (basadas en WhatsApp Web o en Meta Cloud API directo) ya no reciben mantenimiento.
- Desplegado en Render: ver `RENDER_DEPLOY.md`.
