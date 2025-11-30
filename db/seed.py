import sys
#import os

# Añadir el directorio raíz del proyecto al sys.path
# Esto es necesario para que los imports funcionen correctamente cuando se ejecuta el script directamente
#sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy.orm import Session

from db.database import SessionLocal, engine, Base
from db.models import Repartidor, Cliente, Pedido, Vehiculo
from core.security import get_password_hash
from decimal import Decimal

def seed_data():
    """
    Esta función borra la base de datos existente, crea las tablas de nuevo
    y la puebla con datos de ejemplo.
    """
    print("Borrando y recreando la base de datos...")
    # Borra todas las tablas y las vuelve a crear. ¡CUIDADO! Esto elimina todos los datos.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Crea una nueva sesión de base de datos
    db: Session = SessionLocal()

    try:
        print("Insertando datos de ejemplo...")

        # --- Crear Repartidores con Ubicación ---
        # Repartidor 1: Juan Pérez (Ubicado MUY CERCA de la sucursal)
        # Ganará la asignación automática por cercanía.
        repartidor1 = Repartidor(
            nombre_completo="Juan Pérez",
            email="prueba1@gmail.com",
            # Como get_password_hash ahora devuelve texto plano, esto guardará "123456"
            hash_contrasena=get_password_hash("123456"),
            edad="25",
            telefono="123456789",
            estado_disponibilidad="disponible",
            latitud=-17.783300, # A unos metros del restaurante
            longitud=-63.182100
        )

        # Repartidor 2: Ana Gómez (Ubicada un poco más lejos)
        # Será la segunda opción si Juan rechaza.
        repartidor2 = Repartidor(
            nombre_completo="Ana Gómez",
            email="prueba2@gmail.com",
            hash_contrasena=get_password_hash("123456"),
            edad="20",
            telefono="987654321",
            estado_disponibilidad="disponible", 
            latitud=-17.785000, # A unas cuadras
            longitud=-63.185000
        )

        db.add(repartidor1)
        db.add(repartidor2)
        db.commit()

        # --- Crear Clientes ---
        cliente1 = Cliente(
            telegram_user_id=111111,
            nombre_telegram="user_telegram_1",
            telefono_contacto="555111222"
        )
        cliente2 = Cliente(
            telegram_user_id=222222,
            nombre_telegram="user_telegram_2",
            telefono_contacto="555333444"
        )
        db.add(cliente1)
        db.add(cliente2)
        db.commit()

        # --- Crear Pedidos ---
        # Refrescar los objetos para obtener sus IDs asignados por la BD
        db.refresh(repartidor1)
        db.refresh(repartidor2)
        db.refresh(cliente1)
        db.refresh(cliente2)

        vehiculo1 = Vehiculo(
            placa="ABC-123",
            tipo="motocicleta",
            marca="Honda",
            modelo="CGL 125",
            color="Rojo",
            repartidor_id=repartidor1.repartidor_id # Asignado a Juan Pérez
        )
        vehiculo2 = Vehiculo(
            placa="XYZ-789",
            tipo="motocicleta",
            marca="Suzuki",
            modelo="GN 125",
            color="Negro",
            repartidor_id=repartidor2.repartidor_id # Asignado a Ana Gómez
        )
        db.add(vehiculo1)
        db.add(vehiculo2)
        
        # Hacemos commit aquí para guardar los vehículos antes de crear los pedidos
        db.commit()
        
        # Pedido 1: Listo para que la cocina o el bot inicien la búsqueda
        pedido1 = Pedido(
            cliente_id=cliente1.cliente_id,
            descripcion_pedido="1x Pizza familiar, 1x Refresco 2L",
            direccion_entrega="Calle Falsa 123, Ciudad Ejemplo",
            monto_total=Decimal("25.50"),
            estado_pedido="LISTO_PARA_RECOGER"
        )
        
        # Pedido 2: Ya en proceso (para probar el historial)
        pedido2 = Pedido(
            cliente_id=cliente2.cliente_id,
            repartidor_id=repartidor1.repartidor_id, # Asignado a Juan
            descripcion_pedido="2x Hamburguesas con queso, 2x Papas fritas",
            direccion_entrega="Avenida Siempreviva 742",
            monto_total=Decimal("18.75"),
            estado_pedido="EN_CAMINO_AL_CLIENTE",
            instrucciones_entrega="Dejar en la puerta."
        )

        # Pedido 3: Recién creado
        pedido3 = Pedido(
            cliente_id=cliente1.cliente_id,
            descripcion_pedido="1x Ensalada César",
            direccion_entrega="Calle Falsa 123, Ciudad Ejemplo",
            monto_total=Decimal("9.00"),
            estado_pedido="PENDIENTE_CONFIRMACION"
        )

        db.add(pedido1)
        db.add(pedido2)
        db.add(pedido3)
        db.commit()

        print("¡Datos de ejemplo insertados correctamente!")

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
    print("Proceso de seeding finalizado.")