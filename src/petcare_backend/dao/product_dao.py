"""DAO cho bang product (do an / phu kien)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..db import execute, fetch_all, fetch_one
from ..models import Product


CATEGORY_LABEL_TO_DB = {
    "Đồ ăn": "DO_AN",
    "Phụ kiện": "PHU_KIEN",
}
CATEGORY_DB_TO_LABEL = {v: k for k, v in CATEGORY_LABEL_TO_DB.items()}


def _row_to_product(row: dict[str, Any]) -> Product:
    return Product(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        price=Decimal(row["price"]),
        stock=int(row.get("stock") or 0),
        sku=row.get("sku"),
        description=row.get("description"),
        is_active=bool(row["is_active"]),
    )


def list_all(
    active_only: bool = True,
    query: str | None = None,
    category: str | None = None,
) -> list[Product]:
    sql = (
        "SELECT id, name, category, sku, price, stock, description, is_active "
        "FROM product"
    )
    where: list[str] = []
    params: list[Any] = []
    if active_only:
        where.append("is_active=1")
    if category:
        where.append("category=%s")
        params.append(category)
    q = (query or "").strip()
    if q:
        like = f"%{q}%"
        where.append("(name LIKE %s OR sku LIKE %s OR description LIKE %s)")
        params.extend([like, like, like])
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC"
    return [_row_to_product(r) for r in fetch_all(sql, tuple(params))]


def get_by_id(product_id: int) -> Product | None:
    row = fetch_one(
        "SELECT id, name, category, sku, price, stock, description, is_active "
        "FROM product WHERE id=%s",
        (product_id,),
    )
    return _row_to_product(row) if row else None


def create(
    name: str,
    category: str,
    price: Decimal,
    stock: int,
    sku: str | None,
    description: str | None,
    is_active: bool,
) -> int:
    return execute(
        "INSERT INTO product (name, category, sku, price, stock, description, is_active) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (
            name,
            category,
            sku,
            str(price),
            int(stock),
            description,
            1 if is_active else 0,
        ),
    )


def update(
    product_id: int,
    name: str,
    category: str,
    price: Decimal,
    stock: int,
    sku: str | None,
    description: str | None,
    is_active: bool,
) -> None:
    execute(
        "UPDATE product SET name=%s, category=%s, sku=%s, price=%s, stock=%s, "
        "description=%s, is_active=%s WHERE id=%s",
        (
            name,
            category,
            sku,
            str(price),
            int(stock),
            description,
            1 if is_active else 0,
            product_id,
        ),
    )


def soft_delete(product_id: int) -> None:
    """An san pham (giu lai du lieu lich su trong invoice_item)."""
    execute("UPDATE product SET is_active=0 WHERE id=%s", (product_id,))


def adjust_stock(product_id: int, delta: int) -> None:
    """Cong (delta>0) / tru (delta<0) ton kho. Khong cho ton kho < 0."""
    execute(
        "UPDATE product SET stock = GREATEST(stock + %s, 0) WHERE id=%s",
        (int(delta), product_id),
    )
