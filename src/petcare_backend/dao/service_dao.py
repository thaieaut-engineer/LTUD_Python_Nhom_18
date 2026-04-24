"""DAO cho bang service."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from ..db import execute, fetch_all, fetch_one
from ..models import Service


def _row_to_service(row: dict[str, Any]) -> Service:
    return Service(
        id=row["id"],
        name=row["name"],
        price=Decimal(row["price"]),
        description=row.get("description"),
        duration_min=row.get("duration_min"),
        is_active=bool(row["is_active"]),
    )


def list_all(active_only: bool = True) -> list[Service]:
    sql = "SELECT id, name, price, description, duration_min, is_active FROM service"
    params: Sequence[Any] = ()
    if active_only:
        sql += " WHERE is_active=1"
    sql += " ORDER BY id DESC"
    return [_row_to_service(r) for r in fetch_all(sql, params)]


def get_by_id(service_id: int) -> Service | None:
    row = fetch_one(
        "SELECT id, name, price, description, duration_min, is_active FROM service WHERE id=%s",
        (service_id,),
    )
    return _row_to_service(row) if row else None


def create(name: str, price: Decimal, description: str | None, duration_min: int | None, is_active: bool) -> int:
    return execute(
        "INSERT INTO service (name, price, description, duration_min, is_active) VALUES (%s,%s,%s,%s,%s)",
        (name, str(price), description, duration_min, 1 if is_active else 0),
    )


def update(
    service_id: int,
    name: str,
    price: Decimal,
    description: str | None,
    duration_min: int | None,
    is_active: bool,
) -> None:
    execute(
        "UPDATE service SET name=%s, price=%s, description=%s, duration_min=%s, is_active=%s WHERE id=%s",
        (name, str(price), description, duration_min, 1 if is_active else 0, service_id),
    )


def delete(service_id: int) -> None:
    """Xoa mem: chuyen is_active=0 de tranh mat du lieu lich su."""
    execute("UPDATE service SET is_active=0 WHERE id=%s", (service_id,))

