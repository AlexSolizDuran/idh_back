from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, DECIMAL, VARCHAR, BigInteger, Float, func
from sqlalchemy.orm import relationship
from .database import Base

class Repartidor(Base):
    __tablename__ = "repartidor"

    repartidor_id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    edad = Column(String(10), unique=False, nullable=False)
    hash_contrasena = Column(String(255), nullable=False)
    telefono = Column(String(20), nullable=True)
    estado_disponibilidad = Column(VARCHAR(20), nullable=False, default='no_disponible')
    
    # --- CAMPOS DE UBICACIÓN (Necesarios para la demo) ---
    latitud = Column(Float, nullable=True, default=0.0)
    longitud = Column(Float, nullable=True, default=0.0)
    
    fecha_creacion = Column(DateTime, default=func.now())

    # Relaciones
    pedidos = relationship("Pedido", back_populates="repartidor")
    vehiculo = relationship("Vehiculo", back_populates="repartidor", uselist=False)

class Vehiculo(Base):
    __tablename__ = "vehiculo"

    vehiculo_id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(15), unique=True, nullable=False, index=True)
    marca = Column(String(50), nullable=True)
    modelo = Column(String(50), nullable=True)
    color = Column(String(30), nullable=True)
    tipo = Column(VARCHAR(20), nullable=False, default='motocicleta')
    
    repartidor_id = Column(Integer, ForeignKey("repartidor.repartidor_id"), unique=True, nullable=False)
    repartidor = relationship("Repartidor", back_populates="vehiculo")

class Cliente(Base):
    __tablename__ = "cliente"

    cliente_id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    nombre_telegram = Column(String(100), nullable=True)
    telefono_contacto = Column(String(20), nullable=True)
    fecha_creacion = Column(DateTime, default=func.now())

    # Relación inversa (Aquí fallaba si no encontraba la FK en Pedido)
    pedidos = relationship("Pedido", back_populates="cliente")

class Pedido(Base):
    __tablename__ = "pedido"

    pedido_id = Column(Integer, primary_key=True, index=True)
    
    # --- CLAVES FORÁNEAS (Importantes para que relationship funcione) ---
    cliente_id = Column(Integer, ForeignKey("cliente.cliente_id"), nullable=False)
    repartidor_id = Column(Integer, ForeignKey("repartidor.repartidor_id"), nullable=True, index=True)
    
    estado_pedido = Column(VARCHAR(30), nullable=False, default='PENDIENTE_CONFIRMACION', index=True)
    descripcion_pedido = Column(Text, nullable=False)
    direccion_entrega = Column(Text, nullable=False)
    instrucciones_entrega = Column(Text, nullable=True)
    monto_total = Column(DECIMAL(10, 2), nullable=False)
    
    latitud_cliente = Column(Float, nullable=True)
    longitud_cliente = Column(Float, nullable=True)
    # --- CAMPO PARA LOGICA DE RECHAZOS ---
    repartidores_rechazados = Column(Text, default="") 

    fecha_creacion = Column(DateTime, default=func.now())
    fecha_recogido = Column(DateTime, nullable=True)
    fecha_entregado = Column(DateTime, nullable=True)

    # Relaciones
    cliente = relationship("Cliente", back_populates="pedidos")
    repartidor = relationship("Repartidor", back_populates="pedidos")