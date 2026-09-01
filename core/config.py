import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

PACKAGE_DIR = Path(__file__).resolve().parent.parent
env_path = PACKAGE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# Core Security
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    import warnings
    warnings.warn("SECRET_KEY not set! Using insecure default for development only.")
    SECRET_KEY = "dev-secret-change-me-in-production"
ALGORITHM = "RS256"  # Use RS256 for asymmetric signing
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived access tokens
REFRESH_TOKEN_EXPIRE_DAYS = 7
REFRESH_TOKEN_EXPIRE_MINUTES = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60

# RSA Key Configuration
RSA_PRIVATE_KEY_PATH = os.getenv("RSA_PRIVATE_KEY_PATH", str(PACKAGE_DIR / "keys" / "private_key.pem"))
RSA_PUBLIC_KEY_PATH = os.getenv("RSA_PUBLIC_KEY_PATH", str(PACKAGE_DIR / "keys" / "public_key.pem"))
RSA_KEY_SIZE = int(os.getenv("RSA_KEY_SIZE", "2048"))

# Database Configuration
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "medverify")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    if DB_HOST and DB_PASSWORD:
        SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{PACKAGE_DIR / 'medverify.db'}"

IS_POSTGRESQL = SQLALCHEMY_DATABASE_URL.startswith("postgresql") or SQLALCHEMY_DATABASE_URL.startswith("postgresql+")

# Async engine
async_engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}
if IS_POSTGRESQL:
    async_engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
    })
else:
    async_engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
    })

async_engine: AsyncEngine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    **async_engine_kwargs,
)
AsyncSessionLocal = async_sessionmaker(
    async_engine, autocommit=False, autoflush=False, expire_on_commit=False
)

# Sync engine for Alembic
SYNC_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")
sync_engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}
if IS_POSTGRESQL:
    sync_engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
    })
else:
    sync_engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
    })

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    **sync_engine_kwargs,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

# Email Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@medverify.app")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "MedVerify")

# Frontend URL for email links
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Rate Limiting
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "10/minute")
RATE_LIMIT_VERIFY = os.getenv("RATE_LIMIT_VERIFY", "100/minute")

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# Feature Flags
ENABLE_2FA = os.getenv("ENABLE_2FA", "true").lower() == "true"
ENABLE_EMAIL_VERIFICATION = os.getenv("ENABLE_EMAIL_VERIFICATION", "true").lower() == "true"
ENABLE_PASSWORD_RESET = os.getenv("ENABLE_PASSWORD_RESET", "true").lower() == "true"
