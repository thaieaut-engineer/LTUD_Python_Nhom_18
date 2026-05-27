"""Invoice service (C4-C5): tao hoa don tu lich hen / ban le, them san pham, cap nhat tong tien."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from mysql.connector import Error as MySQLError

from ..activity_log import log_admin
from ..dao import (
    appointment_dao,
    appointment_service_dao,
    invoice_dao,
    invoice_item_dao,
    product_dao,
)
from ..session import Session
from . import product_service


class InvoiceError(Exception):
    pass


def _today_prefix(now: datetime | None = None) -> str:
    d = (now or datetime.now()).strftime("%Y%m%d")
    return f"HD{d}"


def generate_invoice_no(retail: bool = False) -> str:
    """Sinh invoice_no theo ngay: HDYYYYMMDD-#### (HD = dich vu, BL = ban le)."""
    base = _today_prefix()
    prefix = base.replace("HD", "BL", 1) if retail else base
    rows = invoice_dao.list_recent(limit=500)
    today_count = sum(1 for r in rows if str(r.get("invoice_no", "")).startswith(prefix))
    return f"{prefix}-{today_count + 1:04d}"


def _recalc_totals_from_items(invoice_id: int) -> Decimal:
    items = invoice_item_dao.list_by_invoice(invoice_id)
    subtotal = Decimal("0")
    for r in items:
        subtotal += Decimal(str(r["unit_price"])) * Decimal(int(r["quantity"]))
    inv = invoice_dao.get_by_id(invoice_id)
    if inv is None:
        return subtotal
    discount = Decimal(str(inv.get("discount_amount") or 0))
    tax = Decimal(str(inv.get("tax_amount") or 0))
    total = subtotal - discount + tax
    if total < 0:
        total = Decimal("0")
    invoice_dao.update_totals(
        invoice_id, float(subtotal), float(discount), float(tax), float(total)
    )
    return total


def create_from_appointment(
    appointment_id: int,
    discount_amount: Decimal = Decimal("0"),
    tax_amount: Decimal = Decimal("0"),
) -> int:
    ap = appointment_dao.get_by_id(appointment_id)
    if ap is None:
        raise InvoiceError("Lịch hẹn không tồn tại.")
    if ap["status"] != "HOAN_THANH":
        raise InvoiceError("Chỉ tạo hóa đơn khi lịch hẹn đã Hoàn thành.")

    exists = invoice_dao.get_by_appointment(appointment_id)
    if exists is not None:
        raise InvoiceError("Lịch hẹn này đã có hóa đơn.")

    items = appointment_service_dao.list_by_appointment(appointment_id)
    if not items:
        raise InvoiceError("Lịch hẹn chưa có dịch vụ.")

    subtotal = Decimal("0")
    for it in items:
        subtotal += Decimal(str(it["unit_price"])) * Decimal(int(it["quantity"]))

    discount = Decimal(discount_amount)
    tax = Decimal(tax_amount)
    if discount < 0 or tax < 0:
        raise InvoiceError("Giảm giá/thuế không hợp lệ.")
    total = subtotal - discount + tax
    if total < 0:
        raise InvoiceError("Tổng tiền không hợp lệ.")

    current = Session.current()
    created_by = current.id if current else None

    inv_no = generate_invoice_no(retail=False)
    try:
        inv_id = invoice_dao.create(
            appointment_id=appointment_id,
            customer_id=int(ap["customer_id"]),
            invoice_type="SERVICE",
            invoice_no=inv_no,
            subtotal_amount=float(subtotal),
            discount_amount=float(discount),
            tax_amount=float(tax),
            total_amount=float(total),
            payment_status="CHUA_TT",
            created_by=created_by,
            note=None,
        )
        for it in items:
            pet_id_raw = it.get("pet_id")
            pet_id_val = int(pet_id_raw) if pet_id_raw is not None else None
            invoice_item_dao.create(
                invoice_id=inv_id,
                service_id=int(it["service_id"]),
                quantity=int(it["quantity"]),
                unit_price=float(it["unit_price"]),
                pet_id=pet_id_val,
                item_type="SERVICE",
            )
        log_admin(
            "CREATE_INVOICE",
            entity="invoice",
            entity_id=int(inv_id),
            message=f"Tạo HĐ dịch vụ {inv_no} từ lịch hẹn #{appointment_id}",
        )
        return inv_id
    except MySQLError as exc:
        raise InvoiceError(f"Không thể tạo hóa đơn: {exc}") from exc


