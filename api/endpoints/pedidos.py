from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import asyncio
import math
import time

from db import crud, schemas, database, models
from api.endpoints.repartidores import get_current_repartidor
from services import notifications

router = APIRouter()

# ==========================================
# CONFIGURACIÓN DE GEOLOCALIZACIÓN
# ==========================================

# Coordenadas fijas de la SUCURSAL ÚNICA (Ejemplo: Plaza 24 de Septiembre, Santa Cruz)
SUCURSAL_LAT = -17.783328
SUCURSAL_LON = -63.182141

def calcular_distancia(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia en Kilómetros entre dos puntos usando la fórmula de Haversine.
    Retorna 9999.0 km si alguna coordenada no existe.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 9999.0
    
    R = 6371 # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ==========================================
# LÓGICA DE NEGOCIO CORE (ASIGNACIÓN)
# ==========================================

async def ciclo_asignacion_pedido(pedido_id: int, db: Session):
    """
    MOTOR DE ASIGNACIÓN INTELIGENTE:
    1. Busca repartidores disponibles.
    2. Filtra los que ya rechazaron este pedido.
    3. Los ordena por cercanía a la SUCURSAL.
    4. Asigna al mejor y espera 5 segundos.
    5. Si no acepta, lo añade a rechazados y pasa al siguiente (recursivo).
    """
    print(f"\n--- 🔄 INICIANDO CICLO DE ASIGNACIÓN PARA PEDIDO #{pedido_id} ---")
    
    # 1. Obtener estado actual del pedido
    pedido = crud.get_pedido(db, pedido_id)
    # Si el pedido no existe o ya cambió de estado (alguien lo aceptó), paramos.
    if not pedido or pedido.estado_pedido != 'BUSCANDO_REPARTIDOR':
        print(f"Deteniendo ciclo: El pedido #{pedido_id} ya no está buscando (Estado: {pedido.estado_pedido if pedido else 'None'}).")
        return

    # 2. Obtener todos los repartidores que están 'disponible'
    candidatos_totales = crud.get_repartidores_disponibles(db)
    
    # 3. Filtrar rechazados
    ids_rechazados = []
    if pedido.repartidores_rechazados:
        ids_rechazados = [int(x) for x in pedido.repartidores_rechazados.split(",") if x]
    
    candidatos_validos = [r for r in candidatos_totales if r.repartidor_id not in ids_rechazados]

    if not candidatos_validos:
        print("❌ ALERTA: No quedan repartidores disponibles.")
        
        # --- NUEVO: AVISAR AL CLIENTE QUE NO HAY NADIE ---
        notifications.notify_telegram_bot(
            pedido.cliente.telegram_user_id,
            "😔 Lo sentimos, no hay repartidores disponibles cerca en este momento. Intenta de nuevo más tarde."
        )
        # -------------------------------------------------
        return

    # 4. ORDENAMIENTO POR CERCANÍA (La Novedad)
    # Calculamos la distancia de cada uno a la Sucursal y ordenamos de menor a mayor.
    candidatos_validos.sort(key=lambda r: calcular_distancia(
        SUCURSAL_LAT, SUCURSAL_LON, r.latitud, r.longitud
    ))

    # El primero de la lista es el ganador
    mejor_repartidor = candidatos_validos[0]
    distancia = calcular_distancia(SUCURSAL_LAT, SUCURSAL_LON, mejor_repartidor.latitud, mejor_repartidor.longitud)
    
    print(f"📍 Asignando a: {mejor_repartidor.nombre_completo} (Distancia: {distancia:.2f} km)")

    # 5. Asignar temporalmente en BD
    pedido.repartidor_id = mejor_repartidor.repartidor_id
    db.commit()

    # 6. Enviar Notificación Push (Simulado)
    notifications.send_push_notification(
        repartidor_id=mejor_repartidor.repartidor_id, 
        title="¡Tienes un Pedido Cercano!", 
        body="Acepta en 5 segundos o pasará al siguiente."
    )

    # 7. --- ESPERAR 5 SEGUNDOS (Timeout) ---
    print(f"⏳ Esperando respuesta de {mejor_repartidor.nombre_completo}...")
    await asyncio.sleep(20)

    # 8. Verificación Post-Espera
    # Refrescamos el objeto pedido para ver si el repartidor lo aceptó
    db.refresh(pedido)
    
    # Si el estado sigue siendo 'BUSCANDO_REPARTIDOR' y el ID sigue siendo el mismo...
    # Significa que se le acabó el tiempo.
    if pedido.estado_pedido == 'BUSCANDO_REPARTIDOR' and pedido.repartidor_id == mejor_repartidor.repartidor_id:
        print(f"🚫 Tiempo agotado. {mejor_repartidor.nombre_completo} no respondió.")
        
        # Agregamos a este repartidor a la lista de rechazados
        nuevo_rechazo = f"{pedido.repartidores_rechazados},{mejor_repartidor.repartidor_id}".strip(",")
        pedido.repartidores_rechazados = nuevo_rechazo
        
        # Le quitamos el pedido
        pedido.repartidor_id = None
        db.commit()
        
        # LLAMADA RECURSIVA: Volvemos a empezar el ciclo inmediatamente
        await ciclo_asignacion_pedido(pedido_id, db)

# ==========================================
# ENDPOINTS: CREACIÓN Y COCINA
# ==========================================

@router.post("/pedidos", response_model=schemas.Pedido, status_code=status.HTTP_201_CREATED)
def route_create_pedido(
    pedido: schemas.PedidoCreate, 
    db: Session = Depends(database.get_db)
):
    """
    Crea un pedido inicial (Estado: PENDIENTE_CONFIRMACION).
    Usado por el Bot.
    """
    return crud.create_pedido(db, pedido)

@router.post("/pedidos/aceptar_cocina/{pedido_id}", response_model=schemas.Pedido)
def route_aceptar_cocina(
    pedido_id: int,
    db: Session = Depends(database.get_db)
):
    """
    La cocina acepta el pedido (Estado: EN_PREPARACION).
    """
    pedido = crud.get_pedido(db, pedido_id)
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    
    # Permitimos pasar de PENDIENTE a EN_PREPARACION
    return crud.actualizar_estado_pedido(db, pedido_id, 'EN_PREPARACION')

@router.post("/pedidos/marcar_listo/{pedido_id}", response_model=schemas.Pedido)
async def route_marcar_listo(
    pedido_id: int,
    background_tasks: BackgroundTasks, # Importante para el proceso en segundo plano
    db: Session = Depends(database.get_db)
):
    """
    La cocina marca el pedido como LISTO.
    ESTO DISPARA EL ALGORITMO DE ASIGNACIÓN.
    """
    pedido = crud.get_pedido(db, pedido_id)
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")

    # Reseteamos la lista de rechazados por si es un reintento
    pedido.repartidores_rechazados = "" 
    
    # Cambiamos estado a BUSCANDO
    updated_pedido = crud.actualizar_estado_pedido(db, pedido_id, 'BUSCANDO_REPARTIDOR')
    
    # Lanzamos el ciclo en background (Fire & Forget)
    background_tasks.add_task(ciclo_asignacion_pedido, pedido_id, db)
    
    return updated_pedido

# ==========================================
# ENDPOINTS: FLUJO DEL REPARTIDOR
# ==========================================

@router.post("/pedidos/aceptar/{pedido_id}", response_model=schemas.Pedido)
def aceptar_pedido(
    pedido_id: int,
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    El repartidor acepta el pedido asignado (Detiene el temporizador).
    """
    pedido = crud.get_pedido(db, pedido_id)
    
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    
    # Validar que el pedido siga asignado a él (puede que haya expirado hace milisegundos)
    if pedido.repartidor_id != repartidor_actual.repartidor_id:
        raise HTTPException(400, "El tiempo ha expirado o el pedido fue reasignado.")
        
    if pedido.estado_pedido != 'BUSCANDO_REPARTIDOR':
        raise HTTPException(400, "El pedido ya no está disponible para aceptar.")

    # Cambio de estado -> Esto detendrá el ciclo async en su próxima verificación
    pedido_actualizado = crud.actualizar_estado_pedido(db, pedido_id, 'EN_CAMINO_AL_RESTAURANTE')
    
    # --- NUEVO: AVISAR AL CLIENTE ---
    notifications.notify_telegram_bot(
        pedido.cliente.telegram_user_id,
        f"✅ ¡Repartidor Asignado!\n\n👤 {repartidor_actual.nombre_completo} ha aceptado tu pedido y va hacia el restaurante."
    )
    # --------------------------------
    
    return pedido_actualizado

@router.post("/pedidos/rechazar/{pedido_id}", response_model=schemas.Pedido)
async def rechazar_pedido(
    pedido_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    El repartidor rechaza explícitamente el pedido.
    Dispara la búsqueda del siguiente candidato INMEDIATAMENTE.
    """
    pedido = crud.get_pedido(db, pedido_id)

    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    if pedido.repartidor_id != repartidor_actual.repartidor_id:
        raise HTTPException(400, "No puedes rechazar un pedido que no es tuyo.")

    print(f"🚫 Repartidor {repartidor_actual.nombre_completo} rechazó manualmente.")

    # 1. Agregar a rechazados
    nuevo_rechazo = f"{pedido.repartidores_rechazados},{repartidor_actual.repartidor_id}".strip(",")
    pedido.repartidores_rechazados = nuevo_rechazo
    
    # 2. Desasignar
    pedido.repartidor_id = None
    db.commit()

    # 3. Disparar ciclo inmediatamente (para no esperar los 5s del sleep anterior)
    background_tasks.add_task(ciclo_asignacion_pedido, pedido_id, db)
    
    return pedido

@router.post("/pedidos/recoger/{pedido_id}", response_model=schemas.Pedido)
def recoger_pedido(
    pedido_id: int,
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    El repartidor indica que ya tiene el paquete.
    """
    pedido = crud.get_pedido(db, pedido_id)
    if not pedido or pedido.repartidor_id != repartidor_actual.repartidor_id:
        raise HTTPException(400, "Operación no válida.")
    if pedido.estado_pedido != 'EN_CAMINO_AL_RESTAURANTE':
        raise HTTPException(400, "Estado incorrecto del pedido.")
        
    # Actualizar estado
    upd_pedido = crud.actualizar_estado_pedido(db, pedido_id, 'EN_CAMINO_AL_CLIENTE')
    
    # Notificar al cliente
    notifications.notify_telegram_bot(
        pedido.cliente.telegram_user_id, 
        f"🛵 ¡Tu pedido va en camino! Repartidor: {repartidor_actual.nombre_completo}"
    )
    return upd_pedido

@router.post("/pedidos/completar/{pedido_id}", response_model=schemas.Pedido)
def completar_pedido(
    pedido_id: int,
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    El repartidor finaliza la entrega.
    """
    pedido = crud.get_pedido(db, pedido_id)
    if not pedido or pedido.repartidor_id != repartidor_actual.repartidor_id:
        raise HTTPException(400, "Operación no válida.")
    if pedido.estado_pedido != 'EN_CAMINO_AL_CLIENTE':
        raise HTTPException(400, "No se puede completar aún.")

    # Finalizar pedido
    upd_pedido = crud.actualizar_estado_pedido(db, pedido_id, 'ENTREGADO')
    
    # Liberar al repartidor para recibir nuevos pedidos
    crud.update_repartidor_status(db, repartidor_actual.repartidor_id, 'disponible')
    
    notifications.notify_telegram_bot(
        pedido.cliente.telegram_user_id, 
        "✅ ¡Pedido entregado! Gracias por tu compra."
    )
    return upd_pedido