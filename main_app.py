import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import pandas as pd
import pywhatkit


APP_NAME = "AutoConfirm"
APP_SUBTITLE = "AutoConfirm automatiza confirmaciones por WhatsApp con una interfaz clara, rápida y profesional."
APP_BG = "#F4F6FB"
CARD_BG = "#FFFFFF"
ACCENT = "#5166F6"
ACCENT_DARK = "#3B4BD1"
SUCCESS = "#198754"
WARNING = "#F59E0B"
DANGER = "#DC2626"
TEXT = "#1F2937"
MUTED = "#6B7280"
BORDER = "#D9E2F1"
SOFT_BLUE = "#EEF2FF"
SOFT_GREEN = "#ECFDF3"
SOFT_YELLOW = "#FEF3C7"
DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_TEMPLATE = DATA_DIR / "invitados.xlsx"


class App:
    REQUIRED_COLUMNS = {"Nombre", "Telefono"}

    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("940x760")
        self.root.minsize(900, 720)
        self.root.configure(bg=APP_BG)

        self.file_path = ""
        self.contacts_df = pd.DataFrame()
        self.is_sending = False
        self.total_contacts = 0
        self.sent_contacts = 0
        self.failed_contacts = 0

        self.status_var = tk.StringVar(value="Selecciona un Excel para comenzar.")
        self.summary_var = tk.StringVar(value="Sin archivo cargado")
        self.delay_var = tk.IntVar(value=12)
        self.country_code_var = tk.StringVar(value="52")
        self.contacts_count_var = tk.StringVar(value="0 contactos")
        self.valid_count_var = tk.StringVar(value="0 válidos")
        self.invalid_count_var = tk.StringVar(value="0 observaciones")
        self.char_count_var = tk.StringVar(value="0 caracteres")

        self._configure_styles()
        self.create_widgets()
        self.update_character_count()

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Main.Horizontal.TProgressbar",
            troughcolor="#E9EEF8",
            background=ACCENT,
            bordercolor="#E9EEF8",
            lightcolor=ACCENT,
            darkcolor=ACCENT,
        )
        style.configure(
            "Treeview",
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground=TEXT,
            rowheight=28,
            bordercolor=BORDER,
        )
        style.configure("Treeview.Heading", background=SOFT_BLUE, foreground=TEXT, relief="flat")
        style.map("Treeview", background=[("selected", "#DCE5FF")], foreground=[("selected", TEXT)])

    def create_widgets(self):
        container = tk.Frame(self.root, bg=APP_BG)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        self._build_header(container)
        self._build_upload_card(container)
        self._build_middle_section(container)
        self._build_bottom_section(container)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=APP_BG)
        header.pack(fill="x", pady=(0, 12))

        title_row = tk.Frame(header, bg=APP_BG)
        title_row.pack(fill="x")

        tk.Label(title_row, text=APP_NAME, font=("Segoe UI", 24, "bold"), bg=APP_BG, fg=TEXT).pack(side="left", anchor="w")


        tk.Label(
            header,
            text=APP_SUBTITLE,
            font=("Segoe UI", 10),
            bg=APP_BG,
            fg=MUTED,
        ).pack(anchor="w", pady=(6, 10))

        steps = tk.Frame(header, bg=APP_BG)
        steps.pack(fill="x")

        for step_text in [
            "1. Carga tu Excel",
            "2. Escribe tu mensaje",
            "3. Revisa la vista previa",
            "4. Inicia el envío",
        ]:
            tk.Label(
                steps,
                text=step_text,
                font=("Segoe UI", 9, "bold"),
                bg="#FFFFFF",
                fg=TEXT,
                relief="solid",
                bd=1,
                padx=12,
                pady=7,
            ).pack(side="left", padx=(0, 8))

    def _build_upload_card(self, parent):
        top_card = tk.Frame(parent, bg=CARD_BG, bd=1, relief="solid", highlightthickness=0)
        top_card.pack(fill="x", pady=(0, 12))

        title_row = tk.Frame(top_card, bg=CARD_BG)
        title_row.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(title_row, text="Lista de invitados", font=("Segoe UI", 12, "bold"), bg=CARD_BG, fg=TEXT).pack(side="left")
        tk.Label(title_row, textvariable=self.summary_var, font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=SUCCESS).pack(side="right")

        file_row = tk.Frame(top_card, bg=CARD_BG)
        file_row.pack(fill="x", padx=16, pady=(0, 10))

        self.file_label = tk.Label(
            file_row,
            text="Ningún archivo seleccionado",
            bg="#F8FAFC",
            fg=MUTED,
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=12,
            anchor="w",
        )
        self.file_label.pack(side="left", fill="x", expand=True)

        tk.Button(
            file_row,
            text="Seleccionar Excel",
            command=self.select_file,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_DARK,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=11,
        ).pack(side="right", padx=(10, 0))

        settings_row = tk.Frame(top_card, bg=CARD_BG)
        settings_row.pack(fill="x", padx=16, pady=(0, 12))

        tk.Label(settings_row, text="Prefijo país", font=("Segoe UI", 10), bg=CARD_BG, fg=TEXT).pack(side="left")
        tk.Entry(settings_row, textvariable=self.country_code_var, width=8, justify="center", relief="solid", bd=1).pack(side="left", padx=(8, 20))

        tk.Label(settings_row, text="Pausa entre mensajes (seg)", font=("Segoe UI", 10), bg=CARD_BG, fg=TEXT).pack(side="left")
        tk.Spinbox(settings_row, from_=8, to=60, textvariable=self.delay_var, width=8, justify="center").pack(side="left", padx=(8, 20))

        tk.Button(
            settings_row,
            text="Usar Excel de ejemplo",
            command=self.load_default_template,
            bg=SOFT_BLUE,
            fg=ACCENT_DARK,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=7,
        ).pack(side="left")

        tk.Button(
            settings_row,
            text="Formato esperado",
            command=self.show_format_help,
            bg="#F9FAFB",
            fg=TEXT,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9),
            padx=10,
            pady=7,
        ).pack(side="left", padx=(8, 0))

        stats_row = tk.Frame(top_card, bg=CARD_BG)
        stats_row.pack(fill="x", padx=16, pady=(0, 16))

        self._stat_card(stats_row, "Contactos cargados", self.contacts_count_var, SOFT_BLUE, ACCENT_DARK).pack(side="left", fill="x", expand=True)
        self._stat_card(stats_row, "Válidos", self.valid_count_var, SOFT_GREEN, SUCCESS).pack(side="left", fill="x", expand=True, padx=8)
        self._stat_card(stats_row, "Observaciones", self.invalid_count_var, SOFT_YELLOW, WARNING).pack(side="left", fill="x", expand=True)

    def _build_middle_section(self, parent):
        middle_frame = tk.Frame(parent, bg=APP_BG)
        middle_frame.pack(fill="both", expand=True)

        message_card = tk.Frame(middle_frame, bg=CARD_BG, bd=1, relief="solid")
        message_card.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(message_card, text="Mensaje", font=("Segoe UI", 12, "bold"), bg=CARD_BG, fg=TEXT).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Label(
            message_card,
            text="Usa {nombre} para personalizar cada mensaje y lograr una mejor respuesta.",
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg=MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self.message_text = scrolledtext.ScrolledText(
            message_card,
            wrap=tk.WORD,
            height=16,
            font=("Segoe UI", 10),
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=10,
        )
        self.message_text.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self.message_text.insert(
            "1.0",
            "Hola {nombre}, espero que estés muy bien. Te escribo para confirmar tu asistencia. ¿Me ayudas respondiendo, por favor?",
        )
        self.message_text.bind("<KeyRelease>", lambda event: self.update_character_count())

        meta_row = tk.Frame(message_card, bg=CARD_BG)
        meta_row.pack(fill="x", padx=16, pady=(0, 6))
        tk.Label(meta_row, textvariable=self.char_count_var, font=("Segoe UI", 9), bg=CARD_BG, fg=MUTED).pack(side="left")
        tk.Label(meta_row, text="Tip: mensajes cortos y claros suelen convertir mejor.", font=("Segoe UI", 9), bg=CARD_BG, fg=MUTED).pack(side="right")

        helper_row = tk.Frame(message_card, bg=CARD_BG)
        helper_row.pack(fill="x", padx=16, pady=(0, 16))

        tk.Button(
            helper_row,
            text="Insertar ejemplo",
            command=self.insert_example_message,
            bg=SOFT_BLUE,
            fg=ACCENT_DARK,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=8,
        ).pack(side="left")

        tk.Button(
            helper_row,
            text="Mensaje para evento",
            command=self.insert_event_message,
            bg="#F9FAFB",
            fg=TEXT,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9),
            padx=10,
            pady=8,
        ).pack(side="left", padx=(8, 0))

        preview_card = tk.Frame(middle_frame, bg=CARD_BG, bd=1, relief="solid")
        preview_card.pack(side="right", fill="both", expand=True, padx=(6, 0))

        top_row = tk.Frame(preview_card, bg=CARD_BG)
        top_row.pack(fill="x", padx=16, pady=(16, 10))
        tk.Label(top_row, text="Vista previa del Excel", font=("Segoe UI", 12, "bold"), bg=CARD_BG, fg=TEXT).pack(side="left")
        tk.Label(top_row, text="Se muestran los primeros 10 registros", font=("Segoe UI", 9), bg=CARD_BG, fg=MUTED).pack(side="right")

        columns = ("Nombre", "Telefono")
        self.preview_table = ttk.Treeview(preview_card, columns=columns, show="headings", height=12)
        for col in columns:
            self.preview_table.heading(col, text=col)
            self.preview_table.column(col, anchor="w", width=180)
        self.preview_table.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _build_bottom_section(self, parent):
        bottom_card = tk.Frame(parent, bg=CARD_BG, bd=1, relief="solid")
        bottom_card.pack(fill="x", pady=(12, 0))

        action_row = tk.Frame(bottom_card, bg=CARD_BG)
        action_row.pack(fill="x", padx=16, pady=(16, 10))

        self.send_button = tk.Button(
            action_row,
            text="Iniciar envío",
            font=("Segoe UI", 11, "bold"),
            bg=SUCCESS,
            fg="white",
            activebackground="#157347",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.start_sending,
            padx=24,
            pady=12,
        )
        self.send_button.pack(side="left")

        tk.Button(
            action_row,
            text="Limpiar registro",
            font=("Segoe UI", 9),
            bg="#F9FAFB",
            fg=TEXT,
            relief="flat",
            cursor="hand2",
            command=self.clear_log,
            padx=12,
            pady=9,
        ).pack(side="left", padx=(10, 0))

        tk.Label(action_row, textvariable=self.status_var, font=("Segoe UI", 10), bg=CARD_BG, fg=MUTED).pack(side="left", padx=(16, 0))

        self.progress = ttk.Progressbar(bottom_card, style="Main.Horizontal.TProgressbar", mode="determinate")
        self.progress.pack(fill="x", padx=16, pady=(0, 10))

        tk.Label(bottom_card, text="Registro de actividad", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT).pack(anchor="w", padx=16)

        self.log_text = scrolledtext.ScrolledText(
            bottom_card,
            wrap=tk.WORD,
            height=8,
            font=("Consolas", 9),
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=10,
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True, padx=16, pady=(8, 10))

        footer = tk.Frame(bottom_card, bg=CARD_BG)
        footer.pack(fill="x", padx=16, pady=(0, 16))
        tk.Label(
            footer,
            text="Recomendación: mantén WhatsApp Web abierto e inicia sesión antes de comenzar.",
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg=MUTED,
        ).pack(side="left")
        tk.Label(
            footer,
            text="AutoConfirm listo para venta y demostraciones.",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG,
            fg=ACCENT_DARK,
        ).pack(side="right")

    def _stat_card(self, parent, title, value_var, bg_color, fg_color):
        card = tk.Frame(parent, bg=bg_color, bd=0)
        tk.Label(card, text=title, font=("Segoe UI", 9), bg=bg_color, fg=fg_color).pack(anchor="w", padx=12, pady=(10, 0))
        tk.Label(card, textvariable=value_var, font=("Segoe UI", 15, "bold"), bg=bg_color, fg=fg_color).pack(anchor="w", padx=12, pady=(2, 10))
        return card

    def update_character_count(self):
        message = self.message_text.get("1.0", tk.END).strip()
        self.char_count_var.set(f"{len(message)} caracteres")

    def show_format_help(self):
        messagebox.showinfo(
            "Formato del Excel",
            "Tu archivo debe incluir exactamente estas columnas:\n\n"
            "- Nombre\n"
            "- Telefono\n\n"
            "Ejemplo:\n"
            "Nombre | Telefono\n"
            "Javier | 8112345678\n"
            "Ana    | 8187654321",
        )

    def load_default_template(self):
        if not DEFAULT_TEMPLATE.exists():
            messagebox.showwarning("Archivo no encontrado", "No se encontró el Excel de ejemplo en la carpeta data.")
            return

        self.file_path = str(DEFAULT_TEMPLATE)
        self.file_label.config(text=DEFAULT_TEMPLATE.name, fg=TEXT)
        self.load_excel_preview()

    def insert_example_message(self):
        example = (
            "Hola {nombre}, espero que estés muy bien. ",
            "Te escribo para confirmar tu asistencia. "
            "Si gustas, respóndeme por este medio. ¡Gracias!"
        )
        self.message_text.delete("1.0", tk.END)
        self.message_text.insert("1.0", example)
        self.update_character_count()

    def insert_event_message(self):
        example = (
            "Hola {nombre}, te compartimos este mensaje para confirmar tu asistencia al evento. "
            "Nos ayudaría mucho si nos confirmas por favor. ¡Gracias por tu tiempo!"
        )
        self.message_text.delete("1.0", tk.END)
        self.message_text.insert("1.0", example)
        self.update_character_count()

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")
        self.log("Registro limpiado.")

    def set_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Archivos de Excel", "*.xlsx")])
        if not file_path:
            return

        self.file_path = file_path
        self.file_label.config(text=Path(file_path).name, fg=TEXT)
        self.load_excel_preview()

    def load_excel_preview(self):
        try:
            df = pd.read_excel(self.file_path, dtype={"Telefono": str})
            self.validate_dataframe(df)
            raw_count = len(df)
            df = self.normalize_dataframe(df)
            self.contacts_df = df
            self.total_contacts = len(df)
            observations = max(raw_count - self.total_contacts, 0)

            self.summary_var.set(f"{self.total_contacts} contactos listos")
            self.contacts_count_var.set(str(raw_count))
            self.valid_count_var.set(str(self.total_contacts))
            self.invalid_count_var.set(str(observations))
            self.set_status("Archivo cargado correctamente.")
            self.populate_preview(df)
            self.log(f"Excel cargado: {Path(self.file_path).name} ({self.total_contacts} registros válidos)")
        except Exception as error:
            self.contacts_df = pd.DataFrame()
            self.summary_var.set("Error al cargar archivo")
            self.contacts_count_var.set("0")
            self.valid_count_var.set("0")
            self.invalid_count_var.set("0")
            self.file_label.config(text="Archivo inválido", fg=DANGER)
            self.clear_preview()
            messagebox.showerror("Error en el Excel", str(error))
            self.set_status("Corrige el archivo e inténtalo de nuevo.")

    def validate_dataframe(self, df):
        missing = self.REQUIRED_COLUMNS.difference(df.columns)
        if missing:
            raise ValueError(
                "El Excel debe incluir las columnas exactas: Nombre y Telefono. "
                f"Faltan: {', '.join(sorted(missing))}."
            )
        if df.empty:
            raise ValueError("El Excel está vacío.")

    def normalize_dataframe(self, df):
        clean_df = df.copy()
        clean_df["Nombre"] = clean_df["Nombre"].fillna("").astype(str).str.strip()
        clean_df["Telefono"] = clean_df["Telefono"].fillna("").astype(str).str.strip()
        clean_df = clean_df[(clean_df["Nombre"] != "") & (clean_df["Telefono"] != "")]

        if clean_df.empty:
            raise ValueError("No hay filas válidas después de limpiar nombres y teléfonos vacíos.")

        clean_df = clean_df.drop_duplicates(subset=["Telefono"], keep="first").reset_index(drop=True)
        return clean_df

    def populate_preview(self, df):
        self.clear_preview()
        for _, row in df.head(10).iterrows():
            self.preview_table.insert("", tk.END, values=(row["Nombre"], row["Telefono"]))

    def clear_preview(self):
        for item in self.preview_table.get_children():
            self.preview_table.delete(item)

    def normalize_phone(self, raw_phone):
        phone = re.sub(r"\D", "", str(raw_phone))
        if not phone:
            raise ValueError("teléfono vacío")

        country_code = re.sub(r"\D", "", self.country_code_var.get()) or "52"
        if not phone.startswith(country_code) and len(phone) <= 10:
            phone = f"{country_code}{phone}"

        return f"+{phone}"

    def start_sending(self):
        if self.is_sending:
            return

        if not self.file_path or self.contacts_df.empty:
            messagebox.showerror("Falta información", "Primero selecciona un Excel válido.")
            return

        mensaje_base = self.message_text.get("1.0", tk.END).strip()
        if not mensaje_base:
            messagebox.showerror("Falta mensaje", "Escribe el mensaje que quieres enviar.")
            return

        if "{nombre}" not in mensaje_base:
            proceed = messagebox.askyesno(
                "Continuar sin personalización",
                "Tu mensaje no incluye {nombre}. ¿Quieres enviarlo igual?",
            )
            if not proceed:
                return

        proceed = messagebox.askyesno(
            "Confirmar envío",
            f"Se iniciará el envío para {len(self.contacts_df)} contactos.\n\n¿Deseas continuar?",
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

        worker = threading.Thread(target=self._send_messages_worker, args=(mensaje_base,), daemon=True)
        worker.start()

    def _send_messages_worker(self, mensaje_base):
        delay_seconds = max(8, int(self.delay_var.get()))

        for index, row in self.contacts_df.iterrows():
            nombre = str(row["Nombre"]).strip()
            telefono_original = str(row["Telefono"]).strip()

            try:
                telefono = self.normalize_phone(telefono_original)
                mensaje_final = mensaje_base.replace("{nombre}", nombre)

                self.root.after(0, self.set_status, f"Enviando a {nombre}...")
                self.root.after(0, self.log, f"[{index + 1}/{len(self.contacts_df)}] Abriendo chat para {nombre} ({telefono})")

                pywhatkit.sendwhatmsg_instantly(
                    telefono,
                    mensaje_final,
                    wait_time=15,
                    tab_close=True,
                    close_time=3,
                )

                self.sent_contacts += 1
                self.root.after(0, self.log, f"âœ“ Mensaje enviado a {nombre}")
            except Exception as error:
                self.failed_contacts += 1
                self.root.after(0, self.log, f"âœ— Error con {nombre} ({telefono_original}): {error}")
            finally:
                self.root.after(0, self.progress.configure, {"value": index + 1})
                time.sleep(delay_seconds)

        self.root.after(0, self.finish_sending)

    def finish_sending(self):
        self.is_sending = False
        self.send_button.config(state="normal", text="Iniciar envío")
        summary = (
            f"Proceso terminado. Enviados: {self.sent_contacts}. "
            f"Con error: {self.failed_contacts}."
        )
        self.set_status(summary)
        self.log(summary)
        messagebox.showinfo("Proceso finalizado", summary)


if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    root = tk.Tk()
    app = App(root)
    root.mainloop()


