"""DAO cho bang payment."""
from __future__ import annotations

from typing import Any

from ..db import execute, fetch_all, fetch_one


def create(invoice_id: int, amount: float, method: str, created_by: int | None, note: str | None) -> int:
    return execute(
        "INSERT INTO payment (invoice_id, amount, method, created_by, note) VALUES (%s,%s,%s,%s,%s)",
        (invoice_id, amount, method, created_by, note),
    )


def sum_paid(invoice_id: int) -> float:
    row = fetch_one("SELECT COALESCE(SUM(amount),0) AS s FROM payment WHERE invoice_id=%s", (invoice_id,))
    return float(row["s"]) if row else 0.0


def list_by_invoice(invoice_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        "SELECT id, amount, method, paid_at, note FROM payment WHERE invoice_id=%s ORDER BY paid_at DESC, id DESC",
        (invoice_id,),
    )

