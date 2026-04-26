"""User service: dang ky, quan tri user (Admin)."""
from __future__ import annotations

import re

from mysql.connector import Error as MySQLError

from ..dao import role_dao, user_dao
from ..activity_log import log_admin
from ..security import hash_password
from ..session import Session


class UserError(Exception):
    pass


_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,50}$")
_PHONE_RE = re.compile(r"^[0-9+() .-]{6,20}$")


def _require_admin() -> None:
    if not Session.is_admin():
        raise UserError("Chỉ Admin mới được thực hiện chức năng này.")


def list_roles() -> list[dict]:
    return list(role_dao.list_all())


def list_users(active_only: bool = False) -> list[dict]:
    _require_admin()
    return user_dao.list_all_with_role(active_only=active_only)


def register_employee(username: str, password: str, full_name: str, phone: str | None = None) -> int:
    """Dang ky tai khoan nhan vien (EMPLOYEE)."""
    username = (username or "").strip()
    password = password or ""
    full_name = (full_name or "").strip()
    phone = (phone or "").strip() or None

    if not username or not password or not full_name:
        raise UserError("Vui lòng nhập đầy đủ thông tin.")
    if not _USERNAME_RE.match(username):
        raise UserError("Username chỉ gồm chữ/số và . _ - (3–50 ký tự).")
    if len(password) < 6:
        raise UserError("Mật khẩu phải có ít nhất 6 ký tự.")
    if phone and not _PHONE_RE.match(phone):
        raise UserError("Số điện thoại không hợp lệ.")

    role = role_dao.get_by_name("EMPLOYEE")
    if role is None:
        raise UserError("Thiếu role EMPLOYEE trong database. Hãy chạy init_db.py.")

    try:
        return user_dao.create(
            role_id=int(role["id"]),
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            phone=phone,
        )
    except MySQLError as exc:
        if "Duplicate" in str(exc) or "duplicate" in str(exc):
            raise UserError("Username đã tồn tại.") from exc
        raise


def admin_create_user(role_name: str, username: str, password: str, full_name: str, phone: str | None = None) -> int:
    _require_admin()
    role_name = (role_name or "").strip().upper()
    username = (username or "").strip()
    password = password or ""
    full_name = (full_name or "").strip()
    phone = (phone or "").strip() or None

    if role_name not in ("ADMIN", "EMPLOYEE"):
        raise UserError("Role không hợp lệ.")
    if not username or not password or not full_name:
        raise UserError("Vui lòng nhập đầy đủ thông tin.")
    if not _USERNAME_RE.match(username):
        raise UserError("Username chỉ gồm chữ/số và . _ - (3–50 ký tự).")
    if len(password) < 6:
        raise UserError("Mật khẩu phải có ít nhất 6 ký tự.")
    if phone and not _PHONE_RE.match(phone):
        raise UserError("Số điện thoại không hợp lệ.")

    role = role_dao.get_by_name(role_name)
    if role is None:
        raise UserError(f"Thiếu role {role_name} trong database.")

    try:
        new_id = user_dao.create(
            role_id=int(role["id"]),
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            phone=phone,
        )
        log_admin(
            "CREATE_USER",
            entity="user",
            entity_id=int(new_id),
            message=f"Tạo tài khoản '{username}' ({role_name})",
            extra={"role": role_name, "full_name": full_name},
        )
        return new_id
    except MySQLError as exc:
        if "Duplicate" in str(exc) or "duplicate" in str(exc):
            raise UserError("Username đã tồn tại.") from exc
        raise


def admin_update_user(user_id: int, full_name: str, phone: str | None = None) -> None:
    _require_admin()
    full_name = (full_name or "").strip()
    phone = (phone or "").strip() or None
    if not full_name:
        raise UserError("Vui lòng nhập họ tên.")
    if phone and not _PHONE_RE.match(phone):
        raise UserError("Số điện thoại không hợp lệ.")
    user_dao.update_profile(user_id, full_name, phone)
    log_admin(
        "UPDATE_USER",
        entity="user",
        entity_id=int(user_id),
        message="Cập nhật thông tin tài khoản",
        extra={"full_name": full_name, "phone": phone},
    )


def admin_set_role(user_id: int, role_name: str) -> None:
    _require_admin()
    role_name = (role_name or "").strip().upper()
    if role_name not in ("ADMIN", "EMPLOYEE"):
        raise UserError("Role không hợp lệ.")
    role = role_dao.get_by_name(role_name)
    if role is None:
        raise UserError(f"Thiếu role {role_name} trong database.")
    user_dao.update_role(user_id, int(role["id"]))
    log_admin(
        "SET_USER_ROLE",
        entity="user",
        entity_id=int(user_id),
        message=f"Đổi role -> {role_name}",
    )


def admin_set_active(user_id: int, is_active: bool) -> None:
    _require_admin()
    user_dao.set_active(user_id, is_active=is_active)
    log_admin(
        "SET_USER_ACTIVE",
        entity="user",
        entity_id=int(user_id),
        message=("Kích hoạt tài khoản" if is_active else "Khoá tài khoản"),
    )


def admin_reset_password(user_id: int, new_password: str) -> None:
    _require_admin()
    new_password = new_password or ""
    if len(new_password) < 6:
        raise UserError("Mật khẩu phải có ít nhất 6 ký tự.")
    user_dao.update_password(user_id, hash_password(new_password))
    log_admin("RESET_USER_PASSWORD", entity="user", entity_id=int(user_id), message="Reset mật khẩu")

