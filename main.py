from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from db import database, models
from api.endpoints import auth, repartidores, pedidos

# Crea las tablas en la base de datos (si no existen)
# Esta línea es crucial: le dice a SQLAlchemy que cree las tablas
# basadas en los 'models.py' si no las encuentra.
try:
    models.Base.metadata.create_all(bind=database.engine)
    print("Tablas de la base de datos verificadas/creadas con éxito.")
except Exception as e:
    print(f"ERROR: No se pudo conectar o crear las tablas de la base de datos: {e}")
    # En un escenario real, podrías querer que la app falle aquí
    # si la BD no es accesible.

app = FastAPI(
    title="API de Delivery para Restaurante",
    description="Backend para la app de repartidores (Flutter) y el bot (Telegram)",
    version="0.1.0"
)

# --- Routers ---
# Incluimos los endpoints de los módulos separados
app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
app.include_router(repartidores.router, prefix="/api", tags=["Repartidores"])
app.include_router(pedidos.router, prefix="/api", tags=["Pedidos"])

# --- Endpoint Raíz ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Bienvenido a la API de Delivery"}

# --- Endpoint de Salud (Health Check) ---
@app.get("/health")
def health_check(db: Session = Depends(database.get_db)):
    """
    Verifica la conectividad con la base de datos.
    """
    try:
        # Intenta una consulta simple
        db.execute("SELECT 1")
        return {"status": "ok", "db_connection": "success"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error de conexión con la base de datos: {e}")