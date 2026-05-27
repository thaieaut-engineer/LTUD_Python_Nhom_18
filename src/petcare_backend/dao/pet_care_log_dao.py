"""DAO cho bang pet_care_log."""
from __future__ import annotations

from typing import Any

from ..db import execute, fetch_all


def create(
    stay_id: int,
    employee_id: int | None,
    log_type: str,
    content: str,
    *,
    product_id: int | None = None,
    service_id: int | None = None,
    quantity: int | None = 1,
) -> int:
    return execute(
        """
        INSERT INTO pet_care_log
        (stay_id, employee_id, log_type, content, product_id, service_id, quantity)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (stay_id, employee_id, log_type, content, product_id, service_id, quantity),
    )


_LOG_SELECT = """
        SELECT l.*, u.full_name AS employee_name,
               pr.name AS product_name, pr.category AS product_category,
               sv.name AS service_name
        FROM pet_care_log l
        LEFT JOIN user u ON u.id = l.employee_id
        LEFT JOIN product pr ON pr.id = l.product_id
        LEFT JOIN service sv ON sv.id = l.service_id
"""


def list_by_stay(stay_id: int, limit: int = 200) -> list[dict[str, Any]]:
    return fetch_all(
        _LOG_SELECT
        + """
        WHERE l.stay_id=%s
        ORDER BY l.created_at DESC, l.id DESC
        LIMIT %s
        """,
        (stay_id, int(limit)),
    )


def list_by_pet(pet_id: int, limit: int = 200) -> list[dict[str, Any]]:
    return fetch_all(
        _LOG_SELECT
        + """
        JOIN pet_stay st ON st.id = l.stay_id
        WHERE st.pet_id=%s
        ORDER BY l.created_at DESC, l.id DESC
        LIMIT %s
        """,
        (pet_id, int(limit)),
    )
