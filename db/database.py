from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# Determinar si estamos usando SQLite
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Argumentos de conexión específicos para SQLite
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Crea el motor de SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args=connect_args
)

# Crea una fábrica de sesiones (SessionLocal)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para las clases de modelos declarativos
Base = declarative_base()

def get_db():
    """
    Dependencia de FastAPI para obtener una sesión de base de datos.
    Asegura que la sesión se cierre después de cada solicitud.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()