def create_retail_invoice(
    customer_id: int | None,
    items: list[tuple[int, int]],
    discount_amount: Decimal = Decimal("0"),
    tax_amount: Decimal = Decimal("0"),
    note: str | None = None,
) -> int:
    """Tao hoa don ban le (POS).

    items: list of (product_id, quantity).
    customer_id co the None -> khach vang lai.
    """
    if not items:
        raise InvoiceError("Vui lòng chọn ít nhất một sản phẩm.")

    # Validate va thu thap don gia
    enriched: list[tuple[int, int, Decimal, str]] = []  # (pid, qty, price, name)
    for pid, qty in items:
        if qty <= 0:
            raise InvoiceError("Số lượng không hợp lệ.")
        p = product_dao.get_by_id(int(pid))
        if p is None:
            raise InvoiceError("Sản phẩm không tồn tại.")
        if not p.is_active:
            raise InvoiceError(f"Sản phẩm '{p.name}' đã bị ẩn.")
        if p.stock < qty:
            raise InvoiceError(
                f"Sản phẩm '{p.name}' không đủ tồn kho (còn {p.stock}, cần {qty})."
            )
        enriched.append((p.id, int(qty), Decimal(p.price), p.name))

    subtotal = sum((price * Decimal(qty) for _, qty, price, _ in enriched), Decimal("0"))
    discount = Decimal(discount_amount)
    tax = Decimal(tax_amount)
    if discount < 0 or tax < 0:
        raise InvoiceError("Giảm giá/thuế không hợp lệ.")
    total = subtotal - discount + tax
    if total < 0:
        raise InvoiceError("Tổng tiền không hợp lệ.")

    current = Session.current()
    created_by = current.id if current else None

    inv_no = generate_invoice_no(retail=True)
    try:
        inv_id = invoice_dao.create(
            appointment_id=None,
            customer_id=int(customer_id) if customer_id else None,
            invoice_type="RETAIL",
            invoice_no=inv_no,
            subtotal_amount=float(subtotal),
            discount_amount=float(discount),
            tax_amount=float(tax),
            total_amount=float(total),
            payment_status="CHUA_TT",
            created_by=created_by,
            note=note,
        )
        for pid, qty, price, _ in enriched:
            invoice_item_dao.create(
                invoice_id=inv_id,
                product_id=pid,
                quantity=qty,
                unit_price=float(price),
                item_type="PRODUCT",
            )
            product_service.reduce_stock(pid, qty)
        log_admin(
            "CREATE_RETAIL_INVOICE",
            entity="invoice",
            entity_id=int(inv_id),
            message=f"Tạo HĐ bán lẻ {inv_no} ({len(enriched)} sp)",
        )
        return inv_id
    except (MySQLError, product_service.ProductError) as exc:
        raise InvoiceError(f"Không thể tạo hóa đơn bán lẻ: {exc}") from exc


