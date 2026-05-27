"""DAO cho bang pet_stay (luu tru / cham soc theo ngay)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..db import execute, fetch_all, fetch_one


def get_by_id(stay_id: int) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT s.*, p.name AS pet_name, p.species, p.breed, p.age, p.gender, p.health_note,
               c.full_name AS customer_name, c.phone AS customer_phone,
               u.full_name AS employee_name
        FROM pet_stay s
        JOIN pet p ON p.id = s.pet_id
        JOIN customer c ON c.id = s.customer_id
        LEFT JOIN user u ON u.id = s.employee_id
        WHERE s.id=%s
        """,
        (stay_id,),
    )


def get_latest_by_pet(pet_id: int) -> dict[str, Any] | None:
    """Đợt gần nhất (mọi trạng thái) — dùng xem HĐ sau khi khách đã nhận thú."""
    return fetch_one(
        """
        SELECT s.*, p.name AS pet_name, c.full_name AS customer_name,
               u.full_name AS employee_name
        FROM pet_stay s
        JOIN pet p ON p.id = s.pet_id
        JOIN customer c ON c.id = s.customer_id
        LEFT JOIN user u ON u.id = s.employee_id
        WHERE s.pet_id=%s
        ORDER BY s.id DESC LIMIT 1
        """,
        (pet_id,),
    )


def get_active_by_pet(pet_id: int) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT s.*, p.name AS pet_name, c.full_name AS customer_name,
               u.full_name AS employee_name
        FROM pet_stay s
        JOIN pet p ON p.id = s.pet_id
        JOIN customer c ON c.id = s.customer_id
        LEFT JOIN user u ON u.id = s.employee_id
        WHERE s.pet_id=%s AND s.status='DANG_CHAM_SOC'
        ORDER BY s.id DESC LIMIT 1
        """,
        (pet_id,),
    )


def list_by_pet(pet_id: int, limit: int = 50) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT s.*, u.full_name AS employee_name
        FROM pet_stay s
        LEFT JOIN user u ON u.id = s.employee_id
        WHERE s.pet_id=%s
        ORDER BY s.check_in_at DESC
        LIMIT %s
        """,
        (pet_id, int(limit)),
    )


def create(
    pet_id: int,
    customer_id: int,
    employee_id: int | None,
    expected_check_out_at: datetime | None,
    daily_rate: float,
    note: str | None,
) -> int:
    return execute(
        """
        INSERT INTO pet_stay
        (pet_id, customer_id, employee_id, expected_check_out_at, daily_rate, note)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (pet_id, customer_id, employee_id, expected_check_out_at, daily_rate, note),
    )


def update_employee(stay_id: int, employee_id: int | None) -> None:
    execute("UPDATE pet_stay SET employee_id=%s WHERE id=%s", (employee_id, stay_id))


def update_note(stay_id: int, note: str | None) -> None:
    execute("UPDATE pet_stay SET note=%s WHERE id=%s", (note, stay_id))


def update_daily_rate(stay_id: int, daily_rate: float) -> None:
    execute("UPDATE pet_stay SET daily_rate=%s WHERE id=%s", (daily_rate, stay_id))


def mark_customer_picked_up(stay_id: int) -> None:
    execute(
        """
        UPDATE pet_stay
        SET status='KHACH_DA_NHAN', actual_check_out_at=NOW()
        WHERE id=%s AND status='DANG_CHAM_SOC'
        """,
        (stay_id,),
    )


def cancel(stay_id: int) -> None:
    execute("UPDATE pet_stay SET status='HUY' WHERE id=%s", (stay_id,))
