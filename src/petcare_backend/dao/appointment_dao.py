"""DAO cho bang appointment."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..db import execute, fetch_all, fetch_one


def create(
    customer_id: int,
    pet_id: int | None,
    employee_id: int | None,
    scheduled_at: datetime,
    status: str,
    note: str | None,
) -> int:
    return execute(
        "INSERT INTO appointment (customer_id, pet_id, employee_id, scheduled_at, status, note) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (customer_id, pet_id, employee_id, scheduled_at, status, note),
    )


def update_status(appointment_id: int, status: str) -> None:
    execute("UPDATE appointment SET status=%s WHERE id=%s", (status, appointment_id))


def update_note(appointment_id: int, note: str | None) -> None:
    execute("UPDATE appointment SET note=%s WHERE id=%s", (note, appointment_id))


def get_by_id(appointment_id: int) -> dict[str, Any] | None:
    return fetch_one(
        "SELECT id, customer_id, pet_id, employee_id, scheduled_at, status, note, created_at "
        "FROM appointment WHERE id=%s",
        (appointment_id,),
    )


# SQL dung chung: gop ten thu cung + dich vu cua 1 appointment thanh chuoi phan cach ", "
_SUMMARY_SQL = """
SELECT
    a.id                                        AS appointment_id,
    a.scheduled_at,
    a.status,
    a.note,
    c.id                                        AS customer_id,
    c.full_name                                 AS customer_name,
    c.phone                                     AS customer_phone,
    c.address                                   AS customer_address,
    -- Ten thu cung: uu tien lay tu appointment_service.pet_id, fallback ve a.pet_id
    COALESCE(
        (
            SELECT GROUP_CONCAT(DISTINCT pet_in.name ORDER BY pet_in.name SEPARATOR ', ')
            FROM appointment_service aps
            LEFT JOIN pet pet_in ON pet_in.id = aps.pet_id
            WHERE aps.appointment_id = a.id AND aps.pet_id IS NOT NULL
        ),
        pet_single.name
    )                                           AS pet_name,
    a.pet_id                                    AS pet_id,
    pet_single.species                          AS pet_species,
    pet_single.breed                            AS pet_breed,
    -- Dich vu: gop ten + SL
    (
        SELECT GROUP_CONCAT(
                   CONCAT(s.name, IF(aps2.quantity > 1, CONCAT(' x', aps2.quantity), ''))
                   ORDER BY aps2.id SEPARATOR ', '
               )
        FROM appointment_service aps2
        JOIN service s ON s.id = aps2.service_id
        WHERE aps2.appointment_id = a.id
    )                                           AS service_name,
    (
        SELECT SUM(aps3.quantity * aps3.unit_price)
        FROM appointment_service aps3
        WHERE aps3.appointment_id = a.id
    )                                           AS total_amount,
    (
        SELECT COUNT(*) FROM appointment_service aps4 WHERE aps4.appointment_id = a.id
    )                                           AS service_count
FROM appointment a
JOIN customer c       ON c.id = a.customer_id
LEFT JOIN pet pet_single ON pet_single.id = a.pet_id
{where_clause}
ORDER BY a.scheduled_at DESC, a.id DESC
LIMIT %s
"""


def list_recent(limit: int = 100) -> list[dict[str, Any]]:
    sql = _SUMMARY_SQL.format(where_clause="")
    return fetch_all(sql, (int(limit),))


def list_by_customer(customer_id: int, limit: int = 200) -> list[dict[str, Any]]:
    sql = _SUMMARY_SQL.format(where_clause="WHERE a.customer_id = %s")
    return fetch_all(sql, (customer_id, int(limit)))
