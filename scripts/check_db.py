"""Smoke test ket noi MySQL + liet ke bang.

Chay:  python scripts/check_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from petcare_backend.config import DB_CONFIG  # noqa: E402
from petcare_backend.db import fetch_all, ping  # noqa: E402


def main() -> int:
    print("=" * 60)
    print(" PETCARE - DB CONNECTION CHECK")
    print("=" * 60)
    print(f" Host    : {DB_CONFIG.host}:{DB_CONFIG.port}")
    print(f" User    : {DB_CONFIG.user}")
    print(f" Database: {DB_CONFIG.database}")
    print("-" * 60)

    if not ping():
        print(" [X] Khong ket noi duoc DB. Kiem tra:")
        print("     - MySQL service da chay chua?")
        print("     - File .env (DB_HOST/PORT/USER/PASSWORD/NAME) dung chua?")
        print("     - Da chay 'python scripts/init_db.py' chua?")
        return 1

    print(" [OK] Ket noi MySQL thanh cong.")

    try:
        tables = fetch_all("SHOW TABLES")
    except Exception as exc:  # pragma: no cover - thong bao loi than thien
        print(f" [X] Khong list duoc bang: {exc}")
        return 2

    if not tables:
        print(" [!] DB rong - hay chay 'python scripts/init_db.py'.")
        return 3

    print(f" [OK] Tim thay {len(tables)} bang:")
    for row in tables:
        name = next(iter(row.values()))
        try:
            count_row = fetch_all(f"SELECT COUNT(*) AS c FROM `{name}`")
            count = count_row[0]["c"] if count_row else 0
        except Exception:
            count = "?"
        print(f"     - {name:<25} ({count} dong)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
