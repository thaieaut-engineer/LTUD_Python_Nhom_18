"""Backup/Restore MySQL database using mysqldump/mysql.

Chay tu thu muc goc project:
  python scripts/backup_db.py backup  --out backups/petcare.sql
  python scripts/backup_db.py restore --in  backups/petcare.sql

Neu dung .env: script tu doc DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME giong init_db.py.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from petcare_backend.config import DB_CONFIG  # noqa: E402


def _mysql_env() -> dict[str, str]:
    env = dict(os.environ)
    # Tranh prompt password: mysql client se doc MYSQL_PWD
    if DB_CONFIG.password:
        env["MYSQL_PWD"] = DB_CONFIG.password
    return env


def _base_mysql_args() -> list[str]:
    return [
        "-h",
        DB_CONFIG.host,
        "-P",
        str(DB_CONFIG.port),
        "-u",
        DB_CONFIG.user,
    ]


def backup(out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "mysqldump",
        *_base_mysql_args(),
        "--databases",
        DB_CONFIG.database,
        "--routines",
        "--events",
        "--triggers",
        "--single-transaction",
        "--quick",
        "--set-gtid-purged=OFF",
        "--default-character-set=utf8mb4",
    ]

    print("=" * 70)
    print(" PETCARE - BACKUP DB")
    print("=" * 70)
    print(f" Database : {DB_CONFIG.database}")
    print(f" Output   : {out_path}")
    print(f" Command  : {' '.join(cmd)}")
    print("-" * 70)

    with out_path.open("wb") as f:
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=_mysql_env())
    if p.returncode != 0:
        sys.stderr.write(p.stderr.decode("utf-8", errors="replace"))
        return p.returncode

    print("[OK] Backup thanh cong.")
    return 0


def restore(in_path: Path) -> int:
    if not in_path.exists():
        print(f"[X] File khong ton tai: {in_path}")
        return 2

    cmd = [
        "mysql",
        *_base_mysql_args(),
        "--default-character-set=utf8mb4",
    ]

    print("=" * 70)
    print(" PETCARE - RESTORE DB")
    print("=" * 70)
    print(f" Input    : {in_path}")
    print(f" Command  : {' '.join(cmd)}")
    print("-" * 70)

    with in_path.open("rb") as f:
        p = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, env=_mysql_env())
    if p.returncode != 0:
        sys.stderr.write(p.stderr.decode("utf-8", errors="replace"))
        return p.returncode

    print("[OK] Restore thanh cong.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup/Restore Petcare MySQL DB (mysqldump/mysql)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_backup = sub.add_parser("backup", help="Backup database ra file .sql")
    p_backup.add_argument(
        "--out",
        required=False,
        default=None,
        help="Duong dan file output (mac dinh: backups/petcare_YYYYmmdd_HHMMSS.sql)",
    )

    p_restore = sub.add_parser("restore", help="Restore database tu file .sql")
    p_restore.add_argument("--in", dest="inp", required=True, help="Duong dan file .sql can restore")

    args = parser.parse_args()

    if args.cmd == "backup":
        if args.out:
            out_path = Path(args.out)
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = ROOT / "backups" / f"petcare_{ts}.sql"
        return backup(out_path)

    if args.cmd == "restore":
        return restore(Path(args.inp))

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

