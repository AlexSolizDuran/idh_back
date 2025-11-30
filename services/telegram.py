# services/telegram.py
import requests

# Configuración
TOKEN = "8419395221:AAG_aNghJPVpKcS0a69_CDVMBzhNPSriw3M"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

def enviar_mensaje(chat_id: int, texto: str, reply_markup: dict = None):
    """
    Envía un mensaje a Telegram usando requests.
    """
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": texto, 
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")