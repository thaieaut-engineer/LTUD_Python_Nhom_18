"""DAO cho bang invoice_item."""
from __future__ import annotations

from typing import Any

from ..db import execute, fetch_all


def create(
    invoice_id: int,
    service_id: int,
    quantity: int,
    unit_price: float,
    pet_id: int | None = None,
) -> int:
    return execute(
        "INSERT INTO invoice_item (invoice_id, service_id, pet_id, quantity, unit_price) "
        "VALUES (%s,%s,%s,%s,%s)",
        (invoice_id, service_id, pet_id, quantity, unit_price),
    )


def list_by_invoice(invoice_id: int) -> list[dict[str, Any]]:
    sql = """
    SELECT
      ii.id,
      ii.service_id,
      s.name AS service_name,
      ii.pet_id,
      p.name AS pet_name,
      ii.quantity,
      ii.unit_price,
      ii.line_total
    FROM invoice_item ii
    JOIN service s ON s.id = ii.service_id
    LEFT JOIN pet p ON p.id = ii.pet_id
    WHERE ii.invoice_id=%s
    ORDER BY ii.id
    """
    return fetch_all(sql, (invoice_id,))
