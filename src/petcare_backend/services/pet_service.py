"""Service cho Pet (CRUD + validation)."""
from __future__ import annotations

from mysql.connector import Error as MySQLError

from ..dao import pet_dao


class PetError(Exception):
    pass


def list_pets(customer_id: int | None = None):
    return pet_dao.list_all(customer_id=customer_id)


def create_pet(
    customer_id: int,
    name: str,
    species: str,
    breed: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    health_note: str | None = None,
) -> int:
    name = (name or "").strip()
    species = (species or "").strip()
    breed = (breed or "").strip() or None
    gender = (gender or "").strip() or None
    health_note = (health_note or "").strip() or None

    if not customer_id:
        raise PetError("Vui lòng chọn khách hàng.")
    if not name:
        raise PetError("Vui lòng nhập tên thú cưng.")
    if not species:
        raise PetError("Vui lòng nhập loài.")
    if age is not None and age < 0:
        raise PetError("Tuổi không hợp lệ.")

    try:
        return pet_dao.create(customer_id, name, species, breed, age, gender, health_note)
    except MySQLError as exc:
        raise PetError("Không thể thêm thú cưng. Kiểm tra dữ liệu đầu vào.") from exc


def update_pet(
    pet_id: int,
    customer_id: int,
    name: str,
    species: str,
    breed: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    health_note: str | None = None,
) -> None:
    name = (name or "").strip()
    species = (species or "").strip()
    breed = (breed or "").strip() or None
    gender = (gender or "").strip() or None
    health_note = (health_note or "").strip() or None

    if not customer_id:
        raise PetError("Vui lòng chọn khách hàng.")
    if not name:
        raise PetError("Vui lòng nhập tên thú cưng.")
    if not species:
        raise PetError("Vui lòng nhập loài.")
    if age is not None and age < 0:
        raise PetError("Tuổi không hợp lệ.")

    try:
        pet_dao.update(pet_id, customer_id, name, species, breed, age, gender, health_note)
    except MySQLError as exc:
        raise PetError("Không thể cập nhật thú cưng.") from exc


def delete_pet(pet_id: int) -> None:
    try:
        pet_dao.delete(pet_id)
    except MySQLError as exc:
        raise PetError("Không thể xoá thú cưng vì đã phát sinh lịch hẹn.") from exc

