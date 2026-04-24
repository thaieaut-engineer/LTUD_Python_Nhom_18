"""DAO cho bang user."""
from __future__ import annotations

from typing import Any

from ..db import execute, fetch_all, fetch_one
from ..models import User


_SELECT_BASE = """
SELECT u.id, u.role_id, r.name AS role_name, u.username,
       u.password_hash, u.full_name, u.phone, u.is_active
FROM   user u
JOIN   role r ON r.id = u.role_id
"""


def _row_to_user(row: dict[str, Any]) -> User:
    return User(
        id=row["id"],
        role_id=row["role_id"],
        role_name=row["role_name"],
        username=row["username"],
        full_name=row["full_name"],
        phone=row.get("phone"),
        is_active=bool(row["is_active"]),
    )


def find_by_username(username: str) -> dict[str, Any] | None:
    """Tra ve nguyen ban dict (con co password_hash) - dung khi login."""
    return fetch_one(_SELECT_BASE + " WHERE u.username = %s LIMIT 1", (username,))


def get_by_id(user_id: int) -> User | None:
    row = fetch_one(_SELECT_BASE + " WHERE u.id = %s LIMIT 1", (user_id,))
    return _row_to_user(row) if row else None


def get_password_hash(user_id: int) -> str | None:
    row = fetch_one("SELECT password_hash FROM user WHERE id = %s", (user_id,))
    return row["password_hash"] if row else None


def update_password(user_id: int, password_hash: str) -> None:
    execute(
        "UPDATE user SET password_hash = %s WHERE id = %s",
        (password_hash, user_id),
    )


def list_all(active_only: bool = False) -> list[User]:
    sql = _SELECT_BASE + (" WHERE u.is_active = 1" if active_only else "") + " ORDER BY u.id"
    return [_row_to_user(r) for r in fetch_all(sql)]
