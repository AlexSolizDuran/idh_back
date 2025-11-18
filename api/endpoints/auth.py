from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from db import crud, schemas, database
from core import security

router = APIRouter()

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(db: Session = Depends(database.get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint de login. Usa el formato OAuth2PasswordRequestForm
    (requiere 'username' y 'password' en un form-data).
    
    Nota: 'username' en este caso es el email del repartidor.
    """
    repartidor = crud.get_repartidor_by_email(db, email=form_data.username)
    
    if not repartidor or not security.verify_password(form_data.password, repartidor.hash_contrasena):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear el token JWT
    access_token_expires = timedelta(minutes=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"repartidor_id": repartidor.repartidor_id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# (Opcional) Endpoint de registro para la demo
@router.post("/register", response_model=schemas.Repartidor, status_code=status.HTTP_201_CREATED)
def register_repartidor(repartidor: schemas.RepartidorCreate, db: Session = Depends(database.get_db)):
    """
    Endpoint para crear un nuevo repartidor (para facilitar la demo).
    """
    db_repartidor = crud.get_repartidor_by_email(db, email=repartidor.email)
    if db_repartidor:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    return crud.create_repartidor(db=db, repartidor=repartidor)