"""Service cho Customer (CRUD + validation)."""
from __future__ import annotations

import re

from mysql.connector import Error as MySQLError

from ..dao import customer_dao


class CustomerError(Exception):
    pass


_PHONE_RE = re.compile(r"^[0-9+() .-]{6,20}$")


def list_customers(query: str | None = None):
    return customer_dao.list_all(query=query)


def create_customer(full_name: str, phone: str, address: str | None = None, email: str | None = None) -> int:
    full_name = (full_name or "").strip()
    phone = (phone or "").strip()
    address = (address or "").strip() or None
    email = (email or "").strip() or None

    if not full_name:
        raise CustomerError("Vui lòng nhập tên khách hàng.")
    if not phone:
        raise CustomerError("Vui lòng nhập số điện thoại.")
    if not _PHONE_RE.match(phone):
        raise CustomerError("Số điện thoại không hợp lệ.")

    try:
        return customer_dao.create(full_name=full_name, phone=phone, address=address, email=email)
    except MySQLError as exc:
        if "Duplicate" in str(exc) or "duplicate" in str(exc):
            raise CustomerError("Số điện thoại đã tồn tại.") from exc
        raise


def update_customer(customer_id: int, full_name: str, phone: str, address: str | None = None, email: str | None = None) -> None:
    full_name = (full_name or "").strip()
    phone = (phone or "").strip()
    address = (address or "").strip() or None
    email = (email or "").strip() or None

    if not full_name:
        raise CustomerError("Vui lòng nhập tên khách hàng.")
    if not phone:
        raise CustomerError("Vui lòng nhập số điện thoại.")
    if not _PHONE_RE.match(phone):
        raise CustomerError("Số điện thoại không hợp lệ.")

    try:
        customer_dao.update(customer_id=customer_id, full_name=full_name, phone=phone, address=address, email=email)
    except MySQLError as exc:
        if "Duplicate" in str(exc) or "duplicate" in str(exc):
            raise CustomerError("Số điện thoại đã tồn tại.") from exc
        raise


def delete_customer(customer_id: int) -> None:
    try:
        customer_dao.delete(customer_id)
    except MySQLError as exc:
        # co appointment -> RESTRICT
        raise CustomerError(
            "Không thể xoá khách hàng vì đã phát sinh lịch hẹn/hoá đơn. "
            "Hãy xoá lịch hẹn liên quan hoặc đánh dấu khách ngừng hoạt động (chức năng sẽ bổ sung sau)."
        ) from exc

