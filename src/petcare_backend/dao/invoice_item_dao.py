"""DAO cho bang invoice_item."""
from __future__ import annotations

from typing import Any

from ..db import execute, fetch_all, fetch_one


def create(
    invoice_id: int,
    service_id: int | None = None,
    quantity: int = 1,
    unit_price: float = 0.0,
    pet_id: int | None = None,
    product_id: int | None = None,
    item_type: str | None = None,
) -> int:
    """Them 1 dong vao hoa don.

    - Voi dich vu: truyen service_id (item_type = 'SERVICE').
    - Voi san pham: truyen product_id (item_type = 'PRODUCT').
    """
    if item_type is None:
        item_type = "PRODUCT" if product_id is not None else "SERVICE"
    return execute(
        "INSERT INTO invoice_item "
        "(invoice_id, service_id, product_id, item_type, pet_id, quantity, unit_price) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (
            invoice_id,
            service_id,
            product_id,
            item_type,
            pet_id,
            int(quantity),
            float(unit_price),
        ),
    )


def list_by_invoice(invoice_id: int) -> list[dict[str, Any]]:
    sql = """
    SELECT
      ii.id,
      ii.invoice_id,
      ii.item_type,
      ii.service_id,
      ii.product_id,
      COALESCE(s.name, pr.name) AS item_name,
      s.name AS service_name,
      pr.name AS product_name,
      pr.category AS product_category,
      ii.pet_id,
      p.name AS pet_name,
      ii.quantity,
      ii.unit_price,
      ii.line_total
    FROM invoice_item ii
    LEFT JOIN service s   ON s.id = ii.service_id
    LEFT JOIN product pr  ON pr.id = ii.product_id
    LEFT JOIN pet p       ON p.id = ii.pet_id
    WHERE ii.invoice_id=%s
    ORDER BY ii.item_type DESC, ii.id
    """
    return fetch_all(sql, (invoice_id,))


def get_by_id(item_id: int) -> dict[str, Any] | None:
    return fetch_one(
        "SELECT id, invoice_id, item_type, service_id, product_id, pet_id, quantity, unit_price "
        "FROM invoice_item WHERE id=%s",
        (item_id,),
    )


def delete(item_id: int) -> None:
    execute("DELETE FROM invoice_item WHERE id=%s", (item_id,))


def update_quantity(item_id: int, quantity: int) -> None:
    execute("UPDATE invoice_item SET quantity=%s WHERE id=%s", (int(quantity), item_id))
