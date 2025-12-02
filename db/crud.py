from sqlalchemy.orm import Session
from datetime import datetime, timezone
from . import models, schemas
from core.security import get_password_hash

# --- Repartidor CRUD ---

def get_repartidor_by_email(db: Session, email: str) -> models.Repartidor:
    """Busca un repartidor por su email."""
    return db.query(models.Repartidor).filter(models.Repartidor.email == email).first()

def get_repartidor(db: Session, repartidor_id: int) -> models.Repartidor:
    """Busca un repartidor por su ID."""
    return db.query(models.Repartidor).filter(models.Repartidor.repartidor_id == repartidor_id).first()

def create_repartidor(db: Session, repartidor: schemas.RepartidorCreate) -> models.Repartidor:
    """Crea un nuevo repartidor (con contraseña hasheada)."""
    hashed_password = get_password_hash(repartidor.password)
    db_repartidor = models.Repartidor(
        email=repartidor.email,
        nombre_completo=repartidor.nombre_completo,
        telefono=repartidor.telefono,
        hash_contrasena=hashed_password
    )
    db.add(db_repartidor)
    db.commit()
    db.refresh(db_repartidor)
    return db_repartidor

def update_repartidor_status(db: Session, repartidor_id: int, estado: str, lat: float = None, lon: float = None):
    db_repartidor = get_repartidor(db, repartidor_id)
    if db_repartidor:
        db_repartidor.estado_disponibilidad = estado
        if lat is not None and lon is not None: # <--- NUEVO
            db_repartidor.latitud = lat
            db_repartidor.longitud = lon
        db.commit()
        db.refresh(db_repartidor)
    return db_repartidor

# --- Cliente CRUD ---

def get_cliente_by_telegram_id(db: Session, telegram_id: int) -> models.Cliente:
    """Busca un cliente por su ID de Telegram."""
    return db.query(models.Cliente).filter(models.Cliente.telegram_user_id == telegram_id).first()

def get_or_create_cliente(db: Session, cliente_data: schemas.ClienteCreate) -> models.Cliente:
    """Busca un cliente por su ID de Telegram, o lo crea si no existe."""
    db_cliente = get_cliente_by_telegram_id(db, cliente_data.telegram_user_id)
    if db_cliente:
        return db_cliente
    
    # Crear nuevo cliente
    db_cliente = models.Cliente(
        telegram_user_id=cliente_data.telegram_user_id,
        nombre_telegram=cliente_data.nombre_telegram,
        telefono_contacto=cliente_data.telefono_contacto
    )
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

# --- Pedido CRUD ---

def create_pedido(db: Session, pedido: schemas.PedidoCreate) -> models.Pedido:
    """
    Crea un nuevo pedido. Esta función sería llamada por el bot de Telegram.
    """
    # 1. Buscar o crear al cliente
    cliente_data = schemas.ClienteCreate(telegram_user_id=pedido.cliente_telegram_id)
    db_cliente = get_or_create_cliente(db, cliente_data)
    
    # 2. Crear el pedido
    db_pedido = models.Pedido(
        cliente_id=db_cliente.cliente_id,
        descripcion_pedido=pedido.descripcion_pedido,
        direccion_entrega=pedido.direccion_entrega,
        monto_total=pedido.monto_total,
        instrucciones_entrega=pedido.instrucciones_entrega,
        estado_pedido='PENDIENTE_CONFIRMACION' # Estado inicial
    )
    db.add(db_pedido)
    db.commit()
    db.refresh(db_pedido)
    return db_pedido

def get_pedidos_listos_para_recoger(db: Session) -> list[models.Pedido]:
    """
    (Endpoint interno, o para un dashboard de cocina)
    Busca pedidos que la cocina marcó como listos.
    """
    return db.query(models.Pedido).filter(models.Pedido.estado_pedido == 'LISTO_PARA_RECOGER').all()

def get_repartidores_disponibles(db: Session) -> list[models.Repartidor]:
    """Busca repartidores con estado 'disponible'."""
    return db.query(models.Repartidor).filter(models.Repartidor.estado_disponibilidad == 'disponible').all()

def get_pedido(db: Session, pedido_id: int) -> models.Pedido:
    """Busca un pedido específico por ID."""
    return db.query(models.Pedido).filter(models.Pedido.pedido_id == pedido_id).first()

def get_pedido_activo_repartidor(db: Session, repartidor_id: int) -> models.Pedido:
    """
    Busca si el repartidor tiene un pedido activo.
    (Estados: BUSCANDO, EN_CAMINO_AL_RESTAURANTE, EN_CAMINO_AL_CLIENTE)
    """
    estados_activos = ['BUSCANDO_REPARTIDOR', 'EN_CAMINO_AL_RESTAURANTE', 'EN_CAMINO_AL_CLIENTE']
    return db.query(models.Pedido).filter(models.Pedido.repartidor_id == repartidor_id).filter(models.Pedido.estado_pedido.in_(estados_activos)).first()

def get_pedidos_by_repartidor(db: Session, repartidor_id: int) -> list[models.Pedido]:
    """Busca todos los pedidos de un repartidor."""
    return db.query(models.Pedido).filter(models.Pedido.repartidor_id == repartidor_id).all()

