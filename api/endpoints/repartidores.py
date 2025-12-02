from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from db import crud, schemas, database, models
from core import security
from core.security import TokenData

router = APIRouter()

# --- Dependencia de autenticación ---
async def get_current_repartidor(token: str = Header(..., alias="Authorization"), db: Session = Depends(database.get_db)) -> models.Repartidor:
    """
    Dependencia que valida el token JWT y retorna el modelo del repartidor.
    """
    if not token.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Formato de token inválido")
    
    token = token.split("Bearer ")[1]
    
    token_data: TokenData = security.decode_access_token(token)
    if token_data is None or token_data.repartidor_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
        
    repartidor = crud.get_repartidor(db, repartidor_id=token_data.repartidor_id)
    if repartidor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repartidor no encontrado")
    
    return repartidor

# --- Endpoints ---

@router.put("/repartidor/status", response_model=schemas.Repartidor)
def update_status(
    status_update: schemas.RepartidorUpdateStatus,
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    Endpoint protegido para que el repartidor actualice su estado de disponibilidad.
    (Fase 1 del flujo)
    """
    # Validar el estado
    valid_statuses = ['disponible', 'no_disponible']
    if status_update.estado_disponibilidad not in valid_statuses:
        raise HTTPException(status_code=400, detail="Estado no válido. Debe ser 'disponible' o 'no_disponible'.")

    # No permitir cambiar a 'disponible' si está en medio de una entrega
    pedido_activo = crud.get_pedido_activo_repartidor(db, repartidor_id=repartidor_actual.repartidor_id)
    if pedido_activo and status_update.estado_disponibilidad == 'disponible':
         raise HTTPException(status_code=400, detail="No puedes marcarte como 'disponible' mientras tienes un pedido activo.")

    updated_repartidor = crud.update_repartidor_status(
        db, 
        repartidor_id=repartidor_actual.repartidor_id, 
        estado=status_update.estado_disponibilidad,
        lat=status_update.latitud,   # <--- NUEVO
        lon=status_update.longitud   # <--- NUEVO
    )
    return updated_repartidor

@router.get("/repartidor/me", response_model=schemas.Repartidor)
def read_repartidor_me(repartidor_actual: models.Repartidor = Depends(get_current_repartidor)):
    """
    Endpoint para que el repartidor obtenga su propia información.
    """
    print(repartidor_actual)
    return repartidor_actual

@router.get("/repartidor/pedidos/activo", response_model=schemas.Pedido, responses={404: {"description": "No hay pedido activo"}})
def get_active_order(
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    Busca si el repartidor tiene un pedido activo.
    Útil si el repartidor cierra y abre la app.
    (Fase 1/3/4/5 del flujo)
    """
    pedido_activo = crud.get_pedido_activo_repartidor(db, repartidor_id=repartidor_actual.repartidor_id)
    if not pedido_activo:
        raise HTTPException(status_code=404, detail="No tienes ningún pedido activo en este momento.")
    return pedido_activo



@router.put("/repartidor/me", response_model=schemas.Repartidor)
def update_repartidor_me(
    repartidor_data: schemas.RepartidorUpdate, # Schema de entrada (ver paso 2)
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    Endpoint para que el repartidor actualice sus propios datos
    (nombre, teléfono).
    """
    updated_repartidor = crud.update_repartidor( # Función CRUD (ver paso 3)
        db, 
        repartidor_id=repartidor_actual.repartidor_id, 
        data=repartidor_data
    )
    if not updated_repartidor:
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Repartidor no encontrado."
        )
    return updated_repartidor

@router.put("/repartidor/vehiculo", response_model=schemas.Vehiculo)
def update_vehiculo_me(
    vehiculo_data: schemas.VehiculoUpdate, # Schema de entrada (ver paso 2)
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    Endpoint para que el repartidor actualice la información de su vehículo.
    El vehículo se crea en el seeder, aquí solo se actualiza.
    """
    updated_vehiculo = crud.update_vehiculo( # Función CRUD que ya te había pasado
        db, 
        repartidor_id=repartidor_actual.repartidor_id, 
        vehiculo_data=vehiculo_data
    )
    if not updated_vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No se encontró un vehículo para este repartidor."
        )
    return updated_vehiculo



@router.get("/repartidor/vehiculo", response_model=schemas.Vehiculo, responses={404: {"description": "Vehículo no encontrado"}})
def get_vehiculo_me(
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    Endpoint para que el repartidor obtenga la información de su vehículo.
    """
    # Usamos la función CRUD que ya existe
    vehiculo = crud.get_vehiculo_by_repartidor(db, repartidor_id=repartidor_actual.repartidor_id)
    
    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes un vehículo asignado."
        )
    return vehiculo

@router.get("/repartidor/me/pedidos", response_model=list[schemas.Pedido])
def get_mis_pedidos(
    db: Session = Depends(database.get_db),
    repartidor_actual: models.Repartidor = Depends(get_current_repartidor)
):
    """
    Obtiene el historial de todos los pedidos asignados a este repartidor.
    """
    pedidos = crud.get_pedidos_by_repartidor(db, repartidor_id=repartidor_actual.repartidor_id)
    return pedidos