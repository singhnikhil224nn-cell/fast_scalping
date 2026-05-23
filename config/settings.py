from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Core API Configurations
    BINANCE_API_KEY: str = Field(default="", validation_alias="BINANCE_API_KEY")
    BINANCE_SECRET_KEY: str = Field(default="", validation_alias="BINANCE_SECRET_KEY")
    ENVIRONMENT: str = Field(default="development", validation_alias="ENVIRONMENT")
    
    # This magic line allows your .env file to contain extra database/telegram configurations 
    # without triggering structural validation strictness crashes
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Strictly instructs pydantic to ignore any extra keys
    )

settings = Settings()
