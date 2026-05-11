"""Service cho Product (do an / phu kien) - CRUD + kiem kho."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from mysql.connector import Error as MySQLError

from ..activity_log import log_admin
from ..dao import product_dao


class ProductError(Exception):
    pass


VALID_CATEGORIES = ("DO_AN", "PHU_KIEN")
CATEGORY_LABELS = {
    "DO_AN": "Đồ ăn",
    "PHU_KIEN": "Phụ kiện",
}
LABEL_TO_CATEGORY = {v: k for k, v in CATEGORY_LABELS.items()}


def list_products(
    active_only: bool = True,
    query: str | None = None,
    category: str | None = None,
):
    """Liet ke san pham. category co the la 'DO_AN' / 'PHU_KIEN' / nhan tieng Viet."""
    cat = category
    if cat and cat in LABEL_TO_CATEGORY:
        cat = LABEL_TO_CATEGORY[cat]
    return product_dao.list_all(active_only=active_only, query=query, category=cat)


def get_product(product_id: int):
    return product_dao.get_by_id(product_id)


def _parse_price(raw: str) -> Decimal:
    raw = (raw or "").strip().replace(".", "").replace(",", "")
    if not raw:
        return Decimal("0")
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ProductError("Giá không hợp lệ.") from exc


def _validate_category(label_or_code: str) -> str:
    val = (label_or_code or "").strip()
    if val in LABEL_TO_CATEGORY:
        return LABEL_TO_CATEGORY[val]
    if val.upper() in VALID_CATEGORIES:
        return val.upper()
    raise ProductError("Loại sản phẩm không hợp lệ. Chọn 'Đồ ăn' hoặc 'Phụ kiện'.")


def create_product(
    name: str,
    category: str,
    price: str,
    stock: int = 0,
    sku: str | None = None,
    description: str | None = None,
    is_active: bool = True,
) -> int:
    name = (name or "").strip()
    sku = (sku or "").strip() or None
    description = (description or "").strip() or None
    if not name:
        raise ProductError("Vui lòng nhập tên sản phẩm.")
    cat = _validate_category(category)
    price_dec = _parse_price(price)
    if price_dec < 0:
        raise ProductError("Giá không hợp lệ.")
    if stock < 0:
        raise ProductError("Tồn kho không hợp lệ.")

    try:
        new_id = product_dao.create(
            name=name,
            category=cat,
            price=price_dec,
            stock=int(stock),
            sku=sku,
            description=description,
            is_active=is_active,
        )
        log_admin(
            "CREATE_PRODUCT",
            entity="product",
            entity_id=int(new_id),
            message=f"Tạo sản phẩm '{name}' ({CATEGORY_LABELS.get(cat, cat)})",
            extra={"price": str(price_dec), "stock": int(stock)},
        )
        return new_id
    except MySQLError as exc:
        if "Duplicate" in str(exc) or "duplicate" in str(exc):
            raise ProductError("Tên sản phẩm đã tồn tại.") from exc
        raise


def update_product(
    product_id: int,
    name: str,
    category: str,
    price: str,
    stock: int,
    sku: str | None = None,
    description: str | None = None,
    is_active: bool = True,
) -> None:
    name = (name or "").strip()
    sku = (sku or "").strip() or None
    description = (description or "").strip() or None
    if not name:
        raise ProductError("Vui lòng nhập tên sản phẩm.")
    cat = _validate_category(category)
    price_dec = _parse_price(price)
    if price_dec < 0:
        raise ProductError("Giá không hợp lệ.")
    if stock < 0:
        raise ProductError("Tồn kho không hợp lệ.")

    try:
        product_dao.update(
            product_id=product_id,
            name=name,
            category=cat,
            price=price_dec,
            stock=int(stock),
            sku=sku,
            description=description,
            is_active=is_active,
        )
        log_admin(
            "UPDATE_PRODUCT",
            entity="product",
            entity_id=int(product_id),
            message=f"Cập nhật sản phẩm '{name}'",
            extra={"price": str(price_dec), "stock": int(stock)},
        )
    except MySQLError as exc:
        if "Duplicate" in str(exc) or "duplicate" in str(exc):
            raise ProductError("Tên sản phẩm đã tồn tại.") from exc
        raise


def deactivate_product(product_id: int) -> None:
    try:
        product_dao.soft_delete(product_id)
        log_admin(
            "DEACTIVATE_PRODUCT",
            entity="product",
            entity_id=int(product_id),
            message="Ẩn sản phẩm",
        )
    except MySQLError as exc:
        raise ProductError("Không thể ẩn sản phẩm.") from exc


def reduce_stock(product_id: int, qty: int) -> None:
    """Tru ton kho theo so luong ban. Goi trong service tao hoa don."""
    if qty <= 0:
        return
    p = product_dao.get_by_id(product_id)
    if p is None:
        raise ProductError("Sản phẩm không tồn tại.")
    if p.stock < qty:
        raise ProductError(
            f"Sản phẩm '{p.name}' không đủ tồn kho (còn {p.stock}, cần {qty})."
        )
    product_dao.adjust_stock(product_id, -int(qty))


def restore_stock(product_id: int, qty: int) -> None:
    if qty <= 0:
        return
    product_dao.adjust_stock(product_id, int(qty))
