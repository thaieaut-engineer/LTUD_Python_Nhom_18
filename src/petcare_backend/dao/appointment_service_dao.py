"""DAO cho bang appointment_service (1 appointment co the co nhieu dich vu + nhieu pet)."""
from __future__ import annotations

from typing import Any

from ..db import execute, fetch_all


def insert(
    appointment_id: int,
    service_id: int,
    quantity: int,
    unit_price: float,
    pet_id: int | None = None,
) -> int:
    """Them 1 dong dich vu vao appointment. Moi lan goi tao 1 row moi."""
    return execute(
        "INSERT INTO appointment_service (appointment_id, service_id, pet_id, quantity, unit_price) "
        "VALUES (%s,%s,%s,%s,%s)",
        (appointment_id, service_id, pet_id, quantity, unit_price),
    )


# Backward compat alias
upsert = insert


def list_by_appointment(appointment_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            aps.id,
            aps.appointment_id,
            aps.service_id,
            s.name AS service_name,
            aps.pet_id,
            p.name AS pet_name,
            aps.quantity,
            aps.unit_price
        FROM appointment_service aps
        JOIN service s ON s.id = aps.service_id
        LEFT JOIN pet p ON p.id = aps.pet_id
        WHERE aps.appointment_id = %s
        ORDER BY aps.id
        """,
        (appointment_id,),
    )
