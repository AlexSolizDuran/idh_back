from services import telegram
def send_push_notification(repartidor_id: int, title: str, body: str):
    """
    Función "stub" (simulacro) para enviar notificaciones push.
    En una app real, aquí iría la lógica de Firebase (FCM) o similar.
    """
    print("---  simulated_push_notification ---")
    print(f"[PUSH] Enviando a Repartidor ID: {repartidor_id}")
    print(f"[TITLE] {title}")
    print(f"[BODY] {body}")
    print("-------------------------------------")
    # Nota: En una app real, buscarías el "FCM Token" del repartidor en la BD
    # y lo usarías para enviar la notificación.
    pass

def notify_telegram_bot(cliente_telegram_id: int, message: str):
    """
    Envía un mensaje REAL al Telegram del cliente.
    """
    print(f"[TELEGRAM -> Cliente {cliente_telegram_id}] Enviando: {message}")
    
    # Usamos tu servicio existente para enviar el mensaje
    telegram.enviar_mensaje(
        chat_id=cliente_telegram_id,
        texto=message
    )