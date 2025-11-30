# api/endpoints/bot.py
import json
from fastapi import APIRouter, Request, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from db import database, crud, schemas
from services import telegram  # Importamos nuestro nuevo servicio
from api.endpoints import pedidos as pedidos_logic # Para la lógica de asignación

router = APIRouter()

# --- RUTAS ---

@router.get("/web", response_class=HTMLResponse)
async def serve_web_app():
    """Sirve el menú HTML."""
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: No se encontró templates/index.html</h1>"

@router.post("/webhook")
async def telegram_webhook(
    request: Request, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(database.get_db)
):
    """Procesa las actualizaciones de Telegram."""
    try:
        update = await request.json()
    except:
        return "Error JSON"

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        
        # 1. Comando /start
        if "text" in msg and msg["text"] == "/start":
            # RECUERDA: Actualiza esta URL con la de Ngrok cuando corras el servidor
            web_app_url = "https://TU-URL-DE-NGROK.ngrok-free.app/web" 
            
            keyboard = {
                "inline_keyboard": [[
                    {"text": "🍔 Abrir Menú", "web_app": {"url": web_app_url}}
                ]]
            }
            telegram.enviar_mensaje(chat_id, "¡Hola! Haz clic abajo para pedir 👇", keyboard)

        # 2. Datos de la Web App
        elif "web_app_data" in msg:
            try:
                data_str = msg["web_app_data"]["data"]
                web_data = json.loads(data_str)
                
                # Crear Pedido
                nuevo_pedido = schemas.PedidoCreate(
                    descripcion_pedido=web_data.get("mensaje", "Pedido Web"),
                    direccion_entrega="Ubicación Telegram", 
                    monto_total=float(web_data.get("total", 0)),
                    cliente_telegram_id=chat_id,
                    instrucciones_entrega="Pedido desde Bot"
                )
                
                pedido_db = crud.create_pedido(db, nuevo_pedido)

                # Confirmar y Buscar Repartidor
                telegram.enviar_mensaje(
                    chat_id, 
                    f"✅ *Pedido #{pedido_db.pedido_id} Recibido*\nTotal: {nuevo_pedido.monto_total} Bs\n\n🔎 Buscando repartidor..."
                )
                
                # Iniciar lógica de 5 segundos
                crud.actualizar_estado_pedido(db, pedido_db.pedido_id, 'BUSCANDO_REPARTIDOR')
                background_tasks.add_task(pedidos_logic.ciclo_asignacion_pedido, pedido_db.pedido_id, db)

            except Exception as e:
                print(f"Error procesando pedido: {e}")
                telegram.enviar_mensaje(chat_id, "❌ Error al procesar el pedido.")

    return {"status": "ok"}