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


def list_all(customer_id: int | None = None, query: str | None = None) -> list[Pet]:
    q = (query or "").strip()
    needs_join = bool(q)
    if needs_join:
        sql = (
            "SELECT p.id, p.customer_id, p.name, p.species, p.breed, p.age, p.gender, p.health_note "
            "FROM pet p LEFT JOIN customer c ON c.id = p.customer_id"
        )
    else:
        sql = "SELECT id, customer_id, name, species, breed, age, gender, health_note FROM pet"
    where: list[str] = []
    params: list[Any] = []
    if customer_id is not None:
        col = "p.customer_id" if needs_join else "customer_id"
        where.append(f"{col}=%s")
        params.append(customer_id)
    if q:
        like = f"%{q}%"
        where.append(
            "(p.name LIKE %s OR p.species LIKE %s OR p.breed LIKE %s OR c.full_name LIKE %s)"
        )
        params.extend([like, like, like, like])
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC" if not needs_join else " ORDER BY p.id DESC"
    return [_row_to_pet(r) for r in fetch_all(sql, tuple(params))]


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

