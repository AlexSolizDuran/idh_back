from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, DECIMAL, VARCHAR, BigInteger, func
from sqlalchemy.orm import relationship
from .database import Base

class Repartidor(Base):
    __tablename__ = "repartidor"

    repartidor_id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    edad = Column(String(10),unique=False,nullable=False)
    hash_contrasena = Column(String(255), nullable=False)
    telefono = Column(String(20), nullable=True)
    estado_disponibilidad = Column(VARCHAR(20), nullable=False, default='no_disponible')
    fecha_creacion = Column(DateTime, default=func.now())

    # Relación uno-a-muchos: Un repartidor puede tener muchos pedidos
    pedidos = relationship("Pedido", back_populates="repartidor")
    
    vehiculo = relationship("Vehiculo", back_populates="repartidor", uselist=False)
    
class Vehiculo(Base):
    __tablename__ = "vehiculo"

    vehiculo_id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(15), unique=True, nullable=False, index=True) # Matrícula/Patente
    marca = Column(String(50), nullable=True)
    modelo = Column(String(50), nullable=True)
    color = Column(String(30), nullable=True)
    tipo = Column(VARCHAR(20), nullable=False, default='motocicleta') # E.g., 'motocicleta', 'automovil', 'bicicleta'
    
    # --- Clave para la relación 1-a-1 ---
    # La clave foránea apunta al repartidor
    # 'unique=True' es lo que fuerza la relación 1-a-1 (un vehículo por repartidor)
    repartidor_id = Column(Integer, ForeignKey("repartidor.repartidor_id"), unique=True, nullable=False)

    # --- Relación de vuelta (back-populates) ---
    repartidor = relationship("Repartidor", back_populates="vehiculo")
    
class Cliente(Base):
    __tablename__ = "cliente"

    cliente_id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    nombre_telegram = Column(String(100), nullable=True)
    telefono_contacto = Column(String(20), nullable=True)
    fecha_creacion = Column(DateTime, default=func.now())

    # Relación uno-a-muchos: Un cliente puede tener muchos pedidos
    pedidos = relationship("Pedido", back_populates="cliente")

class Pedido(Base):
    __tablename__ = "pedido"

    pedido_id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("cliente.cliente_id"), nullable=False)
    repartidor_id = Column(Integer, ForeignKey("repartidor.repartidor_id"), nullable=True, index=True)
    
    estado_pedido = Column(VARCHAR(30), nullable=False, default='PENDIENTE_CONFIRMACION', index=True)
    descripcion_pedido = Column(Text, nullable=False)
    direccion_entrega = Column(Text, nullable=False)
    instrucciones_entrega = Column(Text, nullable=True)
    monto_total = Column(DECIMAL(10, 2), nullable=False)
    
    fecha_creacion = Column(DateTime, default=func.now())
    fecha_recogido = Column(DateTime, nullable=True)
    fecha_entregado = Column(DateTime, nullable=True)

    # Relaciones muchos-a-uno
    cliente = relationship("Cliente", back_populates="pedidos")
    repartidor = relationship("Repartidor", back_populates="pedidos")