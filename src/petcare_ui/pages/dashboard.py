"""Dashboard page - tong quan doanh thu, dich vu, khach hang.

Lay so lieu truc tiep tu `report_service`. Co cac thanh phan:
- 6 the so lieu nhanh (doanh thu hom nay/thang, KH, pet, lich hen, KH moi)
- Bo loc khoang thoi gian (hom nay / 7 ngay / 30 ngay / thang nay / tuy chinh)
- Bieu do cot doanh thu theo ngay trong khoang loc
- Bang Top dich vu pho bien
- Bang Khach hang VIP
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

from PyQt6.QtCore import QDate, Qt, QRectF
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.petcare_backend.services import report_service
from src.petcare_backend.services.report_service import (
    DailyRevenue,
    DashboardOverview,
    ServiceStat,
    VipCustomer,
)

from ..theme import THEME
from ..widgets import Card, page_header


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VND = report_service.format_vnd


def _stat_card(title: str, color: str) -> tuple[QFrame, QLabel]:
    """Tao the so lieu gradient. Tra ve (frame, label_so)."""
    frame = QFrame()
    frame.setObjectName("StatCard")
    frame.setStyleSheet(
        f"QFrame#StatCard{{background: {color}; border: 0px; border-radius: 18px;}}"
        "QLabel{color: white; background: transparent;}"
    )
    frame.setMinimumHeight(96)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(18, 14, 18, 14)
    lay.setSpacing(6)

    t = QLabel(title)
    t.setStyleSheet("font: 700 9pt 'Segoe UI'; color: rgba(255,255,255,0.92);")
    v = QLabel("—")
    v.setStyleSheet("font: 900 18pt 'Segoe UI'; letter-spacing: -0.5px;")
    lay.addWidget(t)
    lay.addWidget(v)
    lay.addStretch(1)
    return frame, v


# ---------------------------------------------------------------------------
# Bieu do cot doanh thu theo ngay (ve bang QPainter)
# ---------------------------------------------------------------------------

class RevenueBarChart(QWidget):
    """Bieu do cot don gian cho doanh thu theo ngay. Khong can matplotlib."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: list[DailyRevenue] = []
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: list[DailyRevenue]) -> None:
        self._data = list(data)
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        margin_left = 58
        margin_right = 16
        margin_top = 16
        margin_bottom = 44

        chart_x = margin_left
        chart_y = margin_top
        chart_w = max(0, rect.width() - margin_left - margin_right)
        chart_h = max(0, rect.height() - margin_top - margin_bottom)

        # Khung ve
        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        painter.drawLine(chart_x, chart_y + chart_h, chart_x + chart_w, chart_y + chart_h)
        painter.drawLine(chart_x, chart_y, chart_x, chart_y + chart_h)

        if not self._data:
            painter.setPen(QColor(15, 23, 42, 120))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Chưa có dữ liệu doanh thu trong khoảng này")
            painter.end()
            return

        max_val = max((float(d.total_revenue) for d in self._data), default=0.0)
        if max_val <= 0:
            max_val = 1.0

        # Luoi ngang + nhan truc tung (4 moc)
        painter.setPen(QPen(QColor("#EEF2F7"), 1, Qt.PenStyle.DashLine))
        painter.setFont(QFont("Segoe UI", 8))
        for i in range(1, 5):
            y = chart_y + chart_h - int(chart_h * i / 4)
            painter.drawLine(chart_x, y, chart_x + chart_w, y)
            val = max_val * i / 4
            painter.setPen(QColor(100, 116, 139))
            painter.drawText(
                0, y - 8, margin_left - 6, 16,
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                _compact_money(val),
            )
            painter.setPen(QPen(QColor("#EEF2F7"), 1, Qt.PenStyle.DashLine))

        n = len(self._data)
        slot = chart_w / n
        bar_w = max(10.0, min(slot * 0.62, 46.0))

        grad_start = QColor("#60A5FA")
        grad_end = QColor("#2563EB")

        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        for i, d in enumerate(self._data):
            v = float(d.total_revenue)
            h = (v / max_val) * chart_h if max_val > 0 else 0.0
            x = chart_x + slot * i + (slot - bar_w) / 2
            y = chart_y + chart_h - h
            bar_rect = QRectF(x, y, bar_w, h)

            if h > 0:
                grad = QLinearGradient(x, y, x, y + h)
                grad.setColorAt(0, grad_start)
                grad.setColorAt(1, grad_end)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(grad))
                painter.drawRoundedRect(bar_rect, 6, 6)

                # Gia tri tren dinh cot
                painter.setPen(QColor(30, 64, 175))
                painter.drawText(
                    QRectF(x - 10, y - 18, bar_w + 20, 16),
                    int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom),
                    _compact_money(v),
                )

            # Nhan truc hoanh (dd/MM)
            painter.setPen(QColor(71, 85, 105))
            painter.drawText(
                QRectF(chart_x + slot * i, chart_y + chart_h + 6, slot, 18),
                int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
                d.revenue_date.strftime("%d/%m"),
            )

        painter.end()


