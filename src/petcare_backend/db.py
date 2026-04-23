"""Quan ly ket noi MySQL - connection pool + helper query."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, Iterator, Sequence

import mysql.connector
from mysql.connector import pooling
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.cursor import MySQLCursor

from .config import DB_CONFIG

_POOL: pooling.MySQLConnectionPool | None = None


def _get_pool() -> pooling.MySQLConnectionPool:
    global _POOL
    if _POOL is None:
        _POOL = pooling.MySQLConnectionPool(
            pool_name="petcare_pool",
            pool_size=5,
            host=DB_CONFIG.host,
            port=DB_CONFIG.port,
            user=DB_CONFIG.user,
            password=DB_CONFIG.password,
            database=DB_CONFIG.database,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
        )
    return _POOL


@contextmanager
def get_connection() -> Iterator[MySQLConnectionAbstract]:
    """Lay 1 connection tu pool. Tu dong tra ve khi ra khoi with."""
    conn = _get_pool().get_connection()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_cursor(dictionary: bool = True) -> Iterator[tuple[MySQLConnectionAbstract, MySQLCursor]]:
    """Lay connection + cursor. Tu commit khi thoat binh thuong, rollback neu co exception."""
    with get_connection() as conn:
        cur = conn.cursor(dictionary=dictionary)
        try:
            yield conn, cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


# ---------- Helper nhanh ----------

def fetch_all(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    with get_cursor() as (_, cur):
        cur.execute(sql, params or ())
        return list(cur.fetchall())


def fetch_one(sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
    with get_cursor() as (_, cur):
        cur.execute(sql, params or ())
        row = cur.fetchone()
        return dict(row) if row else None


def execute(sql: str, params: Sequence[Any] | None = None) -> int:
    """Tra ve lastrowid (neu INSERT) hoac rowcount."""
    with get_cursor() as (_, cur):
        cur.execute(sql, params or ())
        return cur.lastrowid if cur.lastrowid else cur.rowcount


def execute_many(sql: str, seq_params: Iterable[Sequence[Any]]) -> int:
    with get_cursor() as (_, cur):
        cur.executemany(sql, list(seq_params))
        return cur.rowcount


def ping() -> bool:
    """Kiem tra ket noi DB - tra ve True neu OK."""
    try:
        with get_connection() as conn:
            conn.ping(reconnect=True, attempts=1, delay=0)
            return True
    except mysql.connector.Error:
        return False
