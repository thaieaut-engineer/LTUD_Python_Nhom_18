"""Appointment service (C1-C3): tao lich hen, cap nhat trang thai, xem danh sach.

Mot appointment co the gom nhieu pet cua cung 1 khach hang, moi pet 1 dich vu rieng
(luu vao appointment_service.pet_id).
"""
from __future__ import annotations

from datetime import datetime

from mysql.connector import Error as MySQLError

from ..activity_log import log_admin
from ..dao import appointment_dao, appointment_service_dao, service_dao, user_dao
from ..session import Session


class AppointmentError(Exception):
    pass


STATUS_LABEL_TO_DB = {
    "Chờ xử lý": "CHO_XU_LY",
    "Đang thực hiện": "DANG_THUC_HIEN",
    "Hoàn thành": "HOAN_THANH",
    "Hủy": "HUY",
}

STATUS_DB_TO_LABEL = {v: k for k, v in STATUS_LABEL_TO_DB.items()}


def create_appointment_multi(
    customer_id: int,
    scheduled_at: datetime,
    plan: list[tuple[int, int, int]],
) -> int:
    """Tao 1 appointment cho 1 khach hang voi nhieu pet + dich vu.

    plan: list of tuple (pet_id, service_id, quantity).
    Neu plan chi co 1 pet, appointment.pet_id se duoc set = pet do.
    Neu plan co nhieu pet khac nhau, appointment.pet_id = NULL (dung appointment_service.pet_id).
    Tra ve appointment_id.
    """
    if not customer_id:
        raise AppointmentError("Vui lòng chọn khách hàng.")
    if scheduled_at is None:
        raise AppointmentError("Vui lòng chọn thời gian.")
    if not plan:
        raise AppointmentError("Vui lòng chọn ít nhất một thú cưng + dịch vụ.")

    for pet_id, service_id, quantity in plan:
        if not pet_id:
            raise AppointmentError("Thiếu thú cưng trong danh sách.")
        if not service_id:
            raise AppointmentError("Thiếu dịch vụ cho một thú cưng.")
        if quantity <= 0:
            raise AppointmentError("Số lượng không hợp lệ.")

    # Cache service price + validate
    prices: dict[int, float] = {}
    for _, service_id, _ in plan:
        if service_id in prices:
            continue
        svc = service_dao.get_by_id(service_id)
        if svc is None:
            raise AppointmentError("Dịch vụ không tồn tại.")
        if not svc.is_active:
            raise AppointmentError(f"Dịch vụ '{svc.name}' đã bị ẩn.")
        prices[service_id] = float(svc.price)

    current = Session.current()
    employee_id = current.id if current else None

    distinct_pets = {p for p, _, _ in plan}
    # Neu chi 1 pet duy nhat, luu vao appointment.pet_id (tien cho bao cao cu)
    single_pet = next(iter(distinct_pets)) if len(distinct_pets) == 1 else None

    try:
        appt_id = appointment_dao.create(
            customer_id=customer_id,
            pet_id=single_pet,
            employee_id=employee_id,
            scheduled_at=scheduled_at,
            status="CHO_XU_LY",
            note=None,
        )
        for pet_id, service_id, quantity in plan:
            appointment_service_dao.insert(
                appointment_id=appt_id,
                service_id=service_id,
                quantity=int(quantity),
                unit_price=prices[service_id],
                pet_id=pet_id,
            )
        return appt_id
    except MySQLError as exc:
        raise AppointmentError(f"Không thể tạo lịch hẹn: {exc}") from exc


def create_appointment(
    customer_id: int,
    pet_id: int,
    service_id: int,
    scheduled_at: datetime,
    quantity: int = 1,
) -> int:
    """Legacy API: tao 1 appointment cho 1 pet + 1 service."""
    return create_appointment_multi(
        customer_id=customer_id,
        scheduled_at=scheduled_at,
        plan=[(pet_id, service_id, quantity)],
    )


def _decorate(rows: list[dict]) -> list[dict]:
    for r in rows:
        r["status_label"] = STATUS_DB_TO_LABEL.get(r.get("status"), str(r.get("status")))
    return rows


def list_recent(limit: int = 100, *, employee_id: int | None = None) -> list[dict]:
    """Liet ke lich hen gan day. Neu employee_id != None -> chi cua nhan vien do."""
    if employee_id is not None:
        return _decorate(appointment_dao.list_by_employee(int(employee_id), limit=limit))
    return _decorate(appointment_dao.list_recent(limit=limit))


def list_for_employee(employee_id: int, limit: int = 200) -> list[dict]:
    return _decorate(appointment_dao.list_by_employee(int(employee_id), limit=limit))


def list_unassigned(limit: int = 200) -> list[dict]:
    return _decorate(appointment_dao.list_unassigned(limit=limit))


def update_status(appointment_id: int, status_label: str) -> None:
    """Cap nhat trang thai. Cho phep:

    - ADMIN luon duoc cap nhat.
    - EMPLOYEE chi duoc cap nhat lich hen do minh phu trach (employee_id == minh).
    """
    status_db = STATUS_LABEL_TO_DB.get(status_label)
    if not status_db:
        raise AppointmentError("Trạng thái không hợp lệ.")

    current = Session.current()
    if current is not None and not current.is_admin:
        ap = appointment_dao.get_by_id(appointment_id)
        if ap is None:
            raise AppointmentError("Lịch hẹn không tồn tại.")
        if ap.get("employee_id") and int(ap["employee_id"]) != int(current.id):
            raise AppointmentError(
                "Bạn không phải nhân viên phụ trách lịch hẹn này."
            )

    appointment_dao.update_status(appointment_id, status_db)


def update_result_note(appointment_id: int, result: str) -> None:
    current = Session.current()
    if current is not None and not current.is_admin:
        ap = appointment_dao.get_by_id(appointment_id)
        if ap is None:
            raise AppointmentError("Lịch hẹn không tồn tại.")
        if ap.get("employee_id") and int(ap["employee_id"]) != int(current.id):
            raise AppointmentError(
                "Bạn không phải nhân viên phụ trách lịch hẹn này."
            )
    appointment_dao.update_note(appointment_id, (result or "").strip() or None)


def assign_employee(appointment_id: int, employee_id: int | None) -> None:
    """Phan cong nhan vien cham soc cho 1 lich hen. Chi Admin moi duoc thuc hien."""
    if not Session.is_admin():
        raise AppointmentError("Chỉ Admin mới được phân công nhân viên.")

    if employee_id is not None:
        emp = user_dao.get_by_id(int(employee_id))
        if emp is None:
            raise AppointmentError("Không tìm thấy nhân viên.")
        if emp.role_name.upper() != "EMPLOYEE":
            raise AppointmentError("Chỉ phân công cho tài khoản EMPLOYEE.")
        if not emp.is_active:
            raise AppointmentError("Nhân viên này đã bị khoá.")

    ap = appointment_dao.get_by_id(int(appointment_id))
    if ap is None:
        raise AppointmentError("Lịch hẹn không tồn tại.")

    appointment_dao.update_employee(int(appointment_id), int(employee_id) if employee_id else None)
    msg = (
        f"Bỏ phân công lịch hẹn #{appointment_id}"
        if employee_id is None
        else f"Phân công lịch hẹn #{appointment_id} cho user #{employee_id}"
    )
    log_admin(
        "ASSIGN_APPOINTMENT",
        entity="appointment",
        entity_id=int(appointment_id),
        message=msg,
    )
