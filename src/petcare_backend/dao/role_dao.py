"""DAO cho bang role."""
from __future__ import annotations

from typing import Any

from ..db import fetch_all, fetch_one


def list_all() -> list[dict[str, Any]]:
    return fetch_all("SELECT id, name, description FROM role ORDER BY id")


def get_by_name(name: str) -> dict[str, Any] | None:
    return fetch_one("SELECT id, name, description FROM role WHERE name=%s LIMIT 1", (name,))

