"""
Email Sail Agent — Configuration
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8090
    APP_DEBUG: bool = False
    SECRET_KEY: str = "change-this-to-a-random-secret-key"

    # Google OAuth2
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8090/auth/callback"

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Gumroad
    GUMROAD_API_KEY: str = ""

    # Database
    DATABASE_PATH: str = "data/email_sail.db"

    # PoA Engine
    POA_ENGINE_URL: str = "http://localhost:8000"

    # MIO Observer
    MIO_OBSERVER_URL: str = "http://localhost:8787"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
