import requests
import pandas as pd
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import uuid

# --- SQLAlchemy ---
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///invitados.db')
Base = declarative_base()

class Invitado(Base):
    __tablename__ = 'invitados'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    telefono = Column(String)
    uuid = Column(String, unique=True)
    confirmacion = Column(String, default="Pendiente")
    acompanantes = Column(Integer, default=0)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Automatizador de Confirmaciones")
        self.root.geometry("600x600")
        self.root.configure(bg="#f0f0f0")

        self.file_path = ""

        # --- META WHATSAPP CONFIG ---
        self.phone_number_id = "988913294306193"
        self.access_token = "EAAiOEwTLAf8BQ3z9kHvLlb34gS7BpZCZAAhpG342Yawf5cQU0l7tqNcVUZAJBmGsUO3ZBb1DINAZCppywJqZALVCjfJgUmXawZARGWwvvUuWCxOqwdAfUFl86ZBBlE4waJOZCQKAnCjrZC5MykopaGj4PcpqtSjJg2VP8WrqkOWlD0ysK1titvlmZCljufQD7zyLy81AkohcFJYIpmDHZCMMwAVHxmBiGfkA8IATYDScfiTAOO33Bkjo7ZChGx3fMKq0VqXqV682R4Le6NgjNJMyQVKgCAo3e"

        # --- DB ---
        self.engine = create_engine('sqlite:///invitados.db')
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

        self.create_widgets()

    def create_widgets(self):
        file_frame = tk.Frame(self.root, padx=10, pady=10, bg="#e0e0e0")
        file_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(file_frame, text="Selecciona un archivo de Excel:", font=("Arial", 10, "bold"), bg="#e0e0e0").pack(side="left")

        self.file_label = tk.Label(file_frame, text="Ningún archivo seleccionado", bg="#ffffff", relief="sunken", padx=5)
        self.file_label.pack(side="left", fill="x", expand=True, padx=10)

        tk.Button(file_frame, text="Examinar", command=self.select_file, bg="#3E6B40", fg="white").pack(side="right")

        message_frame = tk.Frame(self.root, padx=10, pady=10, bg="#f0f0f0")
        message_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(message_frame, text="Mensaje (usa {nombre}):", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(anchor="w")

        self.message_text = scrolledtext.ScrolledText(message_frame, wrap=tk.WORD, height=15)
        self.message_text.pack(fill="both", expand=True, pady=5)

        self.send_button = tk.Button(self.root, text="Iniciar Envío", bg="#526F86", fg="white", command=self.start_sending)
        self.send_button.pack(pady=20, ipadx=20, ipady=10)

    def select_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if self.file_path:
            self.file_label.config(text=self.file_path.split("/")[-1])
            self.load_excel_to_db()

    def load_excel_to_db(self):
        session = self.Session()
        try:
            df = pd.read_excel(self.file_path, dtype={'Telefono': str})

            for _, row in df.iterrows():
                nuevo = Invitado(
                    nombre=str(row['Nombre']),
                    telefono=str(row['Telefono']),
                    uuid=str(uuid.uuid4())
                )
                session.add(nuevo)

            session.commit()
            messagebox.showinfo("OK", "Invitados cargados correctamente")

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            session.close()

    def start_sending(self):
        mensaje_base = self.message_text.get("1.0", tk.END).strip()

        if not mensaje_base:
            messagebox.showerror("Error", "Escribe un mensaje primero.")
            return

        self.send_button.config(state="disabled", text="Enviando...")
        self.root.update_idletasks()

        session = self.Session()
        invitados = session.query(Invitado).all()
        total_sent = 0

        for invitado in invitados:
            try:
                enlace = f"http://tu_dominio/confirmar?id={invitado.uuid}"

                mensaje_final = mensaje_base.replace("{nombre}", invitado.nombre)
                mensaje_final += f"\n\nConfirma aquí: {enlace}"

                numero = invitado.telefono

                # Agregar código país si no tiene +
                if not numero.startswith('+'):
                    numero = '+52' + numero

                numero_limpio = numero.replace("+", "").replace(" ", "")

                url = f"https://graph.facebook.com/v22.0/{self.phone_number_id}/messages"

                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }

                data = {
                    "messaging_product": "whatsapp",
                    "to": numero_limpio,
                    "type": "text",
                    "text": {
                        "body": mensaje_final
                    }
                }

                response = requests.post(url, headers=headers, json=data)

                if response.status_code == 200:
                    total_sent += 1
                else:
                    print(f"Error con {invitado.nombre}: {response.text}")

                time.sleep(1)

            except Exception as e:
                print(f"Error con {invitado.nombre}: {e}")

        session.close()
        messagebox.showinfo("Finalizado", f"{total_sent} mensajes enviados correctamente 🚀")
        self.send_button.config(state="normal", text="Iniciar Envío")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()