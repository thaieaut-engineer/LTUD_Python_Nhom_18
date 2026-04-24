"""Invoice service (C4-C5): tao hoa don tu appointment, cap nhat giam gia/thue."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from mysql.connector import Error as MySQLError

from ..dao import (
    appointment_dao,
    appointment_service_dao,
    invoice_dao,
    invoice_item_dao,
)
from ..session import Session


class InvoiceError(Exception):
    pass


def _today_prefix(now: datetime | None = None) -> str:
    d = (now or datetime.now()).strftime("%Y%m%d")
    return f"HD{d}"


def generate_invoice_no() -> str:
    """Sinh invoice_no theo ngày: HDYYYYMMDD-####."""
    prefix = _today_prefix()
    # count all invoices today
    rows = invoice_dao.list_recent(limit=500)
    today_count = sum(1 for r in rows if str(r.get("invoice_no", "")).startswith(prefix))
    return f"{prefix}-{today_count + 1:04d}"


def create_from_appointment(appointment_id: int, discount_amount: Decimal = Decimal("0"), tax_amount: Decimal = Decimal("0")) -> int:
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

    inv_no = generate_invoice_no()
    try:
        inv_id = invoice_dao.create(
            appointment_id=appointment_id,
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
            )
        return inv_id
    except MySQLError as exc:
        raise InvoiceError(f"Không thể tạo hóa đơn: {exc}") from exc


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


def list_recent(limit: int = 100) -> list[dict]:
    return invoice_dao.list_recent(limit=limit)

