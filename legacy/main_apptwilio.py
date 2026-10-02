# OBSOLETO (2026-10-02): reemplazado por el dashboard web multi-tenant
# (ver app.py y twilio_sender.py en la raíz del proyecto). El envío por
# Twilio ya no vive en una app de escritorio; se conserva aquí solo como
# referencia histórica.
import json
import os
import re
import threading
import time
import tkinter as tk
import uuid
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

APP_NAME = "AutoConfirm"
APP_BG = "#111116"
CARD_BG = "#1A1B24"
ACCENT = "#7C3AED"
ACCENT_DARK = "#5B21B6"
SUCCESS = "#8B5CF6"
WARNING = "#A78BFA"
DANGER = "#F43F5E"
TEXT = "#F5F3FF"
MUTED = "#A1A1AA"
BORDER = "#2A2D3A"
INPUT_BG = "#242634"
INPUT_FG = "#F5F3FF"
INPUT_BORDER = "#34384A"
SOFT_BLUE = "#221A36"
SOFT_GREEN = "#20182D"
SOFT_YELLOW = "#261F33"
DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_TEMPLATE = DATA_DIR / "invitados.xlsx"
DB_PATH = DATA_DIR / "invitados.db"

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"

# Configuración por variables de entorno (ver .env.example en la raíz del
# proyecto). Nunca se hardcodean credenciales aquí.
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "").strip()
TWILIO_CONTENT_SID = os.getenv("TWILIO_CONTENT_SID", "").strip()
CONFIRMATION_BASE_URL = os.getenv("CONFIRMATION_BASE_URL", "https://autoconfirm.onrender.com/confirmar").strip()
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://autoconfirm.onrender.com/dashboard").strip()

DATABASE_URL = (
    os.getenv("AUTOCONFIRM_DATABASE_URL", "").strip()
    or os.getenv("DATABASE_URL", "").strip()
)

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
    if normalized_database_url.startswith("postgresql://"):
        normalized_database_url = normalized_database_url.replace(
            "postgresql://", "postgresql+psycopg2://", 1
        )
    engine = create_engine(normalized_database_url)
    DATABASE_MODE = "Postgres compartido"
else:
    DATA_DIR.mkdir(exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}")
    DATABASE_MODE = "SQLite local"

Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


def ensure_schema():
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("invitados")}
    migrations = []

    if "mensaje_enviado" not in columns:
        migrations.append("ALTER TABLE invitados ADD COLUMN mensaje_enviado VARCHAR DEFAULT 'No'")
    if "fecha_respuesta" not in columns:
        migrations.append("ALTER TABLE invitados ADD COLUMN fecha_respuesta TIMESTAMP")
    if "notas" not in columns:
        migrations.append("ALTER TABLE invitados ADD COLUMN notas VARCHAR DEFAULT ''")

    with engine.begin() as connection:
        for statement in migrations:
            connection.execute(text(statement))


ensure_schema()


