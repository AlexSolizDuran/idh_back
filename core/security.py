from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

from .config import settings

# Contexto para el hash de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TokenData(BaseModel):
    """Modelo Pydantic para los datos contenidos en el JWT."""
    repartidor_id: Optional[int] = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña plana contra su hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera un hash bcrypt para una contraseña."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un nuevo token JWT.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decodifica un token JWT y valida su contenido.
    Retorna los datos del token o None si es inválido.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        repartidor_id: Optional[int] = payload.get("repartidor_id")
        
        if repartidor_id is None:
            return None
            
        return TokenData(repartidor_id=repartidor_id)
    except JWTError:
        return None