"""Report service - thong ke doanh thu, dich vu, khach hang, tong quan dashboard.

Quy uoc:
- `start`, `end` la kieu `date` va BAO GOM ca hai dau mut.
- Doanh thu chi tinh tren hoa don da thanh toan (DA_TT).
- Neu DB khong co du lieu, cac ham van tra ve cau truc rong (0 / []).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from ..dao import report_dao


TopBy = Literal["quantity", "revenue"]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DailyRevenue:
    revenue_date: date
    invoice_count: int
    total_revenue: Decimal


@dataclass(frozen=True)
class MonthlyRevenue:
    year: int
    month: int
    invoice_count: int
    total_revenue: Decimal

    @property
    def label(self) -> str:
        return f"{self.month:02d}/{self.year}"


@dataclass(frozen=True)
class RevenueSummary:
    start: date
    end: date
    invoice_count: int
    total_revenue: Decimal
    avg_invoice: Decimal


@dataclass(frozen=True)
class ServiceStat:
    service_id: int
    service_name: str
    total_sold: int
    total_revenue: Decimal


@dataclass(frozen=True)
class VipCustomer:
    customer_id: int
    full_name: str
    phone: str | None
    invoice_count: int
    total_spent: Decimal


@dataclass(frozen=True)
class CustomerStats:
    total_customers: int
    new_this_month: int
    vip_customers: list[VipCustomer] = field(default_factory=list)


@dataclass(frozen=True)
class DashboardOverview:
    today: date
    revenue_today: Decimal
    revenue_this_month: Decimal
    invoice_count_today: int
    total_customers: int
    new_customers_this_month: int
    total_pets: int
    appointments_today: int
    pending_appointments: int
    unpaid_invoices: int
    recent_days: list[DailyRevenue]
    top_services: list[ServiceStat]
    vip_customers: list[VipCustomer]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class ReportError(Exception):
    """Loi nghiep vu cua report_service."""


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()
    raise ReportError(f"Khong the chuyen {value!r} sang date")


def _validate_range(start: date, end: date) -> tuple[date, date]:
    start = _as_date(start)
    end = _as_date(end)
    if start > end:
        raise ReportError("Ngay bat dau phai nho hon hoac bang ngay ket thuc.")
    return start, end


def _dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def month_range(year: int, month: int) -> tuple[date, date]:
    """Tra ve (first_day, last_day) cua thang."""
    if not 1 <= month <= 12:
        raise ReportError("Thang phai trong khoang 1..12")
    first = date(year, month, 1)
    if month == 12:
        next_first = date(year + 1, 1, 1)
    else:
        next_first = date(year, month + 1, 1)
    return first, next_first - timedelta(days=1)


def current_month_range(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    return month_range(today.year, today.month)


def last_n_days(n: int, end: date | None = None) -> tuple[date, date]:
    """Khoang n ngay gan nhat, ke ca `end` (mac dinh hom nay)."""
    if n <= 0:
        raise ReportError("So ngay phai > 0")
    end = end or date.today()
    return end - timedelta(days=n - 1), end


# ---------------------------------------------------------------------------
# 1) Doanh thu theo ngay / thang / khoang ngay
# ---------------------------------------------------------------------------

def revenue_by_day(start: date, end: date) -> list[DailyRevenue]:
    """Doanh thu theo tung ngay, co dien them ngay khong phat sinh (total=0)."""
    start, end = _validate_range(start, end)
    rows = report_dao.revenue_by_day(start, end)
    by_date: dict[date, DailyRevenue] = {
        _as_date(r["revenue_date"]): DailyRevenue(
            revenue_date=_as_date(r["revenue_date"]),
            invoice_count=int(r["invoice_count"]),
            total_revenue=_dec(r["total_revenue"]),
        )
        for r in rows
    }

    result: list[DailyRevenue] = []
    cur = start
    while cur <= end:
        result.append(
            by_date.get(
                cur,
                DailyRevenue(revenue_date=cur, invoice_count=0, total_revenue=Decimal("0")),
            )
        )
        cur += timedelta(days=1)
    return result


def revenue_by_month(start: date, end: date) -> list[MonthlyRevenue]:
    """Doanh thu theo thang trong khoang [start, end]. Thang rong van duoc liet ke."""
    start, end = _validate_range(start, end)
    rows = report_dao.revenue_by_month(start, end)
    by_key: dict[tuple[int, int], MonthlyRevenue] = {
        (int(r["year"]), int(r["month"])): MonthlyRevenue(
            year=int(r["year"]),
            month=int(r["month"]),
            invoice_count=int(r["invoice_count"]),
            total_revenue=_dec(r["total_revenue"]),
        )
        for r in rows
    }

    result: list[MonthlyRevenue] = []
    y, m = start.year, start.month
    end_key = (end.year, end.month)
    while (y, m) <= end_key:
        result.append(
            by_key.get(
                (y, m),
                MonthlyRevenue(year=y, month=m, invoice_count=0, total_revenue=Decimal("0")),
            )
        )
        m += 1
        if m > 12:
            m = 1
            y += 1
    return result


def revenue_in_range(start: date, end: date) -> RevenueSummary:
    """Tong hop doanh thu trong khoang [start, end]."""
    start, end = _validate_range(start, end)
    row = report_dao.revenue_summary(start, end)
    return RevenueSummary(
        start=start,
        end=end,
        invoice_count=int(row.get("invoice_count") or 0),
        total_revenue=_dec(row.get("total_revenue")),
        avg_invoice=_dec(row.get("avg_invoice")),
    )


def revenue_today() -> RevenueSummary:
    today = date.today()
    return revenue_in_range(today, today)


def revenue_this_month() -> RevenueSummary:
    s, e = current_month_range()
    return revenue_in_range(s, e)


# ---------------------------------------------------------------------------
# 2) Dich vu pho bien (Top N)
# ---------------------------------------------------------------------------

def top_services(
    limit: int = 5,
    by: TopBy = "quantity",
    start: date | None = None,
    end: date | None = None,
) -> list[ServiceStat]:
    """Top N dich vu pho bien nhat.

    - by="quantity": sap xep theo tong so luong ban ra.
    - by="revenue": sap xep theo tong doanh thu dich vu dong gop.
    - Neu truyen ca start & end thi chi tinh trong khoang do.
    """
    if limit <= 0:
        raise ReportError("limit phai > 0")
    if (start is None) ^ (end is None):
        raise ReportError("Phai truyen ca start va end, hoac khong truyen ca hai.")
    if start is not None and end is not None:
        start, end = _validate_range(start, end)

    if by == "quantity":
        rows = report_dao.top_services_by_quantity(limit, start, end)
    elif by == "revenue":
        rows = report_dao.top_services_by_revenue(limit, start, end)
    else:
        raise ReportError(f"Tham so 'by' khong hop le: {by!r}")

    return [
        ServiceStat(
            service_id=int(r["service_id"]),
            service_name=str(r["service_name"]),
            total_sold=int(r["total_sold"] or 0),
            total_revenue=_dec(r["total_revenue"]),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 3) Thong ke khach hang
# ---------------------------------------------------------------------------

def customer_stats(
    today: date | None = None,
    vip_limit: int = 5,
    vip_period: tuple[date, date] | None = None,
) -> CustomerStats:
    """Tong quan khach hang: tong so, khach moi trong thang, top khach VIP."""
    today = today or date.today()
    month_start, month_end = current_month_range(today)
    total = report_dao.count_customers()
    new_in_month = report_dao.count_new_customers_between(month_start, month_end)

    if vip_period is not None:
        v_start, v_end = _validate_range(*vip_period)
        vip_rows = report_dao.vip_customers_by_spending(vip_limit, v_start, v_end)
    else:
        vip_rows = report_dao.vip_customers_by_spending(vip_limit)

    vips = [
        VipCustomer(
            customer_id=int(r["customer_id"]),
            full_name=str(r["full_name"]),
            phone=r.get("phone"),
            invoice_count=int(r["invoice_count"] or 0),
            total_spent=_dec(r["total_spent"]),
        )
        for r in vip_rows
    ]
    return CustomerStats(
        total_customers=total,
        new_this_month=new_in_month,
        vip_customers=vips,
    )


# ---------------------------------------------------------------------------
# 4) Dashboard tong quan - gop cac so lieu
# ---------------------------------------------------------------------------

def dashboard_overview(
    today: date | None = None,
    recent_days: int = 7,
    top_n: int = 5,
) -> DashboardOverview:
    """Goi 1 phat, lay tat ca so lieu dashboard.

    - `recent_days`: so ngay gan nhat de ve bieu do doanh thu.
    - `top_n`: so dich vu / khach VIP hien thi.
    """
    today = today or date.today()
    month_start, month_end = current_month_range(today)

    today_sum = revenue_in_range(today, today)
    month_sum = revenue_in_range(month_start, month_end)
    days_start, days_end = last_n_days(recent_days, today)
    recent = revenue_by_day(days_start, days_end)
    top = top_services(limit=top_n, by="quantity")

    # VIP trong thang hien tai; neu thang rong thi fallback tong the
    vip_rows = report_dao.vip_customers_by_spending(top_n, month_start, month_end)
    if not vip_rows:
        vip_rows = report_dao.vip_customers_by_spending(top_n)
    vips = [
        VipCustomer(
            customer_id=int(r["customer_id"]),
            full_name=str(r["full_name"]),
            phone=r.get("phone"),
            invoice_count=int(r["invoice_count"] or 0),
            total_spent=_dec(r["total_spent"]),
        )
        for r in vip_rows
    ]

    return DashboardOverview(
        today=today,
        revenue_today=today_sum.total_revenue,
        revenue_this_month=month_sum.total_revenue,
        invoice_count_today=today_sum.invoice_count,
        total_customers=report_dao.count_customers(),
        new_customers_this_month=report_dao.count_new_customers_between(month_start, month_end),
        total_pets=report_dao.count_pets(),
        appointments_today=report_dao.count_appointments_on_date(today),
        pending_appointments=report_dao.count_pending_appointments(),
        unpaid_invoices=report_dao.count_unpaid_invoices(),
        recent_days=recent,
        top_services=top,
        vip_customers=vips,
    )


# ---------------------------------------------------------------------------
# Tien ich format cho UI
# ---------------------------------------------------------------------------

def format_vnd(value: Decimal | int | float | None) -> str:
    """Format so tien theo kieu VN: 1.250.000d."""
    if value is None:
        return "0đ"
    n = int(Decimal(str(value)))
    return f"{n:,}đ".replace(",", ".")
