"""Doc cau hinh tu file .env (hoac bien moi truong)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore


_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _ROOT / ".env"

if load_dotenv is not None and _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "DBConfig":
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "petcare_db"),
        )


DB_CONFIG = DBConfig.from_env()
APP_ENV = os.getenv("APP_ENV", "dev")
