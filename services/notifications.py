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
    Función "stub" para notificar al bot de Telegram (y, por ende, al cliente).
    """
    print("--- simulated_telegram_notification ---")
    print(f"[TELEGRAM] Enviando a Cliente (Telegram ID): {cliente_telegram_id}")
    print(f"[MESSAGE] {message}")
    print("-----------------------------------------")
    # Nota: En una app real, aquí harías una solicitud HTTP
    # al endpoint de tu bot de Telegram.
    pass