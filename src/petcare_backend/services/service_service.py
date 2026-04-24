"""Service cho Service (CRUD + validation)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from mysql.connector import Error as MySQLError

from ..dao import service_dao


class ServiceError(Exception):
    pass


def list_services(active_only: bool = True):
    return service_dao.list_all(active_only=active_only)


def _parse_price(raw: str) -> Decimal:
    raw = (raw or "").strip().replace(".", "").replace(",", "")
    if not raw:
        return Decimal("0")
    return Decimal(raw)


def create_service(
    name: str,
    price: str,
    description: str | None = None,
    duration_min: int | None = None,
    is_active: bool = True,
) -> int:
    name = (name or "").strip()
    description = (description or "").strip() or None

    if not name:
        raise ServiceError("Vui lòng nhập tên dịch vụ.")

    try:
        price_dec = _parse_price(price)
    except InvalidOperation as exc:
        raise ServiceError("Giá không hợp lệ.") from exc

    if price_dec < 0:
        raise ServiceError("Giá không hợp lệ.")

    try:
        return service_dao.create(name, price_dec, description, duration_min, is_active)
    except MySQLError as exc:
        if "Duplicate" in str(exc) or "duplicate" in str(exc):
            raise ServiceError("Tên dịch vụ đã tồn tại.") from exc
        raise


def update_service(
    service_id: int,
    name: str,
    price: str,
    description: str | None = None,
    duration_min: int | None = None,
    is_active: bool = True,
) -> None:
    name = (name or "").strip()
    description = (description or "").strip() or None
    if not name:
        raise ServiceError("Vui lòng nhập tên dịch vụ.")
    try:
        price_dec = _parse_price(price)
    except InvalidOperation as exc:
        raise ServiceError("Giá không hợp lệ.") from exc
    if price_dec < 0:
        raise ServiceError("Giá không hợp lệ.")

    try:
        service_dao.update(service_id, name, price_dec, description, duration_min, is_active)
    except MySQLError as exc:
        if "Duplicate" in str(exc) or "duplicate" in str(exc):
            raise ServiceError("Tên dịch vụ đã tồn tại.") from exc
        raise


def deactivate_service(service_id: int) -> None:
    try:
        service_dao.delete(service_id)
    except MySQLError as exc:
        raise ServiceError("Không thể xoá/ẩn dịch vụ.") from exc

