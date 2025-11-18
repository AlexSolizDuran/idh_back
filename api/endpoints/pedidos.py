from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import time

from db import crud, schemas, database, models
from api.endpoints.repartidores import get_current_repartidor
from services import notifications

router = APIRouter()

# --- Lógica de Negocio (Asignación) ---

def iniciar_proceso_de_asignacion(db: Session, pedido: models.Pedido):
    """
    Lógica de negocio para encontrar un repartidor.
    (Fase 2 del flujo)
    """
    # 1. Buscar repartidores disponibles
    repartidores_disponibles = crud.get_repartidores_disponibles(db)
    
    if not repartidores_disponibles:
        print(f"[ASIGNACION] Pedido #{pedido.pedido_id}: No hay repartidores disponibles. Reintentando...")
        # (En producción, esto se re-intentaría con un worker/cola de tareas)
        return

    # 2. Asignar al primero (lógica simple para demo)
    repartidor_elegido = repartidores_disponibles[0]
    
    # 3. Actualizar BD y notificar
    crud.asignar_pedido_a_repartidor(db, pedido_id=pedido.pedido_id, repartidor_id=repartidor_elegido.repartidor_id)
    
    # 4. Cambiar estado del repartidor a 'en_entrega' (o similar) para que no reciba más pedidos
    crud.update_repartidor_status(db, repartidor_id=repartidor_elegido.repartidor_id, estado='en_entrega')
    
    # 5. Enviar Notificación Push (Stub)
    notifications.send_push_notification(
        repartidor_id=repartidor_elegido.repartidor_id,
        title="¡Nuevo Pedido Asignado!",
        body=f"Tienes un nuevo pedido para recoger. Dirección: {pedido.direccion_entrega}"
    )
    print(f"[ASIGNACION] Pedido #{pedido.pedido_id} asignado a Repartidor #{repartidor_elegido.repartidor_id}")

# --- Endpoints de Pedidos (para el Repartidor) ---

