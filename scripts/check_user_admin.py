"""Smoke test cho dang ky + admin CRUD user.

Chay:
  python scripts/check_user_admin.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from petcare_backend.services import auth_service, user_service  # noqa: E402
from petcare_backend.session import Session  # noqa: E402


def main() -> int:
    print("=" * 60)
    print("PETCARE - USER ADMIN SMOKE TEST")
    print("=" * 60)

    # Login admin
    admin = auth_service.login("admin", "admin123")
    assert admin.is_admin
    print(f"[OK] Login admin -> id={admin.id}")

    # Admin create user
    username = "emp_test_01"
    try:
        uid = user_service.admin_create_user(
            role_name="EMPLOYEE",
            username=username,
            password="123456",
            full_name="Employee Test",
            phone="0900001111",
        )
        print(f"[OK] Admin created user {username} -> id={uid}")
    except user_service.UserError as exc:
        print(f"[!] Create user skipped: {exc}")

    # List users
    users = user_service.list_users()
    print(f"[OK] list_users -> {len(users)} rows")

    # Lock/unlock newest employee found
    target = next((u for u in users if u["username"] == username), None)
    if target:
        tid = int(target["id"])
        user_service.admin_set_active(tid, is_active=False)
        print("[OK] Locked user")
        user_service.admin_set_active(tid, is_active=True)
        print("[OK] Unlocked user")
        user_service.admin_reset_password(tid, "123456")
        print("[OK] Reset password")

    auth_service.logout()
    assert Session.current() is None
    print("[OK] Logout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