def _compact_money(v: float) -> str:
    """Rut gon tien cho truc bieu do: 1.2tr, 850k, 0."""
    if v <= 0:
        return "0"
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}tr".replace(".0tr", "tr")
    if v >= 1_000:
        return f"{v / 1_000:.0f}k"
    return f"{int(v)}"


# ---------------------------------------------------------------------------
# Dashboard view
# ---------------------------------------------------------------------------

class DashboardView(QWidget):
    """Dashboard tong quan dung `report_service`."""

    PRESET_TODAY = "TODAY"
    PRESET_7D = "7D"
    PRESET_30D = "30D"
    PRESET_MONTH = "MONTH"
    PRESET_CUSTOM = "CUSTOM"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("page_key", "dashboard")

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(16)

        # Header + reload button
        refresh_btn = QPushButton("⟳ Làm mới")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(
            "QPushButton{background:#2563EB;color:white;border:none;"
            "padding:6px 14px;border-radius:8px;font:700 9pt 'Segoe UI';}"
            "QPushButton:hover{background:#1D4ED8;}"
        )
        refresh_btn.clicked.connect(self.reload)
        root.addWidget(page_header("Trang chủ", right_widget=refresh_btn, emoji="📊"))

        # --- Bo loc khoang ngay ---
        filter_card = Card()
        filter_lay = QHBoxLayout(filter_card)
        filter_lay.setContentsMargins(18, 12, 18, 12)
        filter_lay.setSpacing(10)

        lbl = QLabel("Khoảng thời gian:")
        lbl.setStyleSheet("font:700 9pt 'Segoe UI';")
        filter_lay.addWidget(lbl)

        self._preset_combo = QComboBox()
        self._preset_combo.addItem("Hôm nay", self.PRESET_TODAY)
        self._preset_combo.addItem("7 ngày gần nhất", self.PRESET_7D)
        self._preset_combo.addItem("30 ngày gần nhất", self.PRESET_30D)
        self._preset_combo.addItem("Tháng này", self.PRESET_MONTH)
        self._preset_combo.addItem("Tuỳ chỉnh...", self.PRESET_CUSTOM)
        self._preset_combo.setCurrentIndex(1)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        filter_lay.addWidget(self._preset_combo)

        self._start_edit = QDateEdit()
        self._start_edit.setCalendarPopup(True)
        self._start_edit.setDisplayFormat("dd/MM/yyyy")
        self._end_edit = QDateEdit()
        self._end_edit.setCalendarPopup(True)
        self._end_edit.setDisplayFormat("dd/MM/yyyy")

        today = date.today()
        self._start_edit.setDate(QDate(today.year, today.month, today.day).addDays(-6))
        self._end_edit.setDate(QDate(today.year, today.month, today.day))

        filter_lay.addWidget(QLabel("Từ"))
        filter_lay.addWidget(self._start_edit)
        filter_lay.addWidget(QLabel("Đến"))
        filter_lay.addWidget(self._end_edit)

        apply_btn = QPushButton("Áp dụng")
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.setStyleSheet(
            "QPushButton{background:#0F172A;color:white;border:none;"
            "padding:6px 14px;border-radius:8px;font:700 9pt 'Segoe UI';}"
            "QPushButton:hover{background:#1E293B;}"
        )
        apply_btn.clicked.connect(self.reload)
        filter_lay.addWidget(apply_btn)
        filter_lay.addStretch(1)

        self._summary_label = QLabel()
        self._summary_label.setStyleSheet("color:#334155; font:700 9pt 'Segoe UI';")
        filter_lay.addWidget(self._summary_label)

        root.addWidget(filter_card)

        # --- The so lieu ---
        stats = QGridLayout()
        stats.setHorizontalSpacing(14)
        stats.setVerticalSpacing(14)

        self._card_revenue_range, self._lbl_revenue_range = _stat_card(
            "Doanh thu (khoảng đã chọn)", "#2563EB"
        )
        self._card_revenue_today, self._lbl_revenue_today = _stat_card(
            "Doanh thu hôm nay", "#0EA5E9"
        )
        self._card_revenue_month, self._lbl_revenue_month = _stat_card(
            "Doanh thu tháng này", "#7C3AED"
        )
        self._card_customers, self._lbl_customers = _stat_card(
            "Khách hàng", "#10B981"
        )
        self._card_new_customers, self._lbl_new_customers = _stat_card(
            "KH mới trong tháng", "#F59E0B"
        )
        self._card_appt_today, self._lbl_appt_today = _stat_card(
            "Lịch hẹn hôm nay", "#EC4899"
        )

        stats.addWidget(self._card_revenue_range, 0, 0)
        stats.addWidget(self._card_revenue_today, 0, 1)
        stats.addWidget(self._card_revenue_month, 0, 2)
        stats.addWidget(self._card_customers, 1, 0)
        stats.addWidget(self._card_new_customers, 1, 1)
        stats.addWidget(self._card_appt_today, 1, 2)
        root.addLayout(stats)

        # --- Bieu do ---
        chart_card = Card()
        chart_lay = QVBoxLayout(chart_card)
        chart_lay.setContentsMargins(18, 14, 18, 14)
        chart_lay.setSpacing(8)
        self._chart_title = QLabel("Doanh thu theo ngày")
        self._chart_title.setStyleSheet("font:800 10pt 'Segoe UI';")
        chart_lay.addWidget(self._chart_title)
        self._chart = RevenueBarChart()
        chart_lay.addWidget(self._chart, 1)
        root.addWidget(chart_card, 1)

        # --- Bang Top dich vu + Khach VIP canh nhau ---
        bottom_grid = QGridLayout()
        bottom_grid.setHorizontalSpacing(14)
        bottom_grid.setVerticalSpacing(14)

        # Top services card
        svc_card = Card()
        svc_lay = QVBoxLayout(svc_card)
        svc_lay.setContentsMargins(18, 14, 18, 14)
        svc_lay.setSpacing(8)
        svc_head = QHBoxLayout()
        svc_title = QLabel("Dịch vụ phổ biến")
        svc_title.setStyleSheet("font:800 10pt 'Segoe UI';")
        svc_head.addWidget(svc_title)
        svc_head.addStretch(1)

        self._svc_by_combo = QComboBox()
        self._svc_by_combo.addItem("Theo số lượng", "quantity")
        self._svc_by_combo.addItem("Theo doanh thu", "revenue")
        self._svc_by_combo.currentIndexChanged.connect(self._reload_top_services)
        svc_head.addWidget(self._svc_by_combo)
        svc_lay.addLayout(svc_head)

        self._svc_table = QTableWidget(0, 4)
        self._svc_table.setHorizontalHeaderLabels(["#", "Dịch vụ", "Số lượng", "Doanh thu"])
        _prepare_table(self._svc_table)
        svc_lay.addWidget(self._svc_table, 1)
        bottom_grid.addWidget(svc_card, 0, 0)

        # VIP customers card
        vip_card = Card()
        vip_lay = QVBoxLayout(vip_card)
        vip_lay.setContentsMargins(18, 14, 18, 14)
        vip_lay.setSpacing(8)
        vip_title = QLabel("Khách hàng VIP (theo chi tiêu)")
        vip_title.setStyleSheet("font:800 10pt 'Segoe UI';")
        vip_lay.addWidget(vip_title)

        self._vip_table = QTableWidget(0, 5)
        self._vip_table.setHorizontalHeaderLabels(
            ["#", "Khách hàng", "SĐT", "Số HĐ", "Tổng chi tiêu"]
        )
        _prepare_table(self._vip_table)
        vip_lay.addWidget(self._vip_table, 1)
        bottom_grid.addWidget(vip_card, 0, 1)

        root.addLayout(bottom_grid)

        self._apply_preset(self.PRESET_7D)
        self.reload()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_preset_changed(self) -> None:
        preset = self._preset_combo.currentData()
        if preset == self.PRESET_CUSTOM:
            self._set_date_editable(True)
            return
        self._set_date_editable(False)
        self._apply_preset(preset)
        self.reload()

    def _set_date_editable(self, editable: bool) -> None:
        self._start_edit.setEnabled(editable)
        self._end_edit.setEnabled(editable)

    def _apply_preset(self, preset: str) -> None:
        today = date.today()
        if preset == self.PRESET_TODAY:
            start, end = today, today
        elif preset == self.PRESET_7D:
            start, end = today - timedelta(days=6), today
        elif preset == self.PRESET_30D:
            start, end = today - timedelta(days=29), today
        elif preset == self.PRESET_MONTH:
            start, end = report_service.current_month_range(today)
        else:
            return
        self._start_edit.blockSignals(True)
        self._end_edit.blockSignals(True)
        self._start_edit.setDate(QDate(start.year, start.month, start.day))
        self._end_edit.setDate(QDate(end.year, end.month, end.day))
        self._start_edit.blockSignals(False)
        self._end_edit.blockSignals(False)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _selected_range(self) -> tuple[date, date]:
        qs = self._start_edit.date()
        qe = self._end_edit.date()
        start = date(qs.year(), qs.month(), qs.day())
        end = date(qe.year(), qe.month(), qe.day())
        if start > end:
            start, end = end, start
        return start, end

    def reload(self) -> None:
        """Tai lai toan bo dashboard (goi khi mo trang hoac bam Lam moi)."""
        self._safe_call(self._reload_overview)
        self._safe_call(self._reload_range)
        self._safe_call(self._reload_top_services)
        self._safe_call(self._reload_vip)

    def _safe_call(self, fn: Callable[[], None]) -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - bao ve UI khi DB loi
            self._summary_label.setText("(không thể tải dữ liệu)")
            QMessageBox.warning(
                self,
                "Dashboard",
                f"Không thể tải dữ liệu báo cáo:\n{exc}",
            )

    def _reload_overview(self) -> None:
        ov: DashboardOverview = report_service.dashboard_overview(top_n=5)
        self._lbl_revenue_today.setText(_VND(ov.revenue_today))
        self._lbl_revenue_month.setText(_VND(ov.revenue_this_month))
        self._lbl_customers.setText(str(ov.total_customers))
        self._lbl_new_customers.setText(str(ov.new_customers_this_month))
        self._lbl_appt_today.setText(str(ov.appointments_today))

    def _reload_range(self) -> None:
        start, end = self._selected_range()
        summary = report_service.revenue_in_range(start, end)
        self._lbl_revenue_range.setText(_VND(summary.total_revenue))

        series = report_service.revenue_by_day(start, end)
        self._chart.set_data(series)
        span = (end - start).days + 1
        self._chart_title.setText(
            f"Doanh thu theo ngày — {start.strftime('%d/%m/%Y')} → {end.strftime('%d/%m/%Y')} ({span} ngày)"
        )
        self._summary_label.setText(
            f"{summary.invoice_count} hoá đơn • TB {_VND(summary.avg_invoice)}/HĐ"
        )

    def _reload_top_services(self) -> None:
        by = self._svc_by_combo.currentData() or "quantity"
        start, end = self._selected_range()
        items = report_service.top_services(limit=5, by=by, start=start, end=end)
        if not items:
            items = report_service.top_services(limit=5, by=by)
        self._fill_services_table(items)

    def _fill_services_table(self, items: list[ServiceStat]) -> None:
        self._svc_table.setRowCount(len(items))
        for r, s in enumerate(items):
            self._svc_table.setItem(r, 0, _cell(str(r + 1), center=True))
            self._svc_table.setItem(r, 1, _cell(s.service_name))
            self._svc_table.setItem(r, 2, _cell(str(s.total_sold), center=True))
            self._svc_table.setItem(r, 3, _cell(_VND(s.total_revenue), right=True))
        if not items:
            self._svc_table.setRowCount(1)
            self._svc_table.setSpan(0, 0, 1, self._svc_table.columnCount())
            self._svc_table.setItem(0, 0, _cell("Chưa có dữ liệu", center=True, muted=True))

    def _reload_vip(self) -> None:
        start, end = self._selected_range()
        stats = report_service.customer_stats(
            vip_limit=5, vip_period=(start, end)
        )
        items: list[VipCustomer] = list(stats.vip_customers)
        if not items:
            stats2 = report_service.customer_stats(vip_limit=5)
            items = list(stats2.vip_customers)
        self._fill_vip_table(items)

    def _fill_vip_table(self, items: list[VipCustomer]) -> None:
        self._vip_table.setRowCount(len(items))
        for r, v in enumerate(items):
            self._vip_table.setItem(r, 0, _cell(str(r + 1), center=True))
            self._vip_table.setItem(r, 1, _cell(v.full_name))
            self._vip_table.setItem(r, 2, _cell(v.phone or "—", center=True))
            self._vip_table.setItem(r, 3, _cell(str(v.invoice_count), center=True))
            self._vip_table.setItem(r, 4, _cell(_VND(v.total_spent), right=True))
        if not items:
            self._vip_table.setRowCount(1)
            self._vip_table.setSpan(0, 0, 1, self._vip_table.columnCount())
            self._vip_table.setItem(0, 0, _cell("Chưa có dữ liệu", center=True, muted=True))


# ---------------------------------------------------------------------------
# Local table helpers
# ---------------------------------------------------------------------------

def _prepare_table(t: QTableWidget) -> None:
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    hdr = t.horizontalHeader()
    hdr.setStretchLastSection(False)
    hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if t.columnCount() >= 2:
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    t.setShowGrid(False)


def _cell(text: str, *, center: bool = False, right: bool = False, muted: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    flags = Qt.AlignmentFlag.AlignVCenter
    if center:
        flags |= Qt.AlignmentFlag.AlignHCenter
    elif right:
        flags |= Qt.AlignmentFlag.AlignRight
    else:
        flags |= Qt.AlignmentFlag.AlignLeft
    item.setTextAlignment(int(flags))
    if muted:
        item.setForeground(QColor(THEME.muted))
    return item
