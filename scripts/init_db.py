"""Script tao database + chay schema/seed + reset mat khau admin, nv01.

Cach chay (tu thu muc goc project):
    python scripts/init_db.py              # chay schema + seed
    python scripts/init_db.py --schema     # chi chay schema
    python scripts/init_db.py --seed       # chi chay seed
    python scripts/init_db.py --reset-pw   # seed xong + re-hash mat khau bang bcrypt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from petcare_backend.config import DB_CONFIG  # noqa: E402
from petcare_backend.security import hash_password  # noqa: E402

SCHEMA_FILE = ROOT / "database" / "schema.sql"
SEED_FILE = ROOT / "database" / "seed.sql"


def _exec_sql_file(path: Path, use_db: bool) -> None:
    sql = path.read_text(encoding="utf-8")
    kwargs = dict(
        host=DB_CONFIG.host,
        port=DB_CONFIG.port,
        user=DB_CONFIG.user,
        password=DB_CONFIG.password,
        autocommit=True,
        charset="utf8mb4",
    )
    if use_db:
        kwargs["database"] = DB_CONFIG.database

    conn = mysql.connector.connect(**kwargs)
    try:
        cur = conn.cursor()
        for statement in _split_sql(sql):
            cur.execute(statement)
            while cur.nextset():
                pass
        cur.close()
    finally:
        conn.close()


def _split_sql(sql: str) -> list[str]:
    """Tach file SQL thanh nhieu cau lenh. Loai bo comment va dong trong."""
    cleaned_lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)
    return [s.strip() for s in cleaned.split(";") if s.strip()]


def reset_default_passwords() -> None:
    """Sinh lai password_hash bcrypt cho admin / nv01."""
    conn = mysql.connector.connect(
        host=DB_CONFIG.host,
        port=DB_CONFIG.port,
        user=DB_CONFIG.user,
        password=DB_CONFIG.password,
        database=DB_CONFIG.database,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE user SET password_hash=%s WHERE username=%s",
            (hash_password("admin123"), "admin"),
        )
        cur.execute(
            "UPDATE user SET password_hash=%s WHERE username=%s",
            (hash_password("123456"), "nv01"),
        )
        cur.close()
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Init Petcare MySQL database")
    parser.add_argument("--schema", action="store_true", help="Chi chay schema.sql")
    parser.add_argument("--seed", action="store_true", help="Chi chay seed.sql")
    parser.add_argument(
        "--reset-pw",
        action="store_true",
        help="Sau khi seed, bam lai mat khau admin / nv01 bang bcrypt",
    )
    args = parser.parse_args()

    run_schema = args.schema or not (args.seed)
    run_seed = args.seed or not (args.schema)

    if run_schema:
        print(f"[1/2] Chay schema: {SCHEMA_FILE}")
        _exec_sql_file(SCHEMA_FILE, use_db=False)
        print("     -> OK")

    if run_seed:
        print(f"[2/2] Chay seed:   {SEED_FILE}")
        _exec_sql_file(SEED_FILE, use_db=True)
        print("     -> OK")

    if args.reset_pw or run_seed:
        print("[+]   Reset password (bcrypt) cho admin / nv01")
        reset_default_passwords()
        print("     -> OK")

    print("\nHoan tat. Tai khoan mac dinh:")
    print("  admin / admin123")
    print("  nv01  / 123456")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
