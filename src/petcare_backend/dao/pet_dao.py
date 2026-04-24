"""DAO cho bang pet."""
from __future__ import annotations

from typing import Any, Sequence

from ..db import execute, fetch_all, fetch_one
from ..models import Pet


def _row_to_pet(row: dict[str, Any]) -> Pet:
    return Pet(
        id=row["id"],
        customer_id=row["customer_id"],
        name=row["name"],
        species=row["species"],
        breed=row.get("breed"),
        age=row.get("age"),
        gender=row.get("gender"),
        health_note=row.get("health_note"),
    )


def list_all(customer_id: int | None = None) -> list[Pet]:
    sql = "SELECT id, customer_id, name, species, breed, age, gender, health_note FROM pet"
    params: Sequence[Any] = ()
    if customer_id is not None:
        sql += " WHERE customer_id=%s"
        params = (customer_id,)
    sql += " ORDER BY id DESC"
    return [_row_to_pet(r) for r in fetch_all(sql, params)]


def get_by_id(pet_id: int) -> Pet | None:
    row = fetch_one(
        "SELECT id, customer_id, name, species, breed, age, gender, health_note FROM pet WHERE id=%s",
        (pet_id,),
    )
    return _row_to_pet(row) if row else None


def create(
    customer_id: int,
    name: str,
    species: str,
    breed: str | None,
    age: int | None,
    gender: str | None,
    health_note: str | None,
) -> int:
    return execute(
        "INSERT INTO pet (customer_id, name, species, breed, age, gender, health_note) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (customer_id, name, species, breed, age, gender, health_note),
    )


def update(
    pet_id: int,
    customer_id: int,
    name: str,
    species: str,
    breed: str | None,
    age: int | None,
    gender: str | None,
    health_note: str | None,
) -> None:
    execute(
        "UPDATE pet SET customer_id=%s, name=%s, species=%s, breed=%s, age=%s, gender=%s, health_note=%s "
        "WHERE id=%s",
        (customer_id, name, species, breed, age, gender, health_note, pet_id),
    )


def delete(pet_id: int) -> None:
    execute("DELETE FROM pet WHERE id=%s", (pet_id,))

