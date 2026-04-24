"""Auth service - dang nhap, dang xuat, doi mat khau."""
from __future__ import annotations

from ..dao import user_dao
from ..models import User
from ..security import hash_password, verify_password
from ..session import Session


class AuthError(Exception):
    """Loi nghiep vu cua AuthService - de UI bat va hien thong bao."""


_MIN_PASSWORD_LEN = 6


def login(username: str, password: str) -> User:
    """Xac thuc tai khoan. Tra ve User va luu vao Session."""
    username = (username or "").strip()
    password = password or ""

    if not username or not password:
        raise AuthError("Vui lòng nhập tên đăng nhập và mật khẩu.")

    row = user_dao.find_by_username(username)
    if row is None:
        raise AuthError("Tên đăng nhập hoặc mật khẩu không đúng.")

    if not row.get("is_active"):
        raise AuthError("Tài khoản đã bị khoá. Liên hệ quản trị viên.")

    if not verify_password(password, row["password_hash"]):
        raise AuthError("Tên đăng nhập hoặc mật khẩu không đúng.")

    user = User(
        id=row["id"],
        role_id=row["role_id"],
        role_name=row["role_name"],
        username=row["username"],
        full_name=row["full_name"],
        phone=row.get("phone"),
        is_active=bool(row["is_active"]),
    )
    Session.set(user)
    return user


def logout() -> None:
    Session.clear()


def change_password(user_id: int, old_password: str, new_password: str, confirm_password: str) -> None:
    if not old_password or not new_password:
        raise AuthError("Vui lòng nhập đầy đủ thông tin.")
    if new_password != confirm_password:
        raise AuthError("Mật khẩu xác nhận không khớp.")
    if len(new_password) < _MIN_PASSWORD_LEN:
        raise AuthError(f"Mật khẩu mới phải có ít nhất {_MIN_PASSWORD_LEN} ký tự.")
    if new_password == old_password:
        raise AuthError("Mật khẩu mới phải khác mật khẩu hiện tại.")

    current_hash = user_dao.get_password_hash(user_id)
    if current_hash is None:
        raise AuthError("Không tìm thấy tài khoản.")

    if not verify_password(old_password, current_hash):
        raise AuthError("Mật khẩu hiện tại không đúng.")

    user_dao.update_password(user_id, hash_password(new_password))
