from datetime import datetime
from functools import wraps
from pathlib import Path
import os
import secrets

import csv
import io

from dotenv import load_dotenv
from flask import Flask, Response, redirect, render_template_string, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from markupsafe import escape
from sqlalchemy import Column, DateTime, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "invitados.db"
DATABASE_URL = (
    os.getenv("AUTOCONFIRM_DATABASE_URL", "").strip()
    or os.getenv("DATABASE_URL", "").strip()
)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()

Base = declarative_base()


class Invitado(Base):
    __tablename__ = "invitados"

    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    telefono = Column(String)
    uuid = Column(String, unique=True)
    confirmacion = Column(String, default="Pendiente")
    acompanantes = Column(Integer, default=0)
    mensaje_enviado = Column(String, default="No")
    fecha_respuesta = Column(DateTime, nullable=True)
    notas = Column(String, default="")


if DATABASE_URL:
    normalized_database_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # Fuerza el driver psycopg2 explícitamente: versiones nuevas de SQLAlchemy
    # intentan usar psycopg (v3) por default para "postgresql://" a secas, y
    # esta app instala psycopg2-binary, no psycopg v3.
    if normalized_database_url.startswith("postgresql://"):
        normalized_database_url = normalized_database_url.replace(
            "postgresql://", "postgresql+psycopg2://", 1
        )
    engine = create_engine(normalized_database_url)
else:
    DATA_DIR.mkdir(exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}")

Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


def ensure_schema():
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("invitados")}

    with engine.begin() as connection:
        migrations = []

        if "mensaje_enviado" not in columns:
            migrations.append("ALTER TABLE invitados ADD COLUMN mensaje_enviado VARCHAR DEFAULT 'No'")
        if "fecha_respuesta" not in columns:
            migrations.append("ALTER TABLE invitados ADD COLUMN fecha_respuesta TIMESTAMP")
        if "notas" not in columns:
            migrations.append("ALTER TABLE invitados ADD COLUMN notas VARCHAR DEFAULT ''")

        for statement in migrations:
            connection.execute(text(statement))


ensure_schema()

app = Flask(__name__)
limiter = Limiter(key_func=get_remote_address, app=app, storage_uri="memory://")

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
            max-width: 820px;
            margin: 0 auto;
            padding: 24px 16px 40px;
        }
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


def status_badge(status: str) -> str:
    normalized = (status or "Pendiente").strip().lower()
    if normalized == "confirmado":
        return '<span class="tag tag-yes">Confirmado</span>'
    if normalized == "rechazado":
        return '<span class="tag tag-no">No asistirá</span>'
    return '<span class="tag tag-pending">Pendiente</span>'


def require_admin_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not ADMIN_PASSWORD:
            return Response(
                "El dashboard está deshabilitado: falta configurar ADMIN_PASSWORD en el servidor.",
                status=503,
            )

        auth = request.authorization
        valid = bool(auth) and secrets.compare_digest(
            auth.username or "", ADMIN_USERNAME
        ) and secrets.compare_digest(auth.password or "", ADMIN_PASSWORD)

        if not valid:
            return Response(
                "Acceso restringido.",
                status=401,
                headers={"WWW-Authenticate": 'Basic realm="AutoConfirm Dashboard"'},
            )

        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def home():
    return redirect(url_for("dashboard"))


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

    session = Session()
    invitado = session.query(Invitado).filter_by(uuid=invitado_uuid).first()
    session.close()

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
        confirmed_section = f"""
        <p class="muted">Tu respuesta actual: {status_badge(invitado.confirmacion)}.</p>
        """

    content = f"""
    <div class="hero">
        <div class="pill">Confirmación de asistencia</div>
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

    session = Session()
    invitado = session.query(Invitado).filter_by(uuid=invitado_uuid).first()

    if not invitado:
        session.close()
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
    session.commit()
    session.close()

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


@app.route("/dashboard")
@require_admin_auth
def dashboard():
    session = Session()
    invitados = session.query(Invitado).order_by(Invitado.id.asc()).all()

    total = len(invitados)
    confirmados = sum(1 for item in invitados if item.confirmacion == "Confirmado")
    rechazados = sum(1 for item in invitados if item.confirmacion == "Rechazado")
    pendientes = total - confirmados - rechazados
    acompanantes = sum(int(item.acompanantes or 0) for item in invitados if item.confirmacion == "Confirmado")
    public_base = request.host_url.rstrip("/")

    rows = []
    for item in invitados:
        fecha = item.fecha_respuesta.strftime("%Y-%m-%d %H:%M") if item.fecha_respuesta else "—"
        enlace_relativo = f"/confirmar?id={escape(item.uuid)}"
        enlace_completo = f"{public_base}{enlace_relativo}"
        rows.append(
            f"""
            <tr>
                <td>{escape(item.nombre or '')}</td>
                <td>{escape(item.telefono or '') or '—'}</td>
                <td>{status_badge(item.confirmacion)}</td>
                <td>{int(item.acompanantes or 0)}</td>
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
        rows.append(
            """
            <tr>
                <td colspan="7">Todavía no hay invitados cargados en la base de datos.</td>
            </tr>
            """
        )

    content = f"""
    <div class="hero">
        <div class="pill">Panel AutoConfirm</div>
        <h1>Dashboard de confirmaciones</h1>
        <p class="muted">Vista rápida del estado actual de invitados y respuestas.</p>
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
            <div>
                <h2 style="margin-bottom:6px;">Invitados</h2>
                <p class="muted" style="margin-bottom:0;">Aquí podrás revisar quién ya respondió y ver el enlace completo individual.</p>
            </div>
            <div class="actions">
                <a class="btn btn-secondary" href="/exportar_csv">Exportar CSV</a>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Nombre</th>
                    <th>Teléfono</th>
                    <th>Estado</th>
                    <th>Acompañantes</th>
                    <th>Respondió</th>
                    <th>Notas</th>
                    <th>Enlace</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """
    session.close()
    return render_page("Dashboard AutoConfirm", content)


@app.route("/exportar_csv")
@require_admin_auth
def exportar_csv():
    session = Session()
    invitados = session.query(Invitado).order_by(Invitado.id.asc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Nombre", "Telefono", "Estado", "Acompanantes", "FechaRespuesta", "Notas", "UUID"])

    for item in invitados:
        fecha = item.fecha_respuesta.strftime("%Y-%m-%d %H:%M:%S") if item.fecha_respuesta else ""
        writer.writerow([
            item.nombre or "",
            item.telefono or "",
            item.confirmacion or "Pendiente",
            item.acompanantes or 0,
            fecha,
            item.notas or "",
            item.uuid or "",
        ])

    session.close()
    csv_data = buffer.getvalue()
    buffer.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=autoconfirm_resultados.csv"},
    )


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


if __name__ == "__main__":
    app.run(port=5000, debug=True)
