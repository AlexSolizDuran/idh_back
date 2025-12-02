from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    '''
    Configuración de la aplicación cargada desde variables de entorno.
    '''
    """
    DATABASE_URL: str = "postgresql://neondb_owner:npg_KoxG7FCzI8sP@ep-tiny-butterfly-afvunra9-pooler.c-2.us-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    JWT_SECRET_KEY: str = "clave_secreta_super_segura_demo_123"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"

# Se crea una instancia única que se importará en otros módulos
settings = Settings()