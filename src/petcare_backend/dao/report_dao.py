"""DAO cho bao cao - doanh thu, dich vu, khach hang.

Moi query deu chi tinh tren hoa don da thanh toan (payment_status = 'DA_TT')
de con so phan anh dung doanh thu thuc te.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ..db import fetch_all, fetch_one


# ---------------------------------------------------------------------------
# Doanh thu
# ---------------------------------------------------------------------------

def revenue_by_day(start: date, end: date) -> list[dict[str, Any]]:
    """Doanh thu theo tung ngay trong khoang [start, end] (bao gom 2 dau mut).

    Tra ve: [{revenue_date, invoice_count, total_revenue}, ...]
    Chi ke cac ngay co hoa don da thanh toan.
    """
    sql = """
    SELECT DATE(i.issued_at)                AS revenue_date,
           COUNT(*)                         AS invoice_count,
           COALESCE(SUM(i.total_amount), 0) AS total_revenue
    FROM   invoice i
    WHERE  i.payment_status = 'DA_TT'
      AND  DATE(i.issued_at) BETWEEN %s AND %s
    GROUP  BY DATE(i.issued_at)
    ORDER  BY revenue_date
    """
    return fetch_all(sql, (start, end))


def revenue_by_month(start: date, end: date) -> list[dict[str, Any]]:
    """Doanh thu gop theo (nam, thang) trong khoang [start, end].

    Tra ve: [{year, month, invoice_count, total_revenue}, ...]
    """
    sql = """
    SELECT YEAR(i.issued_at)                AS year,
           MONTH(i.issued_at)               AS month,
           COUNT(*)                         AS invoice_count,
           COALESCE(SUM(i.total_amount), 0) AS total_revenue
    FROM   invoice i
    WHERE  i.payment_status = 'DA_TT'
      AND  DATE(i.issued_at) BETWEEN %s AND %s
    GROUP  BY YEAR(i.issued_at), MONTH(i.issued_at)
    ORDER  BY year, month
    """
    return fetch_all(sql, (start, end))


def revenue_summary(start: date, end: date) -> dict[str, Any]:
    """Tong hop doanh thu trong khoang [start, end]."""
    sql = """
    SELECT COUNT(*)                         AS invoice_count,
           COALESCE(SUM(i.total_amount), 0) AS total_revenue,
           COALESCE(AVG(i.total_amount), 0) AS avg_invoice
    FROM   invoice i
    WHERE  i.payment_status = 'DA_TT'
      AND  DATE(i.issued_at) BETWEEN %s AND %s
    """
    row = fetch_one(sql, (start, end))
    return row or {"invoice_count": 0, "total_revenue": 0, "avg_invoice": 0}


def revenue_on_date(day: date) -> dict[str, Any]:
    """Doanh thu cua 1 ngay cu the."""
    return revenue_summary(day, day)


# ---------------------------------------------------------------------------
# Dich vu pho bien
# ---------------------------------------------------------------------------

def top_services_by_quantity(
    limit: int,
    start: date | None = None,
    end: date | None = None,
) -> list[dict[str, Any]]:
    """Top dich vu theo so luong ban ra. Chi tinh tren hoa don DA_TT."""
    where_date = ""
    params: list[Any] = []
    if start is not None and end is not None:
        where_date = " AND DATE(i.issued_at) BETWEEN %s AND %s"
        params.extend([start, end])

    sql = f"""
    SELECT s.id                                  AS service_id,
           s.name                                AS service_name,
           COALESCE(SUM(ii.quantity), 0)         AS total_sold,
           COALESCE(SUM(ii.line_total), 0)       AS total_revenue
    FROM   service s
    LEFT   JOIN invoice_item ii ON ii.service_id = s.id
    LEFT   JOIN invoice      i  ON i.id = ii.invoice_id
                                 AND i.payment_status = 'DA_TT'
                                 {where_date}
    GROUP  BY s.id, s.name
    HAVING total_sold > 0
    ORDER  BY total_sold DESC, total_revenue DESC
    LIMIT  %s
    """
    params.append(limit)
    return fetch_all(sql, params)


def top_services_by_revenue(
    limit: int,
    start: date | None = None,
    end: date | None = None,
) -> list[dict[str, Any]]:
    """Top dich vu theo doanh thu dong gop."""
    where_date = ""
    params: list[Any] = []
    if start is not None and end is not None:
        where_date = " AND DATE(i.issued_at) BETWEEN %s AND %s"
        params.extend([start, end])

    sql = f"""
    SELECT s.id                                  AS service_id,
           s.name                                AS service_name,
           COALESCE(SUM(ii.quantity), 0)         AS total_sold,
           COALESCE(SUM(ii.line_total), 0)       AS total_revenue
    FROM   service s
    LEFT   JOIN invoice_item ii ON ii.service_id = s.id
    LEFT   JOIN invoice      i  ON i.id = ii.invoice_id
                                 AND i.payment_status = 'DA_TT'
                                 {where_date}
    GROUP  BY s.id, s.name
    HAVING total_revenue > 0
    ORDER  BY total_revenue DESC, total_sold DESC
    LIMIT  %s
    """
    params.append(limit)
    return fetch_all(sql, params)


# ---------------------------------------------------------------------------
# Khach hang
# ---------------------------------------------------------------------------

def count_customers() -> int:
    row = fetch_one("SELECT COUNT(*) AS n FROM customer")
    return int(row["n"]) if row else 0


def count_new_customers_between(start: date, end: date) -> int:
    """Dem khach hang moi tao trong khoang [start, end]."""
    sql = """
    SELECT COUNT(*) AS n
    FROM   customer
    WHERE  DATE(created_at) BETWEEN %s AND %s
    """
    row = fetch_one(sql, (start, end))
    return int(row["n"]) if row else 0


def vip_customers_by_spending(
    limit: int,
    start: date | None = None,
    end: date | None = None,
) -> list[dict[str, Any]]:
    """Top khach VIP theo tong chi tieu (hoa don DA_TT)."""
    where_date = ""
    params: list[Any] = []
    if start is not None and end is not None:
        where_date = " AND DATE(i.issued_at) BETWEEN %s AND %s"
        params.extend([start, end])

    sql = f"""
    SELECT c.id                                  AS customer_id,
           c.full_name                           AS full_name,
           c.phone                               AS phone,
           COUNT(i.id)                           AS invoice_count,
           COALESCE(SUM(i.total_amount), 0)      AS total_spent
    FROM   customer c
    JOIN   appointment a ON a.customer_id = c.id
    JOIN   invoice     i ON i.appointment_id = a.id
                         AND i.payment_status = 'DA_TT'
                         {where_date}
    GROUP  BY c.id, c.full_name, c.phone
    ORDER  BY total_spent DESC, invoice_count DESC
    LIMIT  %s
    """
    params.append(limit)
    return fetch_all(sql, params)


# ---------------------------------------------------------------------------
# So lieu nhanh cho dashboard
# ---------------------------------------------------------------------------

def count_pets() -> int:
    row = fetch_one("SELECT COUNT(*) AS n FROM pet")
    return int(row["n"]) if row else 0


def count_appointments_on_date(day: date) -> int:
    sql = "SELECT COUNT(*) AS n FROM appointment WHERE DATE(scheduled_at) = %s"
    row = fetch_one(sql, (day,))
    return int(row["n"]) if row else 0


def count_pending_appointments() -> int:
    sql = "SELECT COUNT(*) AS n FROM appointment WHERE status IN ('CHO_XU_LY','DANG_THUC_HIEN')"
    row = fetch_one(sql)
    return int(row["n"]) if row else 0


def count_unpaid_invoices() -> int:
    sql = "SELECT COUNT(*) AS n FROM invoice WHERE payment_status = 'CHUA_TT'"
    row = fetch_one(sql)
    return int(row["n"]) if row else 0


def now() -> datetime:
    """Thoi diem hien tai theo DB (dung cho test - helper khong bat buoc)."""
    row = fetch_one("SELECT NOW() AS t")
    return row["t"] if row else datetime.now()
