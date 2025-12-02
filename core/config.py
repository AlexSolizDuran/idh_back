from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    '''
    Configuración de la aplicación cargada desde variables de entorno.
    '''
    """
    DATABASE_URL: str = "sqlite:///./delivery.db"
    JWT_SECRET_KEY: str = "clave_secreta_super_segura_demo_123"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"

# Se crea una instancia única que se importará en otros módulos
settings = Settings()