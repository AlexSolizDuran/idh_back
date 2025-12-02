from pydantic import BaseModel, EmailStr,ConfigDict
from typing import Optional, List
from datetime import datetime


# --- Esquemas Base ---

class RepartidorBase(BaseModel):
    nombre_completo: str
    email: EmailStr
    edad: str
    telefono: Optional[str] = None

class PedidoBase(BaseModel):
    descripcion_pedido: str
    direccion_entrega: str
    monto_total: float
    instrucciones_entrega: Optional[str] = None

class ClienteBase(BaseModel):
    telegram_user_id: int
    nombre_telegram: Optional[str] = None
    telefono_contacto: Optional[str] = None

# --- Esquemas para Creación (Create) ---

class RepartidorCreate(RepartidorBase):
    password: str

class PedidoCreate(PedidoBase):
    cliente_telegram_id: int # El bot enviará el ID de Telegram

class ClienteCreate(ClienteBase):
    pass

# --- Esquemas para Lectura (Read) ---

class Cliente(ClienteBase):
    cliente_id: int
    fecha_creacion: datetime

    class Config:
        orm_mode = True # Modo ORM

class Pedido(PedidoBase):
    pedido_id: int
    repartidor_id: Optional[int] = None
    estado_pedido: str
    fecha_creacion: datetime
    latitud_cliente: Optional[float] = None
    longitud_cliente: Optional[float] = None
    cliente:Cliente
    class Config:
        orm_mode = True # Modo ORM

class Repartidor(RepartidorBase):
    repartidor_id: int
    estado_disponibilidad: str
    fecha_creacion: datetime
    pedidos: List[Pedido] = [] # Lista de pedidos del repartidor

    class Config:
        orm_mode = True # Modo ORM

# --- Esquemas para Actualización (Update) ---

class RepartidorUpdateStatus(BaseModel):
    estado_disponibilidad: str
    latitud: Optional[float] = None  # <--- NUEVO
    longitud: Optional[float] = None # <--- NUEVO

# --- Esquemas de Autenticación ---

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    
    

class VehiculoBase(BaseModel):
    placa: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    color: Optional[str] = None
    tipo: str = "motocicleta"

class VehiculoCreate(VehiculoBase):
    pass # Este schema ya lo deberías tener para tu seeder

class VehiculoUpdate(BaseModel):
    """Schema para actualizar un vehículo. Todos los campos son opcionales."""
    placa: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    color: Optional[str] = None
    tipo: Optional[str] = None

class Vehiculo(VehiculoBase):
    """Schema para leer un vehículo (respuesta de la API)."""
    vehiculo_id: int
    repartidor_id: int
    
    model_config = ConfigDict(from_attributes=True)


# --- NUEVO SCHEMA PARA ACTUALIZAR REPARTIDOR ---

class RepartidorUpdate(BaseModel):
    """Schema para actualizar los datos del repartidor. Todos opcionales."""
    nombre_completo: Optional[str] = None
    telefono: Optional[str] = None