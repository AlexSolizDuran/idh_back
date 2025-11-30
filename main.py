# main.py
from fastapi import FastAPI
from db import database, models
from api.endpoints import auth, repartidores, pedidos, bot

# Inicializar Base de Datos
try:
    models.Base.metadata.create_all(bind=database.engine)
except Exception as e:
    print(f"Error BD: {e}")

app = FastAPI(title="Delivery Backend + Bot")

# --- ROUTERS ---
# App Móvil
app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
app.include_router(repartidores.router, prefix="/api", tags=["Repartidores"])
app.include_router(pedidos.router, prefix="/api", tags=["Pedidos"])

# Bot Telegram (Sin prefijo /api para que sea más fácil configurar el webhook)
app.include_router(bot.router, tags=["Bot Telegram"])

@app.get("/")
def root():
    return {"msg": "Backend Modular Activo 🚀"}