"""DAO cho bang invoice."""
from __future__ import annotations

from typing import Any

from ..db import execute, fetch_all, fetch_one


def create(
    appointment_id: int,
    invoice_no: str,
    subtotal_amount: float,
    discount_amount: float,
    tax_amount: float,
    total_amount: float,
    payment_status: str,
    created_by: int | None,
    note: str | None,
) -> int:
    return execute(
        "INSERT INTO invoice (appointment_id, invoice_no, subtotal_amount, discount_amount, tax_amount, total_amount, "
        "payment_status, created_by, note) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            appointment_id,
            invoice_no,
            subtotal_amount,
            discount_amount,
            tax_amount,
            total_amount,
            payment_status,
            created_by,
            note,
        ),
    )


def get_by_appointment(appointment_id: int) -> dict[str, Any] | None:
    return fetch_one("SELECT * FROM invoice WHERE appointment_id=%s", (appointment_id,))


def get_by_id(invoice_id: int) -> dict[str, Any] | None:
    return fetch_one("SELECT * FROM invoice WHERE id=%s", (invoice_id,))


def update_totals(invoice_id: int, subtotal: float, discount: float, tax: float, total: float) -> None:
    execute(
        "UPDATE invoice SET subtotal_amount=%s, discount_amount=%s, tax_amount=%s, total_amount=%s WHERE id=%s",
        (subtotal, discount, tax, total, invoice_id),
    )


def update_payment_status(invoice_id: int, status: str) -> None:
    execute("UPDATE invoice SET payment_status=%s WHERE id=%s", (status, invoice_id))


def list_recent(limit: int = 100) -> list[dict[str, Any]]:
    sql = """
    SELECT
      i.id AS invoice_id, i.invoice_no, i.issued_at, i.total_amount, i.payment_status,
      a.id AS appointment_id, a.scheduled_at,
      c.full_name AS customer_name,
      COALESCE(
          (
              SELECT GROUP_CONCAT(DISTINCT p_in.name ORDER BY p_in.name SEPARATOR ', ')
              FROM appointment_service aps
              LEFT JOIN pet p_in ON p_in.id = aps.pet_id
              WHERE aps.appointment_id = a.id AND aps.pet_id IS NOT NULL
          ),
          p_single.name
      ) AS pet_name
    FROM invoice i
    JOIN appointment a ON a.id = i.appointment_id
    JOIN customer c ON c.id = a.customer_id
    LEFT JOIN pet p_single ON p_single.id = a.pet_id
    ORDER BY i.issued_at DESC, i.id DESC
    LIMIT %s
    """
    return fetch_all(sql, (int(limit),))

