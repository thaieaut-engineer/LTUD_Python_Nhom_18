"""Service luu tru / cham soc thu cung theo ngay."""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from mysql.connector import Error as MySQLError

from ..activity_log import log_admin
from ..dao import (
    invoice_dao,
    invoice_item_dao,
    pet_care_log_dao,
    pet_care_media_dao,
    pet_dao,
    pet_stay_dao,
    product_dao,
    service_dao,
)
from ..session import Session
from . import invoice_service, product_service

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MEDIA_ROOT = PROJECT_ROOT / "data" / "pet_care_media"

STAY_STATUS_LABEL = {
    "DANG_CHAM_SOC": "Đang chăm sóc",
    "KHACH_DA_NHAN": "Khách đã nhận",
    "HUY": "Đã huỷ",
}

LOG_TYPE_LABEL = {
    "FEEDING": "Cho ăn",
    "CARE": "Chăm sóc",
    "STATUS": "Tình trạng",
}


class BoardingError(Exception):
    pass


def _media_dir(stay_id: int) -> Path:
    d = MEDIA_ROOT / str(stay_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def copy_media_file(stay_id: int, source_path: str) -> str:
    src = Path(source_path)
    if not src.is_file():
        raise BoardingError("File không tồn tại.")
    dest = _media_dir(stay_id) / f"{uuid.uuid4().hex}_{src.name}"
    shutil.copy2(src, dest)
    return str(dest)


def get_active_stay(pet_id: int) -> dict | None:
    return pet_stay_dao.get_active_by_pet(pet_id)


def get_workspace_stay(pet_id: int) -> dict | None:
    """Đợt đang chăm sóc, hoặc đợt mới nhất (để xem/sửa HĐ)."""
    stay = pet_stay_dao.get_active_by_pet(pet_id)
    if stay is not None:
        return stay
    return pet_stay_dao.get_latest_by_pet(pet_id)


PAYMENT_STATUS_LABEL = {
    "CHUA_TT": "Chưa thanh toán",
    "DA_TT": "Đã thanh toán",
    "HOAN_TIEN": "Hoàn tiền",
}


def reopen_stay_invoice(stay_id: int) -> None:
    """Đặt lại HĐ về chưa thanh toán để chỉnh sửa (sau khi bấm nhầm)."""
    inv = invoice_dao.get_by_pet_stay(stay_id)
    if inv is None:
        raise BoardingError("Chưa có hóa đơn.")
    if str(inv.get("payment_status")) != "DA_TT":
        raise BoardingError("Hóa đơn chưa ở trạng thái đã thanh toán.")
    invoice_dao.update_payment_status(int(inv["id"]), "CHUA_TT")


def check_in(
    pet_id: int,
    employee_id: int | None = None,
    expected_check_out_at: datetime | None = None,
    daily_rate: float = 0,
    note: str | None = None,
) -> int:
    pet = pet_dao.get_by_id(pet_id)
    if pet is None:
        raise BoardingError("Thú cưng không tồn tại.")
    if pet_stay_dao.get_active_by_pet(pet_id) is not None:
        raise BoardingError("Thú cưng đang trong đợt chăm sóc.")

    try:
        stay_id = pet_stay_dao.create(
            pet_id=pet_id,
            customer_id=pet.customer_id,
            employee_id=employee_id,
            expected_check_out_at=expected_check_out_at,
            daily_rate=float(daily_rate),
            note=(note or "").strip() or None,
        )
        pet_care_log_dao.create(
            stay_id,
            employee_id,
            "STATUS",
            "Nhận thú vào chăm sóc.",
        )
        log_admin(
            "PET_CHECK_IN",
            entity="pet_stay",
            entity_id=int(stay_id),
            message=f"Nhận thú #{pet_id} vào chăm sóc",
        )
        return int(stay_id)
    except MySQLError as exc:
        raise BoardingError("Không thể nhận thú. Kiểm tra đã chạy migration boarding.") from exc


def assign_employee(stay_id: int, employee_id: int | None, employee_name: str | None = None) -> None:
    stay = pet_stay_dao.get_by_id(stay_id)
    if stay is None:
        raise BoardingError("Đợt chăm sóc không tồn tại.")
    if stay["status"] != "DANG_CHAM_SOC":
        raise BoardingError("Chỉ gán nhân viên khi đang chăm sóc.")
    pet_stay_dao.update_employee(stay_id, employee_id)
    label = (employee_name or "").strip() or ("Chưa chọn" if not employee_id else f"NV #{employee_id}")
    pet_care_log_dao.create(
        stay_id,
        employee_id,
        "STATUS",
        f"Gán nhân viên chăm sóc: {label}.",
    )


def _require_active_stay(stay_id: int) -> dict:
    stay = pet_stay_dao.get_by_id(stay_id)
    if stay is None or stay["status"] != "DANG_CHAM_SOC":
        raise BoardingError("Đợt chăm sóc không hợp lệ hoặc đã kết thúc.")
    return stay


def _attach_images(
    stay_id: int,
    log_id: int,
    image_paths: list[str] | None,
    caption: str | None = None,
) -> int:
    count = 0
    for path in image_paths or []:
        if path and Path(path).is_file():
            add_media(stay_id, path, "IMAGE", caption, care_log_id=log_id)
            count += 1
    return count


def record_feeding(
    stay_id: int,
    product_id: int,
    quantity: int = 1,
    note: str | None = None,
    image_paths: list[str] | None = None,
    *,
    sync_invoice: bool = True,
) -> int:
    """Ghi nhận cho ăn: chọn đồ ăn trong shop, tải ảnh, trừ tồn kho, cộng HĐ nếu có."""
    stay = _require_active_stay(stay_id)
    if quantity < 1:
        raise BoardingError("Số lượng phải >= 1.")
    product = product_dao.get_by_id(int(product_id))
    if product is None:
        raise BoardingError("Sản phẩm không tồn tại.")
    if not product.is_active:
        raise BoardingError(f"Sản phẩm '{product.name}' đã bị ẩn.")
    if product.stock < quantity:
        raise BoardingError(
            f"'{product.name}' không đủ tồn (còn {product.stock}, cần {quantity})."
        )

    note_txt = (note or "").strip()
    content = f"Cho ăn: {product.name} × {quantity}"
    if note_txt:
        content += f" — {note_txt}"

    emp = stay.get("employee_id")
    try:
        log_id = int(
            pet_care_log_dao.create(
                stay_id, emp, "FEEDING", content,
                product_id=int(product_id), quantity=int(quantity),
            )
        )
        _attach_images(stay_id, log_id, image_paths, caption=product.name)
        product_service.reduce_stock(int(product_id), int(quantity))
        if sync_invoice and invoice_dao.get_by_pet_stay(stay_id) is not None:
            add_product_to_stay_invoice(stay_id, int(product_id), int(quantity))
        return log_id
    except product_service.ProductError as exc:
        raise BoardingError(str(exc)) from exc
    except MySQLError as exc:
        raise BoardingError(f"Không thể ghi cho ăn: {exc}") from exc


def record_care_service(
    stay_id: int,
    service_id: int,
    quantity: int = 1,
    note: str | None = None,
    image_paths: list[str] | None = None,
    *,
    sync_invoice: bool = True,
) -> int:
    """Ghi nhận dịch vụ chăm sóc kèm ảnh, cộng HĐ nếu có."""
    stay = _require_active_stay(stay_id)
    if quantity < 1:
        raise BoardingError("Số lượng phải >= 1.")
    svc = service_dao.get_by_id(int(service_id))
    if svc is None:
        raise BoardingError("Dịch vụ không tồn tại.")
    if not svc.is_active:
        raise BoardingError(f"Dịch vụ '{svc.name}' đã bị ẩn.")

    note_txt = (note or "").strip()
    content = f"Dịch vụ: {svc.name} × {quantity}"
    if note_txt:
        content += f" — {note_txt}"

    emp = stay.get("employee_id")
    try:
        log_id = int(
            pet_care_log_dao.create(
                stay_id, emp, "CARE", content,
                service_id=int(service_id), quantity=int(quantity),
            )
        )
        _attach_images(stay_id, log_id, image_paths, caption=svc.name)
        if sync_invoice and invoice_dao.get_by_pet_stay(stay_id) is not None:
            add_service_to_stay_invoice(stay_id, int(service_id), int(quantity))
        return log_id
    except MySQLError as exc:
        raise BoardingError(f"Không thể ghi dịch vụ: {exc}") from exc


def add_feeding_log(stay_id: int, content: str, employee_id: int | None = None) -> int:
    """Ghi chú cho ăn tự do (không chọn SP) — giữ tương thích."""
    content = (content or "").strip()
    if not content:
        raise BoardingError("Vui lòng nhập nội dung.")
    stay = _require_active_stay(stay_id)
    emp = employee_id or stay.get("employee_id")
    return int(pet_care_log_dao.create(stay_id, emp, "FEEDING", content))


def add_media(
    stay_id: int,
    source_path: str,
    media_type: str,
    caption: str | None = None,
    care_log_id: int | None = None,
) -> int:
    stay = pet_stay_dao.get_by_id(stay_id)
    if stay is None:
        raise BoardingError("Đợt chăm sóc không tồn tại.")
    if media_type not in ("IMAGE", "VIDEO"):
        raise BoardingError("Loại media không hợp lệ.")
    stored = copy_media_file(stay_id, source_path)
    return int(
        pet_care_media_dao.create(
            stay_id, care_log_id, media_type, stored, (caption or "").strip() or None
        )
    )


def mark_picked_up(stay_id: int) -> None:
    stay = pet_stay_dao.get_by_id(stay_id)
    if stay is None:
        raise BoardingError("Đợt chăm sóc không tồn tại.")
    if stay["status"] != "DANG_CHAM_SOC":
        raise BoardingError("Thú đã được trả hoặc đợt đã kết thúc.")
    pet_stay_dao.mark_customer_picked_up(stay_id)
    pet_care_log_dao.create(
        stay_id,
        stay.get("employee_id"),
        "STATUS",
        "Khách hàng đã nhận thú cưng.",
    )


def get_care_history(pet_id: int) -> list[dict]:
    return pet_care_log_dao.list_by_pet(pet_id)


def get_stay_detail(stay_id: int) -> dict | None:
    stay = pet_stay_dao.get_by_id(stay_id)
    if stay is None:
        return None
    stay["logs"] = pet_care_log_dao.list_by_stay(stay_id)
    stay["media"] = pet_care_media_dao.list_by_stay(stay_id)
    stay["invoice"] = invoice_dao.get_by_pet_stay(stay_id)
    return stay


def create_stay_invoice(stay_id: int, include_boarding_days: bool = True) -> int:
    stay = pet_stay_dao.get_by_id(stay_id)
    if stay is None:
        raise BoardingError("Đợt chăm sóc không tồn tại.")
    if invoice_dao.get_by_pet_stay(stay_id) is not None:
        raise BoardingError("Đợt này đã có hóa đơn.")

    subtotal = Decimal("0")
    boarding_lines: list[tuple[int, int, float]] = []  # service_id, qty, unit_price

    if include_boarding_days:
        rate = Decimal(str(stay.get("daily_rate") or 0))
        if rate > 0:
            check_in = stay["check_in_at"]
            end = stay.get("actual_check_out_at") or datetime.now()
            if hasattr(check_in, "date"):
                days = max(1, (end.date() - check_in.date()).days + 1)
            else:
                days = 1
            line_total = rate * Decimal(days)
            subtotal += line_total
            boarding_svc = None
            for s in service_dao.list_all(active_only=False):
                nm = (s.name or "").lower()
                if "lưu trú" in nm or "luu tru" in nm:
                    boarding_svc = s
                    break
            if boarding_svc is None:
                active = service_dao.list_all(active_only=True)
                boarding_svc = active[0] if active else None
            if boarding_svc is not None:
                boarding_lines.append((boarding_svc.id, days, float(rate)))

    current = Session.current()
    created_by = current.id if current else None
    inv_no = invoice_service.generate_invoice_no(retail=False).replace("HD", "LT", 1)

    try:
        inv_id = invoice_dao.create(
            appointment_id=None,
            customer_id=int(stay["customer_id"]),
            invoice_type="SERVICE",
            invoice_no=inv_no,
            subtotal_amount=float(subtotal),
            discount_amount=0,
            tax_amount=0,
            total_amount=float(subtotal),
            payment_status="CHUA_TT",
            created_by=created_by,
            note=f"Hóa đơn lưu trú thú #{stay['pet_id']}",
            pet_stay_id=stay_id,
        )
        for svc_id, qty, price in boarding_lines:
            invoice_item_dao.create(
                invoice_id=inv_id,
                service_id=svc_id,
                quantity=int(qty),
                unit_price=float(price),
                pet_id=int(stay["pet_id"]),
                item_type="SERVICE",
            )
        invoice_service.sync_invoice_totals(int(inv_id))
        log_admin("CREATE_STAY_INVOICE", entity="invoice", entity_id=int(inv_id))
        return int(inv_id)
    except MySQLError as exc:
        raise BoardingError(f"Không thể tạo hóa đơn: {exc}") from exc


def add_service_to_stay_invoice(stay_id: int, service_id: int, quantity: int = 1) -> None:
    inv = invoice_dao.get_by_pet_stay(stay_id)
    if inv is None:
        raise BoardingError("Chưa có hóa đơn. Hãy tạo hóa đơn trước.")
    if inv.get("payment_status") == "DA_TT":
        raise BoardingError("Hóa đơn đã thanh toán.")
    svc = service_dao.get_by_id(service_id)
    if svc is None:
        raise BoardingError("Dịch vụ không tồn tại.")
    stay = pet_stay_dao.get_by_id(stay_id)
    pet_id = int(stay["pet_id"]) if stay else None
    invoice_item_dao.create(
        invoice_id=int(inv["id"]),
        service_id=service_id,
        quantity=quantity,
        unit_price=float(svc.price),
        pet_id=pet_id,
        item_type="SERVICE",
    )
    invoice_service._recalc_totals_from_items(int(inv["id"]))


def add_product_to_stay_invoice(stay_id: int, product_id: int, quantity: int = 1) -> None:
    inv = invoice_dao.get_by_pet_stay(stay_id)
    if inv is None:
        raise BoardingError("Chưa có hóa đơn.")
    invoice_service.add_product_to_invoice(int(inv["id"]), product_id, quantity)