@router.post("/pedidos/aceptar/{pedido_id}", response_model=schemas.Pedido)
def aceptar_pedido(
    pedido_id: int,
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    El repartidor acepta el pedido que se le asignó.
    (Fase 3 del flujo)
    """
    pedido = crud.get_pedido(db, pedido_id)
    
    # Validaciones
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.repartidor_id != repartidor_actual.repartidor_id:
        raise HTTPException(status_code=403, detail="Este pedido no te pertenece")
    if pedido.estado_pedido != 'BUSCANDO_REPARTIDOR':
        raise HTTPException(status_code=400, detail=f"No se puede aceptar este pedido (Estado: {pedido.estado_pedido})")

    # Actualizar estado
    pedido_actualizado = crud.actualizar_estado_pedido(db, pedido_id, 'EN_CAMINO_AL_RESTAURANTE')
    return pedido_actualizado

@router.post("/pedidos/rechazar/{pedido_id}", response_model=schemas.Pedido)
def rechazar_pedido(
    pedido_id: int,
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    El repartidor rechaza el pedido.
    (Fase 3 del flujo)
    """
    pedido = crud.get_pedido(db, pedido_id)

    # Validaciones
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.repartidor_id != repartidor_actual.repartidor_id:
        raise HTTPException(status_code=403, detail="Este pedido no te pertenece")
    if pedido.estado_pedido != 'BUSCANDO_REPARTIDOR':
        raise HTTPException(status_code=400, detail="No se puede rechazar este pedido")

    # 1. Quitar asignación del pedido
    pedido.repartidor_id = None
    pedido.estado_pedido = 'LISTO_PARA_RECOGER' # Vuelve a la cola
    db.commit()
    
    # 2. Poner al repartidor de nuevo como 'disponible'
    crud.update_repartidor_status(db, repartidor_actual.repartidor_id, 'disponible')
    
    # 3. Buscar un nuevo repartidor (simulado)
    print(f"[RECHAZO] Repartidor #{repartidor_actual.repartidor_id} rechazó Pedido #{pedido.pedido_id}. Buscando reemplazo...")
    time.sleep(1) # Simular pequeña demora
    iniciar_proceso_de_asignacion(db, pedido)
    
    db.refresh(pedido)
    return pedido

@router.post("/pedidos/recoger/{pedido_id}", response_model=schemas.Pedido)
def recoger_pedido(
    pedido_id: int,
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    El repartidor confirma que ha recogido el pedido en el restaurante.
    (Fase 4 del flujo)
    """
    pedido = crud.get_pedido(db, pedido_id)

    # Validaciones
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.repartidor_id != repartidor_actual.repartidor_id:
        raise HTTPException(status_code=403, detail="Este pedido no te pertenece")
    if pedido.estado_pedido != 'EN_CAMINO_AL_RESTAURANTE':
        raise HTTPException(status_code=400, detail=f"No se puede recoger este pedido (Estado: {pedido.estado_pedido})")

    # Actualizar estado y notificar al cliente (vía stub)
    pedido_actualizado = crud.actualizar_estado_pedido(db, pedido_id, 'EN_CAMINO_AL_CLIENTE')
    
    notifications.notify_telegram_bot(
        cliente_telegram_id=pedido.cliente.telegram_user_id,
        message="¡Tu pedido ya está en camino! 🛵"
    )
    
    return pedido_actualizado

@router.post("/pedidos/completar/{pedido_id}", response_model=schemas.Pedido)
def completar_pedido(
    pedido_id: int,
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    El repartidor confirma que ha entregado el pedido al cliente.
    (Fase 5 del flujo)
    """
    pedido = crud.get_pedido(db, pedido_id)

    # Validaciones
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.repartidor_id != repartidor_actual.repartidor_id:
        raise HTTPException(status_code=403, detail="Este pedido no te pertenece")
    if pedido.estado_pedido != 'EN_CAMINO_AL_CLIENTE':
        raise HTTPException(status_code=400, detail=f"No se puede completar este pedido (Estado: {pedido.estado_pedido})")

    # 1. Actualizar estado del pedido
    pedido_actualizado = crud.actualizar_estado_pedido(db, pedido_id, 'ENTREGADO')
    
    # 2. Poner al repartidor de nuevo como 'disponible' (Fin del ciclo)
    crud.update_repartidor_status(db, repartidor_actual.repartidor_id, 'disponible')
    
    # 3. Notificar al cliente
    notifications.notify_telegram_bot(
        cliente_telegram_id=pedido.cliente.telegram_user_id,
        message="¡Tu pedido ha sido entregado! Gracias por elegirnos."
    )
    
    return pedido_actualizado

# --- Endpoints de Creación (para el Bot de Telegram / Admin) ---
# (Estos no estarían protegidos por JWT de repartidor, sino por una API Key,
# pero para la demo los dejamos abiertos o con protección simple)

@router.post("/pedidos", response_model=schemas.Pedido, status_code=status.HTTP_201_CREATED)
def route_create_pedido(
    pedido: schemas.PedidoCreate, 
    db: Session = Depends(database.get_db)
    # Aquí iría la validación de una API Key del Bot de Telegram
):
    """
    Endpoint para que el BOT DE TELEGRAM cree un nuevo pedido.
    """
    # El estado inicial (PENDIENTE_CONFIRMACION) lo pone la BD
    nuevo_pedido = crud.create_pedido(db, pedido)
    return nuevo_pedido

@router.post("/pedidos/marcar_listo/{pedido_id}", response_model=schemas.Pedido)
def route_marcar_listo(
    pedido_id: int,
    db: Session = Depends(database.get_db)
    # Aquí iría la validación de una API Key del Panel de Cocina
):
    """
    Endpoint para que la COCINA marque un pedido como 'LISTO_PARA_RECOGER'.
    Esto inicia el proceso de asignación.
    (Fase 2 del flujo)
    """
    pedido = crud.get_pedido(db, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.estado_pedido != 'EN_PREPARACION':
         raise HTTPException(status_code=400, detail=f"Solo se puede marcar como listo un pedido 'EN_PREPARACION'. Estado actual: {pedido.estado_pedido}")

    pedido_actualizado = crud.actualizar_estado_pedido(db, pedido_id, 'LISTO_PARA_RECOGER')
    
    # ¡INICIAR ASIGNACIÓN!
    iniciar_proceso_de_asignacion(db, pedido_actualizado)
    
    return pedido_actualizado

# (Opcional) Endpoint para que la cocina acepte el pedido
@router.post("/pedidos/aceptar_cocina/{pedido_id}", response_model=schemas.Pedido)
def route_aceptar_cocina(
    pedido_id: int,
    db: Session = Depends(database.get_db)
    # Aquí iría la validación de una API Key del Panel de Cocina
):
    """
    Endpoint para que la COCINA acepte un pedido 'PENDIENTE_CONFIRMACION'.
    """
    pedido = crud.get_pedido(db, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.estado_pedido != 'PENDIENTE_CONFIRMACION':
         raise HTTPException(status_code=400, detail=f"Solo se puede aceptar un pedido 'PENDIENTE_CONFIRMACION'. Estado actual: {pedido.estado_pedido}")

    pedido_actualizado = crud.actualizar_estado_pedido(db, pedido_id, 'EN_PREPARACION')
    
    notifications.notify_telegram_bot(
        cliente_telegram_id=pedido.cliente.telegram_user_id,
        message="¡Tu pedido ha sido confirmado! Ya lo estamos preparando. 🧑‍🍳"
    )
    
    return pedido_actualizado