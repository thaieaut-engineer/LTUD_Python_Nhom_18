"""DAO cho bang customer."""
from __future__ import annotations

from typing import Any, Sequence

from ..db import execute, fetch_all, fetch_one
from ..models import Customer


def _row_to_customer(row: dict[str, Any]) -> Customer:
    return Customer(
        id=row["id"],
        full_name=row["full_name"],
        phone=row["phone"],
        address=row.get("address"),
        email=row.get("email"),
        created_at=row.get("created_at"),
    )


def list_all(query: str | None = None) -> list[Customer]:
    sql = "SELECT id, full_name, phone, address, email, created_at FROM customer"
    params: Sequence[Any] = ()
    if query:
        q = f"%{query.strip()}%"
        sql += " WHERE full_name LIKE %s OR phone LIKE %s"
        params = (q, q)
    sql += " ORDER BY id DESC"
    return [_row_to_customer(r) for r in fetch_all(sql, params)]


def get_by_id(customer_id: int) -> Customer | None:
    row = fetch_one(
        "SELECT id, full_name, phone, address, email, created_at FROM customer WHERE id=%s",
        (customer_id,),
    )
    return _row_to_customer(row) if row else None


def create(full_name: str, phone: str, address: str | None, email: str | None) -> int:
    return execute(
        "INSERT INTO customer (full_name, phone, address, email) VALUES (%s,%s,%s,%s)",
        (full_name, phone, address, email),
    )


def update(customer_id: int, full_name: str, phone: str, address: str | None, email: str | None) -> None:
    execute(
        "UPDATE customer SET full_name=%s, phone=%s, address=%s, email=%s WHERE id=%s",
        (full_name, phone, address, email, customer_id),
    )


def delete(customer_id: int) -> None:
    execute("DELETE FROM customer WHERE id=%s", (customer_id,))

