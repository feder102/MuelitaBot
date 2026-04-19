"""Application configuration and settings."""
import base64
import json
from pydantic import field_validator
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

    # Admin Dashboard Configuration (Feature 005)
    admin_jwt_secret: str
    admin_jwt_expire_minutes: int = 60
    admin_dashboard_origins: str = ""

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

    @field_validator("admin_jwt_secret")
    @classmethod
    def validate_admin_jwt_secret(cls, value: str) -> str:
        """Require a strong JWT signing secret."""
        if len(value) < 32:
            raise ValueError("ADMIN_JWT_SECRET must be at least 32 characters long")
        return value

    @property
    def admin_dashboard_origins_list(self) -> list[str]:
        """Parse admin dashboard origins from a comma-separated string."""
        return [
            origin.strip()
            for origin in self.admin_dashboard_origins.split(",")
            if origin.strip()
        ]

    @property
    def cors_allowed_origins(self) -> list[str]:
        """Return the configured CORS allowlist."""
        if self.is_development:
            return ["*"]

        return [
            "https://api.telegram.org",
            *self.admin_dashboard_origins_list,
        ]

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