def asignar_pedido_a_repartidor(db: Session, pedido_id: int, repartidor_id: int) -> models.Pedido:
    """Asigna un pedido a un repartidor y cambia estado a 'BUSCANDO_REPARTIDOR'."""
    db_pedido = get_pedido(db, pedido_id)
    db_repartidor = get_repartidor(db, repartidor_id)
    
    if not db_pedido or not db_repartidor:
        return None
        
    db_pedido.repartidor_id = repartidor_id
    db_pedido.estado_pedido = 'BUSCANDO_REPARTIDOR'
    db.commit()
    db.refresh(db_pedido)
    return db_pedido

def actualizar_estado_pedido(db: Session, pedido_id: int, nuevo_estado: str) -> models.Pedido:
    """Actualiza el estado de un pedido y añade timestamps si es necesario."""
    db_pedido = get_pedido(db, pedido_id)
    if not db_pedido:
        return None
    
    db_pedido.estado_pedido = nuevo_estado
    
    if nuevo_estado == 'EN_CAMINO_AL_CLIENTE':
        db_pedido.fecha_recogido = datetime.now(timezone.utc)
    elif nuevo_estado == 'ENTREGADO':
        db_pedido.fecha_entregado = datetime.now(timezone.utc)
        
    db.commit()
    db.refresh(db_pedido)
    return db_pedido


# --- Vehiculo CRUD ---

def get_vehiculo(db: Session, vehiculo_id: int) -> models.Vehiculo:
    """Busca un vehículo por su ID."""
    return db.query(models.Vehiculo).filter(models.Vehiculo.vehiculo_id == vehiculo_id).first()

def get_vehiculo_by_repartidor(db: Session, repartidor_id: int) -> models.Vehiculo:
    """Busca el vehículo asignado a un repartidor (por la relación 1-a-1)."""
    return db.query(models.Vehiculo).filter(models.Vehiculo.repartidor_id == repartidor_id).first()

def get_vehiculo_by_placa(db: Session, placa: str) -> models.Vehiculo:
    """Busca un vehículo por su número de placa (matrícula)."""
    return db.query(models.Vehiculo).filter(models.Vehiculo.placa == placa).first()

def create_vehiculo(db: Session, vehiculo: schemas.VehiculoCreate, repartidor_id: int) -> models.Vehiculo:
    """
    Crea un nuevo vehículo y lo asigna a un repartidor.
    Asume que el repartidor NO tiene un vehículo (debido a la restricción 1-a-1).
    """
    # Creamos el objeto del modelo SQLAlchemy
    db_vehiculo = models.Vehiculo(
        placa=vehiculo.placa,
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
        color=vehiculo.color,
        tipo=vehiculo.tipo,
        repartidor_id=repartidor_id  # Asignación clave
    )
    db.add(db_vehiculo)
    db.commit()
    db.refresh(db_vehiculo)
    return db_vehiculo

def update_vehiculo(db: Session, repartidor_id: int, vehiculo_data: schemas.VehiculoUpdate) -> models.Vehiculo:
    """
    Actualiza la información del vehículo de un repartidor.
    Busca el vehículo usando el repartidor_id.
    """
    db_vehiculo = get_vehiculo_by_repartidor(db, repartidor_id)
    if not db_vehiculo:
        return None

    # Convierte el schema de Pydantic a un dict, excluyendo los campos
    # que no se enviaron (para no sobrescribir con None)
    update_data = vehiculo_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if hasattr(db_vehiculo, key):
            setattr(db_vehiculo, key, value)

    db.commit()
    db.refresh(db_vehiculo)
    return db_vehiculo

# db/crud.py

# ... (después de tu función 'update_repartidor_status') ...

def update_repartidor(db: Session, repartidor_id: int, data: schemas.RepartidorUpdate) -> models.Repartidor:
    """
    Actualiza los datos de un repartidor (nombre, teléfono).
    """
    db_repartidor = get_repartidor(db, repartidor_id)
    if not db_repartidor:
        return None
    
    # Convierte el schema de Pydantic a un dict, excluyendo los campos
    # que no se enviaron (para no sobrescribir con None)
    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if hasattr(db_repartidor, key):
            setattr(db_repartidor, key, value)
            
    db.commit()
    db.refresh(db_repartidor)
    return db_repartidor

def get_pedidos_by_repartidor(db: Session, repartidor_id: int) -> list[models.Pedido]:
    """Busca TODOS los pedidos de un repartidor, ordenados por fecha."""
    return db.query(models.Pedido)\
             .filter(models.Pedido.repartidor_id == repartidor_id)\
             .order_by(models.Pedido.fecha_creacion.desc())\
             .all()
             
             
def actualizar_ubicacion_pedido(db: Session, telegram_id: int, lat: float, lon: float):
    # 1. Buscar al cliente
    cliente = get_cliente_by_telegram_id(db, telegram_id)
    if not cliente:
        return None
        
    # 2. Buscar su último pedido activo (PENDIENTE o BUSCANDO)
    pedido = db.query(models.Pedido)\
        .filter(models.Pedido.cliente_id == cliente.cliente_id)\
        .order_by(models.Pedido.pedido_id.desc())\
        .first()
        
    if pedido:
        pedido.latitud_cliente = lat
        pedido.longitud_cliente = lon
        db.commit()
        db.refresh(pedido)
        return pedido
    return None