def add_product_to_invoice(invoice_id: int, product_id: int, quantity: int) -> int:
    """Them san pham vao hoa don dich vu / ban le da co. Tu dong tinh lai tong."""
    if quantity <= 0:
        raise InvoiceError("Số lượng phải lớn hơn 0.")

    inv = invoice_dao.get_by_id(invoice_id)
    if inv is None:
        raise InvoiceError("Hóa đơn không tồn tại.")
    if str(inv.get("payment_status")) == "DA_TT":
        raise InvoiceError("Hóa đơn đã thanh toán, không thể thêm sản phẩm.")

    p = product_dao.get_by_id(int(product_id))
    if p is None:
        raise InvoiceError("Sản phẩm không tồn tại.")
    if not p.is_active:
        raise InvoiceError(f"Sản phẩm '{p.name}' đã bị ẩn.")
    if p.stock < quantity:
        raise InvoiceError(
            f"Sản phẩm '{p.name}' không đủ tồn kho (còn {p.stock}, cần {quantity})."
        )

    try:
        item_id = invoice_item_dao.create(
            invoice_id=invoice_id,
            product_id=int(product_id),
            quantity=int(quantity),
            unit_price=float(p.price),
            item_type="PRODUCT",
        )
        product_service.reduce_stock(int(product_id), int(quantity))
        _recalc_totals_from_items(invoice_id)
        log_admin(
            "ADD_PRODUCT_TO_INVOICE",
            entity="invoice",
            entity_id=int(invoice_id),
            message=f"Thêm SP '{p.name}' x{quantity}",
        )
        return item_id
    except (MySQLError, product_service.ProductError) as exc:
        raise InvoiceError(f"Không thể thêm sản phẩm: {exc}") from exc


def remove_invoice_item(item_id: int) -> None:
    """Xoa 1 dong khoi hoa don. Neu la SP -> hoan kho."""
    item = invoice_item_dao.get_by_id(int(item_id))
    if item is None:
        return
    inv_id = int(item["invoice_id"])
    inv = invoice_dao.get_by_id(inv_id)
    if inv is None:
        return
    if str(inv.get("payment_status")) == "DA_TT":
        raise InvoiceError("Hóa đơn đã thanh toán, không thể chỉnh sửa.")

    try:
        if item.get("item_type") == "PRODUCT" and item.get("product_id"):
            product_service.restore_stock(int(item["product_id"]), int(item["quantity"]))
        invoice_item_dao.delete(int(item_id))
        _recalc_totals_from_items(inv_id)
    except MySQLError as exc:
        raise InvoiceError(f"Không thể xoá dòng: {exc}") from exc


def recalc_totals(invoice_id: int, discount_amount: Decimal, tax_amount: Decimal) -> None:
    rows = invoice_item_dao.list_by_invoice(invoice_id)
    subtotal = Decimal("0")
    for r in rows:
        subtotal += Decimal(str(r["unit_price"])) * Decimal(int(r["quantity"]))

    discount = Decimal(discount_amount)
    tax = Decimal(tax_amount)
    if discount < 0 or tax < 0:
        raise InvoiceError("Giảm giá/thuế không hợp lệ.")
    total = subtotal - discount + tax
    if total < 0:
        raise InvoiceError("Tổng tiền không hợp lệ.")

    invoice_dao.update_totals(invoice_id, float(subtotal), float(discount), float(tax), float(total))


def sync_invoice_totals(invoice_id: int) -> Decimal:
    """Cập nhật tổng HĐ theo các dòng chi tiết (trước khi thanh toán / hiển thị)."""
    return _recalc_totals_from_items(invoice_id)


def get_payment_amounts(invoice_id: int) -> dict:
    """Tổng HĐ, đã trả, còn phải trả — sau khi đồng bộ từ invoice_item."""
    from ..dao import payment_dao

    sync_invoice_totals(invoice_id)
    inv = invoice_dao.get_by_id(invoice_id)
    if inv is None:
        raise InvoiceError("Hóa đơn không tồn tại.")
    total = Decimal(str(inv.get("total_amount") or 0))
    paid = Decimal(str(payment_dao.sum_paid(invoice_id)))
    remaining = total - paid
    if remaining < 0:
        remaining = Decimal(0)
    return {
        "invoice_no": str(inv.get("invoice_no") or ""),
        "total": total,
        "paid": paid,
        "remaining": remaining,
    }


def list_recent(
    limit: int = 100,
    *,
    created_by: int | None = None,
    invoice_type: str | None = None,
) -> list[dict]:
    return invoice_dao.list_recent(limit=limit, created_by=created_by, invoice_type=invoice_type)


def list_for_user(user_id: int, limit: int = 100) -> list[dict]:
    """Liet ke hoa don do 1 user tao (User - Invoice)."""
    return invoice_dao.list_recent(limit=limit, created_by=user_id)
