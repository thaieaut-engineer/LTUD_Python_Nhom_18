"""Smoke test AuthService - thu login admin/admin123, sai password, doi mat khau.

Chay:  python scripts/check_auth.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from petcare_backend.services import auth_service  # noqa: E402
from petcare_backend.session import Session  # noqa: E402


def main() -> int:
    print("=" * 60)
    print(" PETCARE - AUTH SMOKE TEST")
    print("=" * 60)

    # 1. Login dung
    try:
        u = auth_service.login("admin", "admin123")
        print(f" [OK] Login admin/admin123 -> id={u.id}, role={u.role_name}, name={u.full_name}")
    except auth_service.AuthError as exc:
        print(f" [X]  Login admin that bai: {exc}")
        print("       -> Hay chay 'python scripts/init_db.py' de seed lai.")
        return 1

    assert Session.current() is not None
    assert Session.is_admin()

    # 2. Sai password
    try:
        auth_service.login("admin", "wrong-pass")
        print(" [X] Login sai password ma van pass - LOI logic")
        return 2
    except auth_service.AuthError as exc:
        print(f" [OK] Sai password -> bao loi: {exc}")

    # 3. Login nv01
    try:
        u2 = auth_service.login("nv01", "123456")
        print(f" [OK] Login nv01/123456 -> id={u2.id}, role={u2.role_name}")
    except auth_service.AuthError as exc:
        print(f" [X] Login nv01 that bai: {exc}")
        return 3

    # 4. Doi mat khau (nv01 -> roi doi lai)
    try:
        auth_service.change_password(u2.id, "123456", "newpass1", "newpass1")
        print(" [OK] Doi mat khau nv01 -> 'newpass1' thanh cong")
        auth_service.change_password(u2.id, "newpass1", "123456", "123456")
        print(" [OK] Doi nguoc lai '123456' thanh cong")
    except auth_service.AuthError as exc:
        print(f" [X] Doi mat khau that bai: {exc}")
        return 4

    # 5. Logout
    auth_service.logout()
    assert Session.current() is None
    print(" [OK] Logout thanh cong (Session da clear)")

    print("\nTAT CA TEST PASS - AuthService san sang dung.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
