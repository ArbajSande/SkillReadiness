from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENV: str = "development"
    MONGODB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "skill_readiness_db"
    SECRET_KEY: str = "skillreadiness_production_super_secret_key_2026_jwt_token_sign"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB strict limit
    RATE_LIMIT_AUTH_PER_MINUTE: int = 20

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def validate_production_security(self) -> None:
        """
        Enforce strict cryptographic secret standards in production environments.
        Prevents deployment with known default or weak development credentials.
        """
        if self.ENV.lower() in ("production", "prod"):
            insecure_defaults = [
                "skillreadiness_production_super_secret_key_2026_jwt_token_sign",
                "secret",
                "changeme",
                "development",
                "password"
            ]
            if self.SECRET_KEY in insecure_defaults or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: "
                    "A secure, unique SECRET_KEY of at least 32 characters is required when ENV=production. "
                    "Do not use default or placeholder secret keys in production."
                )

settings = Settings()
