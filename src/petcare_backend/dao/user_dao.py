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


def list_employees(active_only: bool = True) -> list[User]:
    """Liet ke nhan vien (role = EMPLOYEE)."""
    sql = _SELECT_BASE + " WHERE r.name = 'EMPLOYEE'"
    if active_only:
        sql += " AND u.is_active = 1"
    sql += " ORDER BY u.full_name"
    return [_row_to_user(r) for r in fetch_all(sql)]


# -------- Admin CRUD helpers --------


def list_all_with_role(
    active_only: bool = False,
    query: str | None = None,
    role_name: str | None = None,
) -> list[dict[str, Any]]:
    """Liet ke user kem role, ho tro tim kiem va loc theo role.

    - query   : khop ten / username / phone (LIKE).
    - role_name: ADMIN | EMPLOYEE (None => khong loc).
    """
    sql = _SELECT_BASE
    where: list[str] = []
    params: list[Any] = []
    if active_only:
        where.append("u.is_active = 1")
    if role_name:
        where.append("r.name = %s")
        params.append(role_name.upper())
    q = (query or "").strip()
    if q:
        like = f"%{q}%"
        where.append(
            "(u.full_name LIKE %s OR u.username LIKE %s OR u.phone LIKE %s)"
        )
        params.extend([like, like, like])
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY u.id DESC"
    return fetch_all(sql, tuple(params))


def create(role_id: int, username: str, password_hash: str, full_name: str, phone: str | None) -> int:
    return execute(
        "INSERT INTO user (role_id, username, password_hash, full_name, phone, is_active) "
        "VALUES (%s,%s,%s,%s,%s,1)",
        (role_id, username, password_hash, full_name, phone),
    )


def update_profile(user_id: int, full_name: str, phone: str | None) -> None:
    execute(
        "UPDATE user SET full_name=%s, phone=%s WHERE id=%s",
        (full_name, phone, user_id),
    )


def update_role(user_id: int, role_id: int) -> None:
    execute("UPDATE user SET role_id=%s WHERE id=%s", (role_id, user_id))


def set_active(user_id: int, is_active: bool) -> None:
    execute("UPDATE user SET is_active=%s WHERE id=%s", (1 if is_active else 0, user_id))
