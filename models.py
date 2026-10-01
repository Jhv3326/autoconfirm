import os
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "invitados.db"

DATABASE_URL = (
    os.getenv("AUTOCONFIRM_DATABASE_URL", "").strip()
    or os.getenv("DATABASE_URL", "").strip()
)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "").strip()

Base = declarative_base()


def _fernet() -> Fernet:
    if not ENCRYPTION_KEY:
        raise RuntimeError(
            "Falta ENCRYPTION_KEY en las variables de entorno (ver .env.example)."
        )
    return Fernet(ENCRYPTION_KEY.encode())


def encrypt_value(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    if not value:
        return ""
    return _fernet().decrypt(value.encode()).decode()


class Organizacion(Base):
    __tablename__ = "organizaciones"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    twilio_account_sid = Column(String, default="")
    twilio_auth_token_enc = Column(String, default="")
    twilio_whatsapp_from = Column(String, default="")
    twilio_content_sid = Column(String, default="")

    usuarios = relationship("Usuario", back_populates="organizacion")
    eventos = relationship("Evento", back_populates="organizacion")

    @property
    def twilio_auth_token(self) -> str:
        return decrypt_value(self.twilio_auth_token_enc or "")

    @twilio_auth_token.setter
    def twilio_auth_token(self, value: str) -> None:
        self.twilio_auth_token_enc = encrypt_value(value or "")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    es_admin = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    organizacion = relationship("Organizacion", back_populates="usuarios")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Evento(Base):
    __tablename__ = "eventos"

    id = Column(Integer, primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False)
    creado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    nombre = Column(String, nullable=False)
    fecha_evento = Column(DateTime, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    organizacion = relationship("Organizacion", back_populates="eventos")
    creado_por = relationship("Usuario")
    invitados = relationship(
        "Invitado", back_populates="evento", cascade="all, delete-orphan"
    )
    colaboradores = relationship(
        "EventoColaborador", back_populates="evento", cascade="all, delete-orphan"
    )

    def puede_ver(self, usuario: "Usuario") -> bool:
        if usuario.organizacion_id != self.organizacion_id:
            return False
        if usuario.es_admin:
            return True
        if usuario.id == self.creado_por_id:
            return True
        return any(c.usuario_id == usuario.id for c in self.colaboradores)


class EventoColaborador(Base):
    __tablename__ = "evento_colaboradores"

    id = Column(Integer, primary_key=True)
    evento_id = Column(Integer, ForeignKey("eventos.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    agregado_en = Column(DateTime, default=datetime.utcnow)

    evento = relationship("Evento", back_populates="colaboradores")
    usuario = relationship("Usuario")


class Invitado(Base):
    __tablename__ = "invitados"

    id = Column(Integer, primary_key=True)
    evento_id = Column(Integer, ForeignKey("eventos.id"), nullable=False)
    nombre = Column(String)
    telefono = Column(String)
    uuid = Column(String, unique=True)
    confirmacion = Column(String, default="Pendiente")
    acompanantes = Column(Integer, default=0)
    mensaje_enviado = Column(String, default="No")
    fecha_respuesta = Column(DateTime, nullable=True)
    notas = Column(String, default="")

    evento = relationship("Evento", back_populates="invitados")


def normalize_db_url(url: str) -> str:
    normalized = url.replace("postgres://", "postgresql://", 1)
    if normalized.startswith("postgresql://"):
        normalized = normalized.replace("postgresql://", "postgresql+psycopg2://", 1)
    return normalized


if DATABASE_URL:
    engine = create_engine(normalize_db_url(DATABASE_URL))
else:
    DATA_DIR.mkdir(exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}")

Session = sessionmaker(bind=engine)


def init_db() -> None:
    Base.metadata.create_all(engine)
