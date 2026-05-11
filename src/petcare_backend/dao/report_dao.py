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
    """Top khach VIP theo tong chi tieu (hoa don DA_TT, ca dich vu lan ban le)."""
    where_date = ""
    params: list[Any] = []
    if start is not None and end is not None:
        where_date = " AND DATE(i.issued_at) BETWEEN %s AND %s"
        params.extend([start, end])

    # Lay customer_id cua hoa don: uu tien cot i.customer_id (hoa don ban le hoac
    # da copy tu lich hen), neu khong co thi fallback sang appointment.customer_id.
    sql = f"""
    SELECT c.id                                  AS customer_id,
           c.full_name                           AS full_name,
           c.phone                               AS phone,
           COUNT(i.id)                           AS invoice_count,
           COALESCE(SUM(i.total_amount), 0)      AS total_spent
    FROM   customer c
    JOIN   invoice   i ON COALESCE(i.customer_id,
                            (SELECT a.customer_id FROM appointment a WHERE a.id = i.appointment_id)
                         ) = c.id
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


# ---------------------------------------------------------------------------
# Thong ke nhan vien (User - Appointment, User - Invoice)
# ---------------------------------------------------------------------------

def employee_performance(
    start: date | None = None,
    end: date | None = None,
) -> list[dict[str, Any]]:
    """Bao cao hieu suat tung nhan vien (role = EMPLOYEE).

    Voi moi nhan vien, tinh trong khoang [start, end]:
      - appointment_count        : tong lich hen duoc phan cong
      - appointment_done         : so lich hoan thanh
      - appointment_in_progress  : so lich dang thuc hien
      - appointment_pending      : so lich cho xu ly
      - service_revenue          : doanh thu HD dich vu (DA_TT) tu lich hen do
                                   nhan vien nay phu trach
      - retail_revenue           : doanh thu HD ban le (DA_TT) do nhan vien
                                   nay lap (created_by)
      - invoice_count            : tong so HD (ca dich vu va ban le) ma nhan
                                   vien dong gop (phu trach hoac tao)
      - total_revenue            = service_revenue + retail_revenue

    Sap xep giam dan theo total_revenue.
    """
    where_date_appt = ""
    where_date_inv = ""
    params: list[Any] = []

    if start is not None and end is not None:
        where_date_appt = " AND DATE(a.scheduled_at) BETWEEN %s AND %s"
        where_date_inv = " AND DATE(i.issued_at) BETWEEN %s AND %s"

    # SQL su dung cac sub-select theo employee_id de gop. De don gian va du
    # chuc nang, ta query 3 doan rieng roi join trong service-layer. Tuy nhien
    # gop trong 1 query SQL hieu qua hon. Dung sub-select voi user.id.

    appt_params: list[Any] = []
    inv_service_params: list[Any] = []
    inv_retail_params: list[Any] = []
    if start is not None and end is not None:
        appt_params = [start, end]
        inv_service_params = [start, end]
        inv_retail_params = [start, end]

    sql = f"""
    SELECT
        u.id          AS employee_id,
        u.username,
        u.full_name,
        u.phone,
        u.is_active,
        COALESCE((
            SELECT COUNT(*) FROM appointment a
            WHERE a.employee_id = u.id {where_date_appt}
        ), 0) AS appointment_count,
        COALESCE((
            SELECT COUNT(*) FROM appointment a
            WHERE a.employee_id = u.id AND a.status = 'HOAN_THANH' {where_date_appt}
        ), 0) AS appointment_done,
        COALESCE((
            SELECT COUNT(*) FROM appointment a
            WHERE a.employee_id = u.id AND a.status = 'DANG_THUC_HIEN' {where_date_appt}
        ), 0) AS appointment_in_progress,
        COALESCE((
            SELECT COUNT(*) FROM appointment a
            WHERE a.employee_id = u.id AND a.status = 'CHO_XU_LY' {where_date_appt}
        ), 0) AS appointment_pending,
        COALESCE((
            SELECT SUM(i.total_amount)
            FROM   invoice i
            JOIN   appointment a ON a.id = i.appointment_id
            WHERE  a.employee_id = u.id
              AND  i.payment_status = 'DA_TT'
              AND  i.invoice_type = 'SERVICE'
              {where_date_inv}
        ), 0) AS service_revenue,
        COALESCE((
            SELECT SUM(i.total_amount)
            FROM   invoice i
            WHERE  i.created_by = u.id
              AND  i.payment_status = 'DA_TT'
              AND  i.invoice_type = 'RETAIL'
              {where_date_inv}
        ), 0) AS retail_revenue,
        COALESCE((
            SELECT COUNT(DISTINCT i.id) FROM invoice i
            LEFT JOIN appointment a ON a.id = i.appointment_id
            WHERE (i.created_by = u.id OR a.employee_id = u.id)
              {where_date_inv}
        ), 0) AS invoice_count
    FROM  user u
    JOIN  role r ON r.id = u.role_id
    WHERE r.name = 'EMPLOYEE'
    """

    # Truyen params cho cac sub-select theo dung thu tu xuat hien
    if where_date_appt:
        # 4 sub-select tren appointment, moi cai can [start, end]
        params.extend(appt_params * 4)
    if where_date_inv:
        # 3 sub-select tren invoice (service revenue, retail revenue, invoice count)
        params.extend(inv_service_params)
        params.extend(inv_retail_params)
        params.extend(inv_retail_params)

    rows = fetch_all(sql, params)
    for r in rows:
        r["total_revenue"] = (r.get("service_revenue") or 0) + (r.get("retail_revenue") or 0)
    rows.sort(key=lambda x: float(x["total_revenue"] or 0), reverse=True)
    return rows


def employee_recent_appointments(
    employee_id: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Lich hen gan day cua 1 nhan vien (de dialog chi tiet)."""
    sql = """
    SELECT a.id              AS appointment_id,
           a.scheduled_at,
           a.status,
           c.full_name        AS customer_name,
           (SELECT GROUP_CONCAT(s.name SEPARATOR ', ')
              FROM appointment_service aps
              JOIN service s ON s.id = aps.service_id
             WHERE aps.appointment_id = a.id) AS service_name
    FROM   appointment a
    JOIN   customer    c ON c.id = a.customer_id
    WHERE  a.employee_id = %s
    ORDER  BY a.scheduled_at DESC, a.id DESC
    LIMIT  %s
    """
    return fetch_all(sql, (int(employee_id), int(limit)))


def employee_recent_invoices(
    employee_id: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Hoa don gan day do nhan vien lap (created_by) hoac phu trach lich hen."""
    sql = """
    SELECT i.id               AS invoice_id,
           i.invoice_no,
           i.issued_at,
           i.invoice_type,
           i.total_amount,
           i.payment_status,
           COALESCE(c_inv.full_name, c_appt.full_name) AS customer_name,
           CASE WHEN i.created_by = %s THEN 1 ELSE 0 END AS is_creator,
           CASE WHEN a.employee_id = %s THEN 1 ELSE 0 END AS is_assignee
    FROM   invoice i
    LEFT JOIN appointment a   ON a.id  = i.appointment_id
    LEFT JOIN customer c_inv  ON c_inv.id  = i.customer_id
    LEFT JOIN customer c_appt ON c_appt.id = a.customer_id
    WHERE  i.created_by = %s OR a.employee_id = %s
    ORDER  BY i.issued_at DESC, i.id DESC
    LIMIT  %s
    """
    return fetch_all(
        sql,
        (int(employee_id), int(employee_id), int(employee_id), int(employee_id), int(limit)),
    )
