# AutoConfirm en Render

## Archivos ya listos
- `app.py`
- `requirements.txt`
- `render.yaml`

## Qué harás tú
1. Subir la carpeta/proyecto a GitHub.
2. Crear cuenta en Render.
3. En Render: **New +** → **Blueprint** o **Web Service**.
4. Conectar tu repo.
5. Si detecta `render.yaml`, aceptar la configuración.
6. Esperar a que termine el deploy.
7. Abrir la URL pública que te entregue Render.

## Si lo haces como Web Service manual
Usa estos valores:
- **Environment:** Python
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`

## Después del deploy
Cuando Render te dé una URL como esta:
- `https://autoconfirm-web.onrender.com`

la URL base de confirmación será:
- `https://autoconfirm-web.onrender.com/confirmar`

Esa URL la pondrás en `main_app_meta_test.py` en el campo:
- **URL base confirmación**

## Nota importante
Ahorita la base usa SQLite. Para pruebas sirve bien.
Si luego lo vendes en serio, convendrá migrar a una base más robusta.
