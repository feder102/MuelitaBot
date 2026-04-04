"""Application configuration and settings."""
import base64
import json
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram Configuration
    telegram_bot_token: str
    telegram_bot_webhook_secret: str

    # Database Configuration
    database_url: str
    database_name: str
    postgres_user: str
    postgres_password: str

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"

    # Logging
    log_level: str = "INFO"

    # Google Calendar Configuration (Feature 002)
    google_calendar_credentials_b64: str = ""
    google_calendar_id: str = ""
    clinic_timezone: str = "America/Argentina/Buenos_Aires"

    # Appointment Configuration
    appointment_slots_start_time: str = "08:00"
    appointment_slots_end_time: str = "13:00"
    appointment_reason_max_length: int = 150

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.api_env.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.api_env.lower() == "production"

    @property
    def google_calendar_credentials(self) -> dict:
        """Decode base64-encoded service account credentials.

        Returns:
            Dictionary with Google service account info

        Raises:
            ValueError: If credentials not set or invalid base64
        """
        if not self.google_calendar_credentials_b64:
            raise ValueError("GOOGLE_CALENDAR_CREDENTIALS_B64 environment variable not set")

        try:
            creds_json = base64.b64decode(self.google_calendar_credentials_b64).decode()
            return json.loads(creds_json)
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid Google Calendar credentials: {e}")


# Create global settings instance
settings = Settings()
