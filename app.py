import csv
import io
import os
import threading
import uuid
from datetime import datetime
from functools import wraps

import pandas as pd
from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    g,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from markupsafe import escape

from models import Evento, EventoColaborador, Invitado, Organizacion, Session, Usuario, init_db
from twilio_sender import enviar_invitaciones_evento

load_dotenv()

init_db()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "").strip()
if not app.secret_key:
    raise RuntimeError("Falta SECRET_KEY en las variables de entorno (ver .env.example).")

limiter = Limiter(key_func=get_remote_address, app=app, storage_uri="memory://")

REQUIRED_COLUMNS = {"Nombre", "Telefono"}

BASE_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }}</title>
    <style>
        :root {
            --bg: #111116;
            --card: #1a1b24;
            --text: #f5f3ff;
            --muted: #a1a1aa;
            --accent: #7c3aed;
            --accent-dark: #5b21b6;
            --success: #8b5cf6;
            --danger: #f43f5e;
            --border: #2a2d3a;
            --input: #242634;
            --soft: #221a36;
            --soft-2: #20182d;
            --soft-3: #261f33;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: Segoe UI, Arial, sans-serif;
            background: linear-gradient(180deg, #0f1016 0%, #171822 100%);
            color: var(--text);
        }
        .wrap {
            max-width: 920px;
            margin: 0 auto;
            padding: 24px 16px 40px;
        }
        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            font-size: 14px;
        }
        .topbar a { color: #c4b5fd; text-decoration: none; }
        .topbar a:hover { text-decoration: underline; }
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 18px;
            box-shadow: 0 14px 34px rgba(0, 0, 0, 0.35);
            padding: 24px;
        }
        h1, h2, h3, p { margin-top: 0; }
        .muted { color: var(--muted); }
        .hero {
            text-align: center;
            margin-bottom: 18px;
        }
        .pill {
            display: inline-block;
            background: var(--soft);
            color: #c4b5fd;
            padding: 8px 12px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 12px;
            border: 1px solid var(--border);
        }
        .field { margin-bottom: 16px; }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
        }
        input, select, textarea {
            width: 100%;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px 14px;
            font-size: 15px;
            background: var(--input);
            color: var(--text);
        }
        input::placeholder, textarea::placeholder { color: var(--muted); }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
        }
        .actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 18px;
        }
        .btn {
            display: inline-block;
            border: 0;
            border-radius: 12px;
            padding: 12px 18px;
            font-weight: 700;
            cursor: pointer;
            text-decoration: none;
            font-size: 15px;
        }
        .btn-primary { background: var(--accent); color: #fff; }
        .btn-primary:hover { background: var(--accent-dark); }
        .btn-secondary { background: var(--soft); color: #c4b5fd; border: 1px solid var(--border); }
        .btn-danger { background: #3a1722; color: #fda4af; border: 1px solid #5b2231; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
            margin: 18px 0 24px;
        }
        .stat {
            background: var(--input);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px;
        }
        .stat strong {
            display: block;
            font-size: 26px;
            margin-top: 8px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            font-size: 14px;
        }
        th, td {
            border-bottom: 1px solid var(--border);
            text-align: left;
            padding: 12px 10px;
            vertical-align: top;
        }
        th { background: var(--soft); }
        .tag {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
        }
        .tag-pending { background: #3d2f0d; color: #facc15; }
        .tag-yes { background: #1f2937; color: #86efac; }
        .tag-no { background: #3a1722; color: #fda4af; }
        .footer-note {
            margin-top: 14px;
            font-size: 13px;
            color: var(--muted);
            text-align: center;
        }
        .footer-note a { color: #c4b5fd; }
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 14px;
        }
        .link-box {
            font-size: 12px;
            color: var(--muted);
            word-break: break-all;
        }
        .event-card {
            display: block;
            background: var(--input);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 12px;
            color: var(--text);
            text-decoration: none;
        }
        .event-card:hover { border-color: var(--accent); }
        .flash {
            background: var(--soft);
            border: 1px solid var(--border);
            color: #c4b5fd;
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 16px;
        }
        .error-text { color: #fda4af; margin-bottom: 16px; }
    </style>
</head>
<body>
    <div class="wrap">
        {{ content|safe }}
    </div>
</body>
</html>
"""


def render_page(title: str, content: str):
    return render_template_string(BASE_HTML, title=title, content=content)


def topbar() -> str:
    if not g.usuario:
        return ""
    config_link = f'<a href="{url_for("configuracion")}">Configuración</a>&nbsp;·&nbsp;' if g.usuario.es_admin else ""
    return f"""
    <div class="topbar">
        <a href="{url_for('eventos_lista')}">AutoConfirm</a>
        <div>
            <span class="muted">{escape(g.usuario.email)} · {escape(g.usuario.organizacion.nombre)}</span>
            &nbsp;·&nbsp;
            {config_link}
            <a href="{url_for('logout')}">Cerrar sesión</a>
        </div>
    </div>
    """


def status_badge(status: str) -> str:
    normalized = (status or "Pendiente").strip().lower()
    if normalized == "confirmado":
        return '<span class="tag tag-yes">Confirmado</span>'
    if normalized == "rechazado":
        return '<span class="tag tag-no">No asistirá</span>'
    return '<span class="tag tag-pending">Pendiente</span>'


# --- Sesión / autenticación -------------------------------------------------


@app.before_request
def cargar_usuario():
    g.db = Session()
    g.usuario = None
    usuario_id = session.get("usuario_id")
    if usuario_id:
        g.usuario = g.db.get(Usuario, usuario_id)


@app.teardown_appcontext
def cerrar_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.usuario:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.usuario:
            return redirect(url_for("login", next=request.path))
        if not g.usuario.es_admin:
            return render_page("No autorizado", f'{topbar()}<div class="card"><h1>No autorizado</h1><p class="muted">Solo un administrador de tu empresa puede ver esta página.</p></div>'), 403
        return view(*args, **kwargs)

    return wrapped


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if g.usuario:
        return redirect(url_for("eventos_lista"))

    error = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        usuario = g.db.query(Usuario).filter_by(email=email, activo=True).first()
        if usuario and usuario.check_password(password):
            session.clear()
            session["usuario_id"] = usuario.id
            destino = request.args.get("next") or url_for("eventos_lista")
            return redirect(destino)
        error = "Correo o contraseña incorrectos."

    error_html = f'<p class="error-text">{escape(error)}</p>' if error else ""
    content = f"""
    <div class="hero">
        <div class="pill">AutoConfirm</div>
        <h1>Iniciar sesión</h1>
    </div>
    <div class="card">
        {error_html}
        <form method="post">
            <div class="field">
                <label for="email">Correo</label>
                <input type="email" name="email" id="email" required autofocus>
            </div>
            <div class="field">
                <label for="password">Contraseña</label>
                <input type="password" name="password" id="password" required>
            </div>
            <div class="actions">
                <button class="btn btn-primary" type="submit">Entrar</button>
            </div>
        </form>
    </div>
    <div class="footer-note"><a href="/privacy">Privacidad</a> · <a href="/terms">Términos de servicio</a></div>
    """
    return render_page("Iniciar sesión", content)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def home():
    return redirect(url_for("eventos_lista") if g.usuario else url_for("login"))


# --- Eventos -----------------------------------------------------------------


def eventos_visibles(usuario: Usuario):
    todos = g.db.query(Evento).filter_by(organizacion_id=usuario.organizacion_id).all()
    return [e for e in todos if e.puede_ver(usuario)]


@app.route("/eventos", methods=["GET", "POST"])
@login_required
def eventos_lista():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        fecha_raw = request.form.get("fecha_evento", "").strip()
        if nombre:
            fecha_evento = None
            if fecha_raw:
                try:
                    fecha_evento = datetime.strptime(fecha_raw, "%Y-%m-%d")
                except ValueError:
                    fecha_evento = None
            nuevo = Evento(
                organizacion_id=g.usuario.organizacion_id,
                creado_por_id=g.usuario.id,
                nombre=nombre,
                fecha_evento=fecha_evento,
            )
            g.db.add(nuevo)
            g.db.commit()
            return redirect(url_for("evento_detalle", evento_id=nuevo.id))

    eventos = sorted(eventos_visibles(g.usuario), key=lambda e: e.creado_en, reverse=True)

    rows = []
    for evento in eventos:
        total = len(evento.invitados)
        fecha = evento.fecha_evento.strftime("%Y-%m-%d") if evento.fecha_evento else "Sin fecha"
        rows.append(
            f"""
            <a class="event-card" href="{url_for('evento_detalle', evento_id=evento.id)}">
                <strong>{escape(evento.nombre)}</strong>
                <div class="muted">{escape(fecha)} · {total} invitado(s)</div>
            </a>
            """
        )
    if not rows:
        rows.append('<p class="muted">Todavía no tienes eventos. Crea el primero abajo.</p>')

    content = f"""
    {topbar()}
    <div class="hero">
        <div class="pill">Mis eventos</div>
        <h1>Eventos</h1>
    </div>

    <div class="card" style="margin-bottom:18px;">
        {''.join(rows)}
    </div>

    <div class="card">
        <h2>Crear nuevo evento</h2>
        <form method="post">
            <div class="grid">
                <div class="field">
                    <label for="nombre">Nombre del evento</label>
                    <input type="text" name="nombre" id="nombre" placeholder="Ej. Boda Ana y Luis" required>
                </div>
                <div class="field">
                    <label for="fecha_evento">Fecha (opcional)</label>
                    <input type="date" name="fecha_evento" id="fecha_evento">
                </div>
            </div>
            <div class="actions">
                <button class="btn btn-primary" type="submit">Crear evento</button>
            </div>
        </form>
    </div>
    """
    return render_page("Eventos", content)


def cargar_evento_o_404(evento_id: int):
    evento = g.db.get(Evento, evento_id)
    if not evento or not evento.puede_ver(g.usuario):
        return None
    return evento


@app.route("/eventos/<int:evento_id>")
@login_required
def evento_detalle(evento_id):
    evento = cargar_evento_o_404(evento_id)
    if not evento:
        return render_page("No encontrado", f'{topbar()}<div class="card"><h1>Evento no encontrado</h1></div>'), 404

    invitados = sorted(evento.invitados, key=lambda i: i.id)
    total = len(invitados)
    confirmados = sum(1 for i in invitados if i.confirmacion == "Confirmado")
    rechazados = sum(1 for i in invitados if i.confirmacion == "Rechazado")
    pendientes = total - confirmados - rechazados
    acompanantes = sum(int(i.acompanantes or 0) for i in invitados if i.confirmacion == "Confirmado")
    public_base = request.host_url.rstrip("/")

    rows = []
    for item in invitados:
        fecha = item.fecha_respuesta.strftime("%Y-%m-%d %H:%M") if item.fecha_respuesta else "—"
        enlace_relativo = f"/confirmar?id={item.uuid}"
        enlace_completo = f"{public_base}{enlace_relativo}"
        enviado = "Sí" if item.mensaje_enviado == "Si" else "No"
        rows.append(
            f"""
            <tr>
                <td>{escape(item.nombre or '')}</td>
                <td>{escape(item.telefono or '') or '—'}</td>
                <td>{status_badge(item.confirmacion)}</td>
                <td>{int(item.acompanantes or 0)}</td>
                <td>{enviado}</td>
                <td>{fecha}</td>
                <td>{escape(item.notas or '') or '—'}</td>
                <td>
                    <a href="{enlace_relativo}" target="_blank">Abrir enlace</a>
                    <div class="link-box">{enlace_completo}</div>
                </td>
            </tr>
            """
        )
    if not rows:
        rows.append('<tr><td colspan="8">Todavía no hay invitados cargados. Sube un Excel abajo.</td></tr>')

    puede_administrar = evento.creado_por_id == g.usuario.id or g.usuario.es_admin
    colaboradores_html = ""
    if puede_administrar:
        colaboradores_rows = []
        for colaborador in evento.colaboradores:
            colaboradores_rows.append(
                f"""
                <li>{escape(colaborador.usuario.email)}
                    <form method="post" action="{url_for('evento_quitar_colaborador', evento_id=evento.id, usuario_id=colaborador.usuario_id)}" style="display:inline;">
                        <button class="btn btn-secondary" type="submit" style="padding:2px 8px;font-size:12px;">Quitar</button>
                    </form>
                </li>
                """
            )
        colaboradores_html = f"""
        <div class="card" style="margin-top:18px;">
            <h2>Compartir este evento</h2>
            <p class="muted">Dale acceso a otro planner de tu misma empresa para que vea y administre este evento.</p>
            <ul>{''.join(colaboradores_rows) or '<li class="muted">Nadie más tiene acceso todavía.</li>'}</ul>
            <form method="post" action="{url_for('evento_compartir', evento_id=evento.id)}">
                <div class="grid">
                    <div class="field">
                        <label for="email_colaborador">Correo del planner</label>
                        <input type="email" name="email" id="email_colaborador" required>
                    </div>
                </div>
                <div class="actions">
                    <button class="btn btn-secondary" type="submit">Compartir</button>
                </div>
            </form>
        </div>
        """

    content = f"""
    {topbar()}
    <div class="hero">
        <div class="pill">{escape(evento.nombre)}</div>
        <h1>Invitados</h1>
    </div>

    <div class="stats">
        <div class="stat"><span>Total invitados</span><strong>{total}</strong></div>
        <div class="stat"><span>Confirmados</span><strong>{confirmados}</strong></div>
        <div class="stat"><span>No asistirán</span><strong>{rechazados}</strong></div>
        <div class="stat"><span>Pendientes</span><strong>{pendientes}</strong></div>
        <div class="stat"><span>Acompañantes</span><strong>{acompanantes}</strong></div>
    </div>

    <div class="card">
        <div class="toolbar">
            <h2 style="margin:0;">Lista de invitados</h2>
            <div class="actions">
                <a class="btn btn-secondary" href="{url_for('evento_exportar_csv', evento_id=evento.id)}">Exportar CSV</a>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Nombre</th><th>Teléfono</th><th>Estado</th><th>Acomp.</th>
                    <th>Enviado</th><th>Respondió</th><th>Notas</th><th>Enlace</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>

    <div class="card" style="margin-top:18px;">
        <h2>Cargar invitados (Excel)</h2>
        <p class="muted">El archivo debe tener las columnas "Nombre" y "Telefono".</p>
        <form method="post" action="{url_for('evento_cargar', evento_id=evento.id)}" enctype="multipart/form-data">
            <div class="grid">
                <div class="field">
                    <label for="archivo">Archivo .xlsx</label>
                    <input type="file" name="archivo" id="archivo" accept=".xlsx,.xls" required>
                </div>
                <div class="field">
                    <label for="prefijo_pais">Prefijo país</label>
                    <input type="text" name="prefijo_pais" id="prefijo_pais" value="52">
                </div>
            </div>
            <div class="actions">
                <button class="btn btn-secondary" type="submit">Cargar</button>
            </div>
        </form>
    </div>

    <div class="card" style="margin-top:18px;">
        <h2>Enviar invitaciones por WhatsApp</h2>
        <p class="muted">Manda la invitación a los invitados que todavía no la han recibido.</p>
        <form method="post" action="{url_for('evento_enviar', evento_id=evento.id)}">
            <div class="actions">
                <button class="btn btn-primary" type="submit">Enviar invitaciones pendientes</button>
            </div>
        </form>
    </div>

    {colaboradores_html}
    """
    return render_page(f"Evento: {evento.nombre}", content)


@app.route("/eventos/<int:evento_id>/cargar", methods=["POST"])
@login_required
def evento_cargar(evento_id):
    evento = cargar_evento_o_404(evento_id)
    if not evento:
        return render_page("No encontrado", f'{topbar()}<div class="card"><h1>Evento no encontrado</h1></div>'), 404

    archivo = request.files.get("archivo")
    prefijo_pais = (request.form.get("prefijo_pais", "52") or "52").strip()
    if not archivo or archivo.filename == "":
        return redirect(url_for("evento_detalle", evento_id=evento.id))

    try:
        df = pd.read_excel(archivo, dtype={"Telefono": str})
    except Exception:
        return render_page(
            "Error al leer el Excel",
            f'{topbar()}<div class="card"><h1>No se pudo leer el archivo</h1><p class="muted">Verifica que sea un .xlsx válido.</p></div>',
        ), 400

    faltantes = REQUIRED_COLUMNS - set(df.columns)
    if faltantes:
        return render_page(
            "Formato inválido",
            f'{topbar()}<div class="card"><h1>Faltan columnas</h1><p class="muted">Faltan: {escape(", ".join(sorted(faltantes)))}</p></div>',
        ), 400

    df["Nombre"] = df["Nombre"].fillna("").astype(str).str.strip()
    df["Telefono"] = df["Telefono"].fillna("").astype(str).str.strip()

    existentes = {(i.nombre, i.telefono) for i in evento.invitados}
    for _, row in df.iterrows():
        nombre, telefono = row["Nombre"], row["Telefono"]
        if not nombre or (nombre, telefono) in existentes:
            continue
        nuevo = Invitado(
            evento_id=evento.id,
            nombre=nombre,
            telefono=telefono,
            uuid=str(uuid.uuid4()),
            confirmacion="Pendiente",
            acompanantes=0,
            mensaje_enviado="No",
            notas="",
        )
        g.db.add(nuevo)
        existentes.add((nombre, telefono))

    g.db.commit()
    return redirect(url_for("evento_detalle", evento_id=evento.id))


@app.route("/eventos/<int:evento_id>/enviar", methods=["POST"])
@login_required
def evento_enviar(evento_id):
    evento = cargar_evento_o_404(evento_id)
    if not evento:
        return render_page("No encontrado", f'{topbar()}<div class="card"><h1>Evento no encontrado</h1></div>'), 404

    organizacion = evento.organizacion
    if not (organizacion.twilio_account_sid and organizacion.twilio_auth_token and organizacion.twilio_whatsapp_from):
        return render_page(
            "Falta configuración",
            f'{topbar()}<div class="card"><h1>Falta configurar Twilio</h1>'
            f'<p class="muted">Tu organización todavía no tiene credenciales de Twilio registradas. Contacta al administrador.</p></div>',
        ), 400

    confirmation_base_url = f"{request.host_url.rstrip('/')}/confirmar"
    hilo = threading.Thread(
        target=enviar_invitaciones_evento,
        args=(evento.id, confirmation_base_url),
        daemon=True,
    )
    hilo.start()

    content = f"""
    {topbar()}
    <div class="card hero">
        <div class="pill">Envío iniciado</div>
        <h1>Mandando invitaciones…</h1>
        <p class="muted">Esto corre en segundo plano. Actualiza esta página en unos segundos para ver el progreso.</p>
        <div class="actions" style="justify-content:center;">
            <a class="btn btn-primary" href="{url_for('evento_detalle', evento_id=evento.id)}">Volver al evento</a>
        </div>
    </div>
    """
    return render_page("Enviando invitaciones", content)


@app.route("/eventos/<int:evento_id>/compartir", methods=["POST"])
@login_required
def evento_compartir(evento_id):
    evento = cargar_evento_o_404(evento_id)
    if not evento or not (evento.creado_por_id == g.usuario.id or g.usuario.es_admin):
        return render_page("No autorizado", f'{topbar()}<div class="card"><h1>No autorizado</h1></div>'), 403

    email = request.form.get("email", "").strip().lower()
    colaborador = g.db.query(Usuario).filter_by(email=email, organizacion_id=g.usuario.organizacion_id).first()
    if colaborador and colaborador.id != evento.creado_por_id:
        ya_existe = any(c.usuario_id == colaborador.id for c in evento.colaboradores)
        if not ya_existe:
            g.db.add(EventoColaborador(evento_id=evento.id, usuario_id=colaborador.id))
            g.db.commit()

    return redirect(url_for("evento_detalle", evento_id=evento.id))


@app.route("/eventos/<int:evento_id>/colaboradores/<int:usuario_id>/quitar", methods=["POST"])
@login_required
def evento_quitar_colaborador(evento_id, usuario_id):
    evento = cargar_evento_o_404(evento_id)
    if not evento or not (evento.creado_por_id == g.usuario.id or g.usuario.es_admin):
        return render_page("No autorizado", f'{topbar()}<div class="card"><h1>No autorizado</h1></div>'), 403

    g.db.query(EventoColaborador).filter_by(evento_id=evento.id, usuario_id=usuario_id).delete()
    g.db.commit()
    return redirect(url_for("evento_detalle", evento_id=evento.id))


@app.route("/eventos/<int:evento_id>/exportar_csv")
@login_required
def evento_exportar_csv(evento_id):
    evento = cargar_evento_o_404(evento_id)
    if not evento:
        return render_page("No encontrado", f'{topbar()}<div class="card"><h1>Evento no encontrado</h1></div>'), 404

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Nombre", "Telefono", "Estado", "Acompanantes", "FechaRespuesta", "Notas", "UUID"])
    for item in evento.invitados:
        fecha = item.fecha_respuesta.strftime("%Y-%m-%d %H:%M:%S") if item.fecha_respuesta else ""
        writer.writerow([
            item.nombre or "", item.telefono or "", item.confirmacion or "Pendiente",
            item.acompanantes or 0, fecha, item.notas or "", item.uuid or "",
        ])

    csv_data = buffer.getvalue()
    buffer.close()
    nombre_archivo = f"invitados_{evento.id}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )


@app.route("/configuracion", methods=["GET", "POST"])
@admin_required
def configuracion():
    organizacion = g.db.get(Organizacion, g.usuario.organizacion_id)
    guardado = False

    if request.method == "POST":
        organizacion.twilio_account_sid = request.form.get("twilio_account_sid", "").strip()
        organizacion.twilio_whatsapp_from = request.form.get("twilio_whatsapp_from", "").strip()
        organizacion.twilio_content_sid = request.form.get("twilio_content_sid", "").strip()

        nuevo_token = request.form.get("twilio_auth_token", "").strip()
        if nuevo_token:
            organizacion.twilio_auth_token = nuevo_token

        g.db.commit()
        guardado = True

    es_sandbox = organizacion.twilio_whatsapp_from.strip() == "whatsapp:+14155238886"
    sid_actual = organizacion.twilio_account_sid or ""
    sid_enmascarado = f"{sid_actual[:6]}…{sid_actual[-4:]}" if len(sid_actual) > 10 else (sid_actual or "— sin configurar —")
    token_configurado = bool(organizacion.twilio_auth_token_enc)

    aviso_sandbox = ""
    if es_sandbox:
        aviso_sandbox = """
        <div class="flash">
            <strong>Usando el sandbox de prueba de Twilio.</strong>
            Solo funciona con números que hicieron "join" al sandbox, y expira a los 3 días.
            Para mandar mensajes a tus invitados reales sin que se unan primero, necesitas en Twilio
            un <strong>WhatsApp Sender</strong> propio aprobado (número de producción) — eso puede
            implicar costo y verificación de negocio en Meta. Mientras tanto, el sandbox sirve para seguir probando.
        </div>
        """
    elif not sid_actual:
        aviso_sandbox = """
        <div class="flash">
            Todavía no has configurado Twilio para esta organización. Sin esto, el botón
            "Enviar invitaciones" de tus eventos no va a funcionar.
        </div>
        """

    guardado_html = '<p class="flash">Configuración guardada.</p>' if guardado else ""

    content = f"""
    {topbar()}
    <div class="hero">
        <div class="pill">Configuración</div>
        <h1>Credenciales de Twilio</h1>
        <p class="muted">Esto aplica a todos los eventos de {escape(organizacion.nombre)}.</p>
    </div>

    {aviso_sandbox}
    {guardado_html}

    <div class="card">
        <form method="post">
            <div class="field">
                <label for="twilio_account_sid">Twilio Account SID</label>
                <input type="text" name="twilio_account_sid" id="twilio_account_sid" value="{escape(sid_actual)}" placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" required>
            </div>
            <div class="field">
                <label for="twilio_auth_token">Twilio Auth Token</label>
                <input type="password" name="twilio_auth_token" id="twilio_auth_token" placeholder="{'(dejar en blanco para no cambiarlo)' if token_configurado else 'Pega tu Auth Token'}">
                <p class="muted" style="margin-top:6px;">Actual: {'configurado (oculto)' if token_configurado else 'sin configurar'}. Se guarda cifrado.</p>
            </div>
            <div class="field">
                <label for="twilio_whatsapp_from">Número de WhatsApp (From)</label>
                <input type="text" name="twilio_whatsapp_from" id="twilio_whatsapp_from" value="{escape(organizacion.twilio_whatsapp_from or '')}" placeholder="whatsapp:+14155238886" required>
            </div>
            <div class="field">
                <label for="twilio_content_sid">Content SID de plantilla aprobada (opcional)</label>
                <input type="text" name="twilio_content_sid" id="twilio_content_sid" value="{escape(organizacion.twilio_content_sid or '')}" placeholder="HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx">
                <p class="muted" style="margin-top:6px;">Sin esto, se manda texto libre: solo llega dentro del sandbox o de una conversación ya abierta de 24h.</p>
            </div>
            <div class="actions">
                <button class="btn btn-primary" type="submit">Guardar</button>
            </div>
        </form>
    </div>

    <div class="card" style="margin-top:18px;">
        <h2>Account SID actual</h2>
        <p class="muted">{escape(sid_enmascarado)}</p>
    </div>
    """
    return render_page("Configuración", content)


# --- Páginas públicas (sin login) --------------------------------------------


@app.route("/confirmar")
def confirmar():
    invitado_uuid = request.args.get("id", "").strip()
    if not invitado_uuid:
        return render_page(
            "Enlace inválido",
            """
            <div class="card hero">
                <div class="pill">AutoConfirm</div>
                <h1>Enlace inválido</h1>
                <p class="muted">Falta el identificador del invitado.</p>
            </div>
            """,
        ), 400

    invitado = g.db.query(Invitado).filter_by(uuid=invitado_uuid).first()

    if not invitado:
        return render_page(
            "Invitado no encontrado",
            """
            <div class="card hero">
                <div class="pill">AutoConfirm</div>
                <h1>No encontramos este enlace</h1>
                <p class="muted">Puede que el enlace sea incorrecto o ya no esté disponible.</p>
            </div>
            """,
        ), 404

    selected_yes = "selected" if invitado.confirmacion == "Confirmado" else ""
    selected_no = "selected" if invitado.confirmacion == "Rechazado" else ""
    confirmed_section = ""
    if invitado.confirmacion in {"Confirmado", "Rechazado"}:
        confirmed_section = f'<p class="muted">Tu respuesta actual: {status_badge(invitado.confirmacion)}.</p>'

    nombre_evento = invitado.evento.nombre if invitado.evento else ""

    content = f"""
    <div class="hero">
        <div class="pill">{escape(nombre_evento) or "Confirmación de asistencia"}</div>
        <h1>Hola, {escape(invitado.nombre or '')}</h1>
        <p class="muted">Por favor confirma tu asistencia. Tu respuesta se guardará automáticamente.</p>
        {confirmed_section}
    </div>

    <div class="card">
        <form action="/submit_form" method="post">
            <input type="hidden" name="uuid" value="{escape(invitado.uuid)}">

            <div class="field">
                <label for="asistencia">¿Asistirás al evento?</label>
                <select name="asistencia" id="asistencia" required>
                    <option value="si" {selected_yes}>Sí, asistiré</option>
                    <option value="no" {selected_no}>No podré asistir</option>
                </select>
            </div>

            <div class="grid">
                <div class="field">
                    <label for="acompanantes">Número de acompañantes</label>
                    <input type="number" name="acompanantes" id="acompanantes" value="{int(invitado.acompanantes or 0)}" min="0" max="20">
                </div>
                <div class="field">
                    <label for="telefono">Teléfono de referencia</label>
                    <input type="text" id="telefono" value="{escape(invitado.telefono or '')}" disabled>
                </div>
            </div>

            <div class="field">
                <label for="notas">Notas (opcional)</label>
                <textarea name="notas" id="notas" rows="4" placeholder="Ej. Llegaré un poco tarde, llevo 2 niños, etc.">{escape(invitado.notas or '')}</textarea>
            </div>

            <div class="actions">
                <button class="btn btn-primary" type="submit">Guardar respuesta</button>
            </div>
        </form>
    </div>
    <div class="footer-note">Powered by AutoConfirm</div>
    """
    return render_page("Confirmación de asistencia", content)


@app.route("/submit_form", methods=["POST"])
@limiter.limit("10 per minute")
def submit_form():
    invitado_uuid = request.form.get("uuid", "").strip()
    asistencia = request.form.get("asistencia", "").strip().lower()
    acompanantes_raw = request.form.get("acompanantes", "0").strip()
    notas = request.form.get("notas", "").strip()

    try:
        acompanantes = max(0, int(acompanantes_raw or 0))
    except ValueError:
        acompanantes = 0

    invitado = g.db.query(Invitado).filter_by(uuid=invitado_uuid).first()

    if not invitado:
        return render_page(
            "Error",
            """
            <div class="card hero">
                <h1>No se pudo registrar tu respuesta</h1>
                <p class="muted">El invitado no existe o el enlace ya no es válido.</p>
            </div>
            """,
        ), 400

    invitado.confirmacion = "Confirmado" if asistencia == "si" else "Rechazado"
    invitado.acompanantes = acompanantes if asistencia == "si" else 0
    invitado.notas = notas
    invitado.fecha_respuesta = datetime.now()
    g.db.commit()

    content = f"""
    <div class="card hero">
        <div class="pill">Respuesta registrada</div>
        <h1>¡Gracias por tu confirmación!</h1>
        <p>Hemos guardado tu respuesta correctamente.</p>
        <p class="muted">Estado: {status_badge('Confirmado' if asistencia == 'si' else 'Rechazado')}</p>
        <div class="actions" style="justify-content:center;">
            <a class="btn btn-secondary" href="/confirmar?id={escape(invitado_uuid)}">Volver a ver mi respuesta</a>
        </div>
    </div>
    """
    return render_page("Respuesta registrada", content)


@app.route("/privacy")
def privacy():
    content = """
    <div class="hero">
        <div class="pill">AutoConfirm</div>
        <h1>Política de privacidad</h1>
        <p class="muted">Última actualización: marzo 2026.</p>
    </div>

    <div class="card">
        <p>AutoConfirm recopila únicamente la información necesaria para gestionar invitaciones y confirmaciones de asistencia a eventos, como nombre, número de teléfono y respuesta del invitado.</p>

        <p>Esta información se utiliza exclusivamente para el envío de invitaciones, recepción de confirmaciones y visualización de resultados por parte del organizador del evento.</p>

        <p>AutoConfirm no vende ni comparte datos personales con terceros ajenos a la operación del servicio, salvo cuando sea necesario para el funcionamiento técnico de plataformas utilizadas, como WhatsApp Business Platform y servicios de alojamiento.</p>

        <p>Los datos se conservan solo durante el tiempo necesario para operar el evento y dar seguimiento a las confirmaciones.</p>

        <p>Si deseas solicitar la eliminación o modificación de tus datos, puedes contactar al responsable del evento o al administrador del sistema.</p>
    </div>
    """
    return render_page("Política de privacidad", content)


@app.route("/terms")
def terms():
    content = """
    <div class="hero">
        <div class="pill">AutoConfirm</div>
        <h1>Términos de servicio</h1>
        <p class="muted">Última actualización: octubre 2026.</p>
    </div>

    <div class="card">
        <h2>1. El servicio</h2>
        <p>AutoConfirm es una herramienta para que empresas organizadoras de eventos (la "Organización") gestionen invitaciones, confirmaciones de asistencia y el envío de mensajes de WhatsApp a sus propios invitados, a través de un panel web y de la plataforma de WhatsApp Business operada por un proveedor externo (Twilio u otro BSP autorizado).</p>

        <h2>2. Cuentas y acceso</h2>
        <p>Cada Organización recibe una o más cuentas de usuario para su personal. La Organización es responsable de mantener la confidencialidad de sus credenciales y de toda actividad realizada desde sus cuentas, así como de revocar el acceso a personal que deje de colaborar con ella.</p>

        <h2>3. Uso aceptable de WhatsApp</h2>
        <p>La Organización es la única responsable de contar con el consentimiento de las personas a quienes les envía mensajes a través de AutoConfirm. Queda prohibido usar el servicio para enviar mensajes no solicitados (spam), contenido engañoso, o a listas de contactos que no hayan autorizado recibir comunicación de la Organización. El incumplimiento de las políticas de WhatsApp Business puede resultar en el bloqueo del número de la Organización por parte de Meta/Twilio, fuera del control de AutoConfirm.</p>

        <h2>4. Credenciales de terceros (Twilio)</h2>
        <p>Cuando la Organización proporciona sus propias credenciales de Twilio (u otro proveedor de WhatsApp), es responsable de la vigencia, costos y cumplimiento de los términos de dicho proveedor. AutoConfirm almacena estas credenciales cifradas, pero no es responsable por suspensiones, costos o políticas impuestas por el proveedor externo.</p>

        <h2>5. Pagos</h2>
        <p>Las condiciones comerciales (precio, periodicidad, forma de pago) se acuerdan directamente entre AutoConfirm y cada Organización cliente, fuera de esta plataforma, salvo que se indique lo contrario por escrito.</p>

        <h2>6. Propiedad de los datos</h2>
        <p>Los datos de invitados que la Organización carga al servicio (nombres, teléfonos, respuestas) son propiedad de la Organización. AutoConfirm los trata conforme a su <a href="/privacy">política de privacidad</a> y los conserva mientras la cuenta esté activa.</p>

        <h2>7. Límite de responsabilidad</h2>
        <p>AutoConfirm se ofrece "tal cual". No garantizamos disponibilidad ininterrumpida del servicio ni de los proveedores externos (Twilio, Meta, Render) de los que depende. En la máxima medida permitida por la ley, AutoConfirm no será responsable por daños indirectos derivados del uso del servicio.</p>

        <h2>8. Terminación</h2>
        <p>Cualquiera de las partes puede terminar el servicio con aviso previo. Al terminar, la Organización puede solicitar la exportación de sus datos antes de su eliminación.</p>

        <h2>9. Cambios a estos términos</h2>
        <p>Podemos actualizar estos términos ocasionalmente. Los cambios relevantes se notificarán a los administradores de cada Organización.</p>

        <h2>10. Ley aplicable</h2>
        <p>Estos términos se rigen por las leyes de los Estados Unidos Mexicanos.</p>
    </div>
    """
    return render_page("Términos de servicio", content)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
