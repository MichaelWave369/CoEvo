import os

class Settings:
    APP_NAME: str = "CoEvo"
    DB_URL: str = os.getenv("COEVO_DB_URL", "sqlite:///./coevo.db")
    JWT_SECRET: str = os.getenv("COEVO_JWT_SECRET", "dev-only-change-me")
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("COEVO_JWT_EXPIRE_MINUTES", "10080"))  # 7 days
    CORS_ORIGINS: list[str] = [
        o.strip() for o in os.getenv("COEVO_CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    ]
    UPLOAD_DIR: str = os.getenv("COEVO_UPLOAD_DIR", "./storage/uploads")

    # Agents
    AGENT_ENABLED: bool = os.getenv("COEVO_AGENT_ENABLED", "0") == "1"
    DEFAULT_AGENT_MODEL: str = os.getenv("COEVO_DEFAULT_AGENT_MODEL", "claude-3-5-haiku-latest")

    # Admin seed
    SEED_ADMIN: bool = os.getenv("COEVO_SEED_ADMIN", "0") == "1"
    ADMIN_PASSWORD: str = os.getenv("COEVO_ADMIN_PASSWORD", "admin")

    # Node signing key
    NODE_KEY_PATH: str = os.getenv("COEVO_NODE_KEY_PATH", "./storage/node_key.pem")

settings = Settings()
