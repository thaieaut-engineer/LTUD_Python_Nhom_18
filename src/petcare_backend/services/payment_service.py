"""Payment service (C6)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from mysql.connector import Error as MySQLError

from ..dao import invoice_dao, payment_dao
from ..session import Session


class PaymentError(Exception):
    pass


METHOD_LABEL_TO_DB = {
    "Tiền mặt": "TIEN_MAT",
    "Chuyển khoản": "CHUYEN_KHOAN",
    "Thẻ": "THE",
}

METHOD_DB_TO_LABEL = {v: k for k, v in METHOD_LABEL_TO_DB.items()}


def add_payment(invoice_id: int, amount_text: str, method_label: str, note: str | None = None) -> int:
    inv = invoice_dao.get_by_id(invoice_id)
    if inv is None:
        raise PaymentError("Hóa đơn không tồn tại.")

    method_db = METHOD_LABEL_TO_DB.get(method_label)
    if not method_db:
        raise PaymentError("Phương thức thanh toán không hợp lệ.")

    try:
        amount = Decimal((amount_text or "").strip().replace(".", "").replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise PaymentError("Số tiền không hợp lệ.") from exc

    if amount <= 0:
        raise PaymentError("Số tiền phải > 0.")

    current = Session.current()
    created_by = current.id if current else None

    try:
        pay_id = payment_dao.create(invoice_id, float(amount), method_db, created_by, (note or "").strip() or None)
    except MySQLError as exc:
        raise PaymentError(f"Không thể thanh toán: {exc}") from exc

    total_paid = Decimal(str(payment_dao.sum_paid(invoice_id)))
    total_amount = Decimal(str(inv["total_amount"]))

    new_status = "DA_TT" if total_paid >= total_amount else "CHUA_TT"
    invoice_dao.update_payment_status(invoice_id, new_status)
    return pay_id


def list_payments(invoice_id: int) -> list[dict]:
    rows = payment_dao.list_by_invoice(invoice_id)
    for r in rows:
        r["method_label"] = METHOD_DB_TO_LABEL.get(r.get("method"), r.get("method"))
    return rows