class App:
    REQUIRED_COLUMNS = {"Nombre", "Telefono"}

    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("980x700")
        self.root.minsize(920, 640)
        self.root.configure(bg=APP_BG)

        self.file_path = ""
        self.contacts_df = pd.DataFrame()
        self.is_sending = False
        self.sent_contacts = 0
        self.failed_contacts = 0

        self.status_var = tk.StringVar(value="Carga tu archivo para comenzar.")
        self.summary_var = tk.StringVar(value="Sin archivo cargado")
        self.country_code_var = tk.StringVar(value="52")
        self.contacts_count_var = tk.StringVar(value="0 contactos")
        self.valid_count_var = tk.StringVar(value="0 válidos")
        self.invalid_count_var = tk.StringVar(value="0 observaciones")
        self.delay_var = tk.IntVar(value=2)

        self.account_sid_var = tk.StringVar(value=TWILIO_ACCOUNT_SID)
        self.auth_token_var = tk.StringVar(value=TWILIO_AUTH_TOKEN)
        self.from_number_var = tk.StringVar(value=TWILIO_WHATSAPP_FROM)
        self.content_sid_var = tk.StringVar(value=TWILIO_CONTENT_SID)
        self.link_var = tk.StringVar(value=CONFIRMATION_BASE_URL)
        self.dashboard_url_var = tk.StringVar(value=DASHBOARD_URL)

        self._configure_styles()
        self.create_widgets()

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Main.Horizontal.TProgressbar",
            troughcolor="#232533",
            background=ACCENT,
            bordercolor="#232533",
            lightcolor=ACCENT,
            darkcolor=ACCENT,
        )
        style.configure(
            "Treeview",
            background=INPUT_BG,
            fieldbackground=INPUT_BG,
            foreground=TEXT,
            rowheight=28,
            bordercolor=BORDER,
        )
        style.configure("Treeview.Heading", background=SOFT_BLUE, foreground=TEXT, relief="flat")
        style.map("Treeview", background=[("selected", "#312E81")], foreground=[("selected", "#FFFFFF")])

    def create_widgets(self):
        container = tk.Frame(self.root, bg=APP_BG)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        self._build_header(container)
        self._build_upload_card(container)
        self._build_bottom_section(container)
        self._build_middle_section(container)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=APP_BG)
        header.pack(fill="x", pady=(0, 12))

        tk.Label(header, text=APP_NAME, font=("Segoe UI", 24, "bold"), bg=APP_BG, fg=TEXT).pack(anchor="w")
        tk.Label(
            header,
            text="Carga tu lista, envía invitaciones y da seguimiento a confirmaciones desde una sola vista.",
            font=("Segoe UI", 10),
            bg=APP_BG,
            fg=MUTED,
        ).pack(anchor="w", pady=(6, 0))

    def _build_upload_card(self, parent):
        top_card = tk.Frame(parent, bg=CARD_BG, bd=1, relief="solid", highlightthickness=0)
        top_card.pack(fill="x", pady=(0, 12))

        title_row = tk.Frame(top_card, bg=CARD_BG)
        title_row.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(title_row, text="Base de invitados", font=("Segoe UI", 12, "bold"), bg=CARD_BG, fg=TEXT).pack(side="left")
        tk.Label(title_row, textvariable=self.summary_var, font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=SUCCESS).pack(side="right")

        file_row = tk.Frame(top_card, bg=CARD_BG)
        file_row.pack(fill="x", padx=12, pady=(0, 6))

        self.file_label = tk.Label(
            file_row,
            text="Ningún archivo seleccionado",
            bg=INPUT_BG,
            fg=MUTED,
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=8,
            anchor="w",
        )
        self.file_label.pack(side="left", fill="x", expand=True)

        tk.Button(
            file_row,
            text="Cargar archivo",
            command=self.select_file,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_DARK,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=8,
        ).pack(side="right", padx=(8, 0))

        settings_row = tk.Frame(top_card, bg=CARD_BG)
        settings_row.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(settings_row, text="Prefijo país", font=("Segoe UI", 10), bg=CARD_BG, fg=TEXT).pack(side="left")
        tk.Entry(
            settings_row,
            textvariable=self.country_code_var,
            width=8,
            justify="center",
            relief="solid",
            bd=1,
            bg=INPUT_BG,
            fg=INPUT_FG,
            insertbackground=INPUT_FG,
            highlightthickness=1,
            highlightbackground=INPUT_BORDER,
            highlightcolor=ACCENT,
        ).pack(side="left", padx=(8, 20))

        tk.Label(settings_row, text="Pausa entre mensajes (seg)", font=("Segoe UI", 10), bg=CARD_BG, fg=TEXT).pack(side="left")
        tk.Spinbox(
            settings_row,
            from_=1,
            to=15,
            textvariable=self.delay_var,
            width=8,
            justify="center",
            bg=INPUT_BG,
            fg=INPUT_FG,
            insertbackground=INPUT_FG,
            highlightthickness=1,
            highlightbackground=INPUT_BORDER,
            highlightcolor=ACCENT,
            buttonbackground=INPUT_BG,
        ).pack(side="left", padx=(8, 20))

        tk.Button(
            settings_row,
            text="Cargar ejemplo",
            command=self.load_default_template,
            bg=SOFT_BLUE,
            fg=ACCENT_DARK,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=7,
        ).pack(side="left")

        stats_row = tk.Frame(top_card, bg=CARD_BG)
        stats_row.pack(fill="x", padx=12, pady=(0, 10))

        self._stat_card(stats_row, "Contactos cargados", self.contacts_count_var, SOFT_BLUE, ACCENT_DARK).pack(side="left", fill="x", expand=True)
        self._stat_card(stats_row, "Válidos", self.valid_count_var, SOFT_GREEN, SUCCESS).pack(side="left", fill="x", expand=True, padx=8)
        self._stat_card(stats_row, "Observaciones", self.invalid_count_var, SOFT_YELLOW, WARNING).pack(side="left", fill="x", expand=True)

    def _build_middle_section(self, parent):
        middle_frame = tk.Frame(parent, bg=APP_BG)
        middle_frame.pack(fill="both", expand=True)

        left_card = tk.Frame(middle_frame, bg=CARD_BG, bd=1, relief="solid")
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(left_card, text="Mensaje de referencia", font=("Segoe UI", 12, "bold"), bg=CARD_BG, fg=TEXT).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Label(
            left_card,
            text="Aquí puedes dejar una nota breve de referencia para la operación del envío.",
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg=MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self.preview_text = scrolledtext.ScrolledText(
            left_card,
            wrap=tk.WORD,
            height=8,
            font=("Segoe UI", 10),
            relief="solid",
            borderwidth=1,
            bg=INPUT_BG,
            fg=INPUT_FG,
            insertbackground=INPUT_FG,
            padx=10,
            pady=10,
        )
        self.preview_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.preview_text.insert(
            "1.0",
            "Envío por Twilio (WhatsApp Business API vía BSP):\n\n"
            "1) Modo plantilla aprobada (recomendado)\n"
            "- Configura TWILIO_CONTENT_SID en el .env\n"
            "- La app mandará esa plantilla con:\n"
            "  variable 1 = nombre del invitado\n"
            "  variable 2 = link único de confirmación\n\n"
            "2) Modo mensaje libre (solo pruebas)\n"
            "- Si TWILIO_CONTENT_SID está vacío, se manda texto libre\n"
            "- Solo funciona en el sandbox de Twilio o dentro de una\n"
            "  sesión de 24h ya iniciada por el contacto\n",
        )

        right_card = tk.Frame(middle_frame, bg=CARD_BG, bd=1, relief="solid")
        right_card.pack(side="left", fill="both", expand=True, padx=(6, 0))

        tk.Label(right_card, text="Vista previa de contactos", font=("Segoe UI", 12, "bold"), bg=CARD_BG, fg=TEXT).pack(anchor="w", padx=16, pady=(16, 8))

        columns = ("Nombre", "Telefono")
        self.preview_table = ttk.Treeview(right_card, columns=columns, show="headings", height=8)
        self.preview_table.heading("Nombre", text="Nombre")
        self.preview_table.heading("Telefono", text="Teléfono")
        self.preview_table.column("Nombre", width=180)
        self.preview_table.column("Telefono", width=140)
        self.preview_table.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _build_bottom_section(self, parent):
        bottom_card = tk.Frame(parent, bg=CARD_BG, bd=1, relief="solid")
        bottom_card.pack(fill="both", pady=(12, 0))

        actions_row = tk.Frame(bottom_card, bg=CARD_BG)
        actions_row.pack(fill="x", padx=12, pady=(10, 6))

        self.send_button = tk.Button(
            actions_row,
            text="Enviar invitaciones",
            command=self.start_sending,
            bg=SUCCESS,
            fg="white",
            activebackground="#7C3AED",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=8,
        )
        self.send_button.pack(side="left")

        self.dashboard_button = tk.Button(
            actions_row,
            text="Abrir dashboard",
            command=self.open_dashboard,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_DARK,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=8,
        )
        self.dashboard_button.pack(side="left", padx=(8, 0))

        self.clear_data_button = tk.Button(
            actions_row,
            text="Borrar datos",
            command=self.clear_dashboard_data,
            bg=DANGER,
            fg="white",
            activebackground="#E11D48",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=8,
        )
        self.clear_data_button.pack(side="left", padx=(8, 0))

        ttk.Progressbar(bottom_card, style="Main.Horizontal.TProgressbar", variable=tk.DoubleVar(value=0))

        self.progress = ttk.Progressbar(bottom_card, style="Main.Horizontal.TProgressbar", mode="determinate")
        self.progress.pack(fill="x", padx=12, pady=(0, 6))

        status_row = tk.Frame(bottom_card, bg=CARD_BG)
        status_row.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(status_row, textvariable=self.status_var, font=("Segoe UI", 9), bg=CARD_BG, fg=MUTED).pack(side="left")

        tk.Label(bottom_card, text="Registro", font=("Segoe UI", 11, "bold"), bg=CARD_BG, fg=TEXT).pack(anchor="w", padx=16)
        self.log_text = scrolledtext.ScrolledText(
            bottom_card,
            wrap=tk.WORD,
            height=6,
            font=("Consolas", 9),
            relief="solid",
            borderwidth=1,
            bg=INPUT_BG,
            fg=INPUT_FG,
            insertbackground=INPUT_FG,
        )
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(6, 10))
        self.log_text.configure(state="disabled")

    def _stat_card(self, parent, title, variable, bg_color, fg_color):
        card = tk.Frame(parent, bg=bg_color, padx=12, pady=10)
        tk.Label(card, text=title, font=("Segoe UI", 9), bg=bg_color, fg=fg_color).pack(anchor="w")
        tk.Label(card, textvariable=variable, font=("Segoe UI", 13, "bold"), bg=bg_color, fg=fg_color).pack(anchor="w", pady=(4, 0))
        return card

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def set_status(self, message):
        self.status_var.set(message)

    def select_file(self):
        selected = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx;*.xls")])
        if not selected:
            return
        self.load_contacts(selected)

    def load_default_template(self):
        if not DEFAULT_TEMPLATE.exists():
            messagebox.showerror("Archivo no encontrado", f"No existe el archivo de ejemplo: {DEFAULT_TEMPLATE}")
            return
        self.load_contacts(str(DEFAULT_TEMPLATE))

    def load_contacts(self, path):
        try:
            df = pd.read_excel(path, dtype={"Telefono": str})
        except Exception as error:
            messagebox.showerror("Error al abrir Excel", str(error))
            return

        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            messagebox.showerror("Formato inválido", f"Faltan columnas requeridas: {', '.join(sorted(missing))}")
            return

        df = df.copy()
        df["Nombre"] = df["Nombre"].fillna("").astype(str).str.strip()
        df["Telefono"] = df["Telefono"].fillna("").astype(str).str.strip()
        df["Valido"] = df["Telefono"].apply(lambda phone: bool(re.sub(r"\D", "", phone)))
        df["uuid"] = ""

        session = Session()
        try:
            for index, row in df.iterrows():
                nombre = row["Nombre"]
                telefono = row["Telefono"]
                existente = session.query(Invitado).filter_by(nombre=nombre, telefono=telefono).first()
                if existente:
                    invitado_uuid = existente.uuid
                else:
                    invitado_uuid = str(uuid.uuid4())
                    nuevo = Invitado(
                        nombre=nombre,
                        telefono=telefono,
                        uuid=invitado_uuid,
                        confirmacion="Pendiente",
                        acompanantes=0,
                        mensaje_enviado="No",
                        notas="",
                    )
                    session.add(nuevo)
                df.at[index, "uuid"] = invitado_uuid
            session.commit()
        except Exception as error:
            session.rollback()
            messagebox.showerror("Error de base de datos", str(error))
            session.close()
            return
        finally:
            session.close()

        self.file_path = path
        self.contacts_df = df
        self.file_label.config(text=Path(path).name)
        self.summary_var.set(f"{len(df)} registros")
        self.contacts_count_var.set(f"{len(df)} contactos")
        self.valid_count_var.set(f"{int(df['Valido'].sum())} válidos")
        self.invalid_count_var.set(f"{int((~df['Valido']).sum())} observaciones")
        self.refresh_preview()
        self.set_status("Excel cargado y sincronizado con la base de datos.")
        self.log(f"Excel cargado: {path}")
        self.log("Invitados listos con UUID para links únicos.")

    def refresh_preview(self):
        for item in self.preview_table.get_children():
            self.preview_table.delete(item)

        if self.contacts_df.empty:
            return

        for _, row in self.contacts_df.head(20).iterrows():
            self.preview_table.insert("", tk.END, values=(row["Nombre"], row["Telefono"]))

    def normalize_phone(self, raw_phone):
        phone = re.sub(r"\D", "", str(raw_phone))
        if not phone:
            raise ValueError("teléfono vacío")

        country_code = re.sub(r"\D", "", self.country_code_var.get()) or "52"
        if not phone.startswith(country_code) and len(phone) <= 10:
            phone = f"{country_code}{phone}"

        # WhatsApp (a diferencia de la telefonía normal) requiere un "1"
        # extra después del código de país 52 para celulares de México.
        if country_code == "52" and phone.startswith("52") and not phone.startswith("521"):
            phone = f"521{phone[2:]}"

        return phone

    def build_confirmation_link(self, invitado_uuid):
        base_url = self.link_var.get().strip().rstrip("/")
        return f"{base_url}?id={invitado_uuid}"

    def open_dashboard(self):
        dashboard_url = self.dashboard_url_var.get().strip()
        if not dashboard_url:
            messagebox.showerror("Falta información", "Configura DASHBOARD_URL en el archivo .env.")
            return

        if not re.match(r"^https?://", dashboard_url, re.IGNORECASE):
            messagebox.showerror("URL inválida", "La URL del dashboard debe iniciar con http:// o https://")
            return

        opened = webbrowser.open(dashboard_url)
        if opened:
            self.set_status("Dashboard abierto en el navegador predeterminado.")
            self.log(f"Dashboard abierto: {dashboard_url}")
        else:
            messagebox.showerror("No se pudo abrir", "No se pudo abrir el dashboard en el navegador.")

    def clear_dashboard_data(self):
        if self.is_sending:
            messagebox.showwarning("Proceso en curso", "No puedes borrar datos mientras se están enviando invitaciones.")
            return

        confirmed = messagebox.askyesno(
            "Advertencia importante",
            "Esto borrará todos los invitados, links únicos y confirmaciones guardadas en la base de datos actual.\n\n"
            "El dashboard quedará vacío al volver a abrirlo.\n\n"
            "¿Deseas continuar?",
            icon="warning",
        )
        if not confirmed:
            return

        second_confirm = messagebox.askyesno(
            "Confirmación final",
            "Esta acción no se puede deshacer desde la app.\n\n"
            "¿Seguro que quieres borrar todos los datos actuales?",
            icon="warning",
        )
        if not second_confirm:
            return

        session = Session()
        try:
            deleted_rows = session.query(Invitado).delete()
            session.commit()
        except Exception as error:
            session.rollback()
            messagebox.showerror("Error al borrar", str(error))
            return
        finally:
            session.close()

        self.file_path = ""
        self.contacts_df = pd.DataFrame()
        self.summary_var.set("Sin archivo cargado")
        self.contacts_count_var.set("0 contactos")
        self.valid_count_var.set("0 válidos")
        self.invalid_count_var.set("0 observaciones")
        self.file_label.config(text="Ningún archivo seleccionado")
        self.progress.configure(value=0)
        self.refresh_preview()
        self.set_status("Datos borrados. El dashboard quedó listo para una nueva carga.")
        self.log(f"Se borraron {deleted_rows} registros de la base de datos.")
        messagebox.showinfo("Datos eliminados", "Se borraron los datos actuales. El dashboard ya puede iniciar vacío.")

    def is_template_mode(self):
        return bool(self.content_sid_var.get().strip())

    def build_twilio_payload(self, phone_e164, name, link):
        payload = {
            "From": self.from_number_var.get().strip(),
            "To": f"whatsapp:{phone_e164}",
        }

        content_sid = self.content_sid_var.get().strip()
        if content_sid:
            payload["ContentSid"] = content_sid
            payload["ContentVariables"] = json.dumps({"1": name, "2": link})
        else:
            payload["Body"] = f"Hola {name}, por favor confirma tu asistencia aquí: {link}"

        return payload

    def validate_api_fields(self):
        if not self.account_sid_var.get().strip():
            messagebox.showerror("Falta información", "Configura TWILIO_ACCOUNT_SID en el archivo .env.")
            return False
        if not self.auth_token_var.get().strip():
            messagebox.showerror("Falta información", "Configura TWILIO_AUTH_TOKEN en el archivo .env.")
            return False
        if not self.from_number_var.get().strip():
            messagebox.showerror("Falta información", "Configura TWILIO_WHATSAPP_FROM en el archivo .env.")
            return False
        if not self.link_var.get().strip():
            messagebox.showerror("Falta información", "Configura CONFIRMATION_BASE_URL en el archivo .env.")
            return False
        return True

    def start_sending(self):
        if self.is_sending:
            return

        if not self.validate_api_fields():
            return

        if not self.file_path or self.contacts_df.empty:
            messagebox.showerror("Falta información", "Primero selecciona un Excel válido.")
            return

        mode_message = (
            "Se enviará la plantilla aprobada de Twilio con link único por invitado."
            if self.is_template_mode()
            else "No hay TWILIO_CONTENT_SID configurado: se enviará un mensaje de texto libre "
            "(solo funciona en sandbox o dentro de una sesión de 24h)."
        )
        proceed = messagebox.askyesno(
            "Confirmar envío",
            f"{mode_message}\n\nContactos: {len(self.contacts_df)}\n¿Deseas continuar?",
        )
        if not proceed:
            return

        self.is_sending = True
        self.sent_contacts = 0
        self.failed_contacts = 0
        self.progress.configure(maximum=len(self.contacts_df), value=0)
        self.send_button.config(state="disabled", text="Enviando...")
        self.set_status("Preparando envío...")
        self.log("Inicio del envío")

        worker = threading.Thread(target=self._send_messages_worker, daemon=True)
        worker.start()

    def _send_messages_worker(self):
        delay_seconds = max(1, int(self.delay_var.get()))
        account_sid = self.account_sid_var.get().strip()
        auth_token = self.auth_token_var.get().strip()
        url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/Messages.json"

        for index, row in self.contacts_df.iterrows():
            nombre = str(row["Nombre"]).strip() or "Invitado"
            telefono_original = str(row["Telefono"]).strip()

            try:
                telefono = self.normalize_phone(telefono_original)
                invitado_uuid = str(row.get("uuid", "")).strip() or str(uuid.uuid4())
                if not str(row.get("uuid", "")).strip():
                    self.contacts_df.at[index, "uuid"] = invitado_uuid
                link = self.build_confirmation_link(invitado_uuid)
                payload = self.build_twilio_payload(f"+{telefono}", nombre, link)

                self.root.after(0, self.set_status, f"Enviando a {nombre}...")
                self.root.after(0, self.log, f"[{index + 1}/{len(self.contacts_df)}] Enviando a {nombre} ({telefono})")
                if self.is_template_mode():
                    self.root.after(0, self.log, f"LINK | {nombre} | {link}")

                response = requests.post(url, data=payload, auth=(account_sid, auth_token), timeout=30)
                if response.ok:
                    self.sent_contacts += 1
                    self.mark_message_sent(nombre, telefono_original, invitado_uuid)
                    self.root.after(0, self.log, f"OK | {nombre} | link único listo")
                else:
                    self.failed_contacts += 1
                    try:
                        error_detail = response.json().get("message", response.text)
                    except ValueError:
                        error_detail = response.text
                    self.root.after(0, self.log, f"ERROR | {nombre} | {response.status_code} | {error_detail}")
            except Exception as error:
                self.failed_contacts += 1
                self.root.after(0, self.log, f"ERROR | {nombre} ({telefono_original}) | {error}")
            finally:
                self.root.after(0, self.progress.configure, {"value": index + 1})
                time.sleep(delay_seconds)

        self.root.after(0, self.finish_sending)

    def mark_message_sent(self, nombre, telefono, invitado_uuid):
        session = Session()
        try:
            invitado = session.query(Invitado).filter_by(uuid=invitado_uuid).first()
            if invitado:
                invitado.mensaje_enviado = "Si"
            else:
                invitado = Invitado(
                    nombre=nombre,
                    telefono=telefono,
                    uuid=invitado_uuid,
                    confirmacion="Pendiente",
                    acompanantes=0,
                    mensaje_enviado="Si",
                    notas="",
                )
                session.add(invitado)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def finish_sending(self):
        self.is_sending = False
        self.send_button.config(state="normal", text="Enviar invitaciones")
        summary = f"Proceso terminado. Enviados: {self.sent_contacts}. Con error: {self.failed_contacts}."
        self.set_status(summary)
        self.log(summary)
        messagebox.showinfo("Proceso finalizado", summary)


if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    root = tk.Tk()
    app = App(root)
    root.mainloop()
