"""DAO cho bang invoice."""
from __future__ import annotations

from typing import Any

from ..db import execute, fetch_all, fetch_one


def create(
    appointment_id: int | None,
    invoice_no: str,
    subtotal_amount: float,
    discount_amount: float,
    tax_amount: float,
    total_amount: float,
    payment_status: str,
    created_by: int | None,
    note: str | None,
    customer_id: int | None = None,
    invoice_type: str = "SERVICE",
) -> int:
    return execute(
        "INSERT INTO invoice (appointment_id, customer_id, invoice_type, invoice_no, "
        "subtotal_amount, discount_amount, tax_amount, total_amount, payment_status, created_by, note) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            appointment_id,
            customer_id,
            invoice_type,
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


def list_recent(
    limit: int = 100,
    *,
    created_by: int | None = None,
    invoice_type: str | None = None,
) -> list[dict[str, Any]]:
    """Liet ke hoa don gan day, ho tro hoa don ban le (RETAIL) lan dich vu (SERVICE).

    - created_by: chi liet ke hoa don do user nay tao (None = tat ca).
    - invoice_type: 'SERVICE' | 'RETAIL' | None.
    """
    where: list[str] = []
    params: list[Any] = []
    if created_by is not None:
        where.append("i.created_by = %s")
        params.append(int(created_by))
    if invoice_type:
        where.append("i.invoice_type = %s")
        params.append(invoice_type)
    where_clause = (" WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
    SELECT
      i.id AS invoice_id, i.invoice_no, i.issued_at, i.total_amount, i.payment_status,
      i.invoice_type,
      a.id AS appointment_id, a.scheduled_at,
      COALESCE(c_inv.full_name, c_appt.full_name) AS customer_name,
      COALESCE(c_inv.phone, c_appt.phone) AS customer_phone,
      COALESCE(
          (
              SELECT GROUP_CONCAT(DISTINCT p_in.name ORDER BY p_in.name SEPARATOR ', ')
              FROM appointment_service aps
              LEFT JOIN pet p_in ON p_in.id = aps.pet_id
              WHERE aps.appointment_id = a.id AND aps.pet_id IS NOT NULL
          ),
          p_single.name
      ) AS pet_name,
      i.created_by AS created_by_id,
      u.full_name AS created_by_name,
      u.username  AS created_by_username
    FROM invoice i
    LEFT JOIN appointment a ON a.id = i.appointment_id
    LEFT JOIN customer c_inv  ON c_inv.id  = i.customer_id
    LEFT JOIN customer c_appt ON c_appt.id = a.customer_id
    LEFT JOIN pet p_single    ON p_single.id = a.pet_id
    LEFT JOIN user u          ON u.id = i.created_by
    {where_clause}
    ORDER BY i.issued_at DESC, i.id DESC
    LIMIT %s
    """
    params.append(int(limit))
    return fetch_all(sql, tuple(params))


def list_by_customer(customer_id: int, limit: int = 100) -> list[dict[str, Any]]:
    """Hoa don cua 1 khach hang (qua ca duong customer_id va appointment.customer_id)."""
    sql = """
    SELECT
      i.id AS invoice_id, i.invoice_no, i.issued_at, i.total_amount, i.payment_status,
      i.invoice_type,
      a.id AS appointment_id, a.scheduled_at,
      COALESCE(c_inv.full_name, c_appt.full_name) AS customer_name,
      u.full_name AS created_by_name
    FROM invoice i
    LEFT JOIN appointment a ON a.id = i.appointment_id
    LEFT JOIN customer c_inv  ON c_inv.id  = i.customer_id
    LEFT JOIN customer c_appt ON c_appt.id = a.customer_id
    LEFT JOIN user u          ON u.id = i.created_by
    WHERE i.customer_id = %s OR a.customer_id = %s
    ORDER BY i.issued_at DESC, i.id DESC
    LIMIT %s
    """
    return fetch_all(sql, (int(customer_id), int(customer_id), int(limit)))

