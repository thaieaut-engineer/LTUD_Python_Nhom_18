"""Dashboard page - tong quan doanh thu, dich vu, khach hang.

Lay so lieu truc tiep tu `report_service`. Co cac thanh phan:
- 6 the so lieu nhanh (doanh thu hom nay/thang, KH, pet, lich hen, KH moi)
- Bo loc khoang thoi gian (hom nay / 7 ngay / 30 ngay / thang nay / tuy chinh)
- Bieu do cot doanh thu theo ngay trong khoang loc
- Bang Top dich vu pho bien, Khach VIP, Doanh so nhan vien (mac dinh 8 dong)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

from PyQt6.QtCore import QDate, QPointF, Qt, QRect, QRectF
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
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
    EmployeePerformance,
    ReportError,
    RetailCategory,
    RetailCategoryDailyPoint,
    RetailProductRevenue,
    ServiceStat,
    VipCustomer,
)

from ..theme import THEME
from ..widgets import Card, page_header


# So ban ghi hien thi o bang: dich vu pho bien, khach VIP, doanh so nhan vien
DASHBOARD_RANK_ROWS = 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VND = report_service.format_vnd


def _sync_rank_table_height(table: QTableWidget) -> None:
    """Chieu cao bang xep hang du cho DASHBOARD_RANK_ROWS hang (cuon ca trang, khong cuon trong bang)."""
    hdr = table.horizontalHeader()
    hdr_h = max(hdr.sizeHint().height(), 36)
    if table.rowCount() > 0:
        table.resizeRowsToContents()
        sample_h = max(30, min(44, table.rowHeight(0)))
    else:
        sample_h = 34
    for r in range(table.rowCount()):
        table.setRowHeight(r, sample_h)
    table.setMinimumHeight(int(hdr_h + DASHBOARD_RANK_ROWS * sample_h + 8))
    table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)


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
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

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

        grad_start = QColor(THEME.primary_left)
        grad_end = QColor(THEME.primary)

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
                painter.setPen(QColor(THEME.text_strong))
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


# ---------------------------------------------------------------------------
# Bieu do duong: ban le do an vs phu kien theo ngay
# ---------------------------------------------------------------------------


class RetailCategoryLineChart(QWidget):
    """Hai duong: doanh thu do an (cam) va phu kien (xanh) theo tung ngay."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: list[RetailCategoryDailyPoint] = []
        self.setMinimumHeight(280)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

    def set_data(self, data: list[RetailCategoryDailyPoint]) -> None:
        self._data = list(data)
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        margin_left = 58
        margin_right = 16
        margin_top = 34
        margin_bottom = 44

        chart_x = margin_left
        chart_y = margin_top
        chart_w = max(0, rect.width() - margin_left - margin_right)
        chart_h = max(0, rect.height() - margin_top - margin_bottom)

        if not self._data:
            painter.setPen(QColor(100, 116, 139))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Chưa có dữ liệu trong khoảng")
            painter.end()
            return

        max_v = max(
            max(float(p.do_an), float(p.phu_kien)) for p in self._data
        )
        if max_v <= 0:
            painter.setPen(QColor(100, 116, 139))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                "Không có doanh thu bán lẻ trong khoảng",
            )
            painter.end()
            return

        # Chuc thich (goc phai tren vung bieu do)
        lx = chart_x + chart_w - 132
        ly = chart_y - 26
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(THEME.stat_orange))
        painter.drawRoundedRect(int(lx), int(ly), 10, 10, 2, 2)
        painter.setPen(QColor(THEME.text))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.drawText(int(lx + 14), int(ly + 9), "Đồ ăn")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(THEME.accent))
        painter.drawRoundedRect(int(lx + 62), int(ly), 10, 10, 2, 2)
        painter.setPen(QColor(THEME.text))
        painter.drawText(int(lx + 76), int(ly + 9), "Phụ kiện")

        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        painter.drawLine(chart_x, chart_y + chart_h, chart_x + chart_w, chart_y + chart_h)
        painter.drawLine(chart_x, chart_y, chart_x, chart_y + chart_h)

        painter.setPen(QPen(QColor("#EEF2F7"), 1, Qt.PenStyle.DashLine))
        painter.setFont(QFont("Segoe UI", 8))
        for i in range(1, 5):
            y = chart_y + chart_h - int(chart_h * i / 4)
            painter.drawLine(chart_x, y, chart_x + chart_w, y)
            val = max_v * i / 4
            painter.setPen(QColor(100, 116, 139))
            painter.drawText(
                0,
                y - 8,
                margin_left - 6,
                16,
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                _compact_money(val),
            )
            painter.setPen(QPen(QColor("#EEF2F7"), 1, Qt.PenStyle.DashLine))

        n = len(self._data)
        pts_do: list[QPointF] = []
        pts_pk: list[QPointF] = []
        for i in range(n):
            if n == 1:
                x = float(chart_x + chart_w / 2)
            else:
                x = float(chart_x + chart_w * i / (n - 1))
            d = float(self._data[i].do_an)
            pk = float(self._data[i].phu_kien)
            y_do = float(chart_y + chart_h - (d / max_v) * chart_h)
            y_pk = float(chart_y + chart_h - (pk / max_v) * chart_h)
            pts_do.append(QPointF(x, y_do))
            pts_pk.append(QPointF(x, y_pk))

        painter.setPen(QPen(QColor(THEME.stat_orange), 2.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(QPolygonF(pts_do))
        painter.setPen(QPen(QColor(THEME.accent), 2.5))
        painter.drawPolyline(QPolygonF(pts_pk))

        r = 3.5
        painter.setBrush(QColor(THEME.stat_orange))
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
        for pt in pts_do:
            painter.drawEllipse(pt, r, r)
        painter.setBrush(QColor(THEME.accent))
        for pt in pts_pk:
            painter.drawEllipse(pt, r, r)

        # Nhan truc hoanh
        painter.setPen(QColor(71, 85, 105))
        painter.setFont(QFont("Segoe UI", 8))
        step_x = max(1, n // 8) if n > 8 else 1
        for i in range(0, n, step_x):
            if n == 1:
                cx = chart_x + chart_w / 2
            else:
                cx = chart_x + chart_w * i / (n - 1)
            painter.drawText(
                int(cx - 24),
                chart_y + chart_h + 6,
                48,
                18,
                int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
                self._data[i].day.strftime("%d/%m"),
            )

        painter.end()


# ---------------------------------------------------------------------------
# Bieu do tron: ban le chi tiet theo san pham (do an / phu kien)
# ---------------------------------------------------------------------------


def _vary_category_color(base: QColor, idx: int, n: int) -> QColor:
    """Tạo màu khác nhau theo thứ tự slice (cùng nhóm do an/phụ kiện).

    Thay vì chỉ "làm nhạt" (có thể gần như cùng màu), ta dịch theo dải hue để phân biệt rõ hơn.
    """
    if n <= 1:
        return QColor(base)

    h, s, v, a = base.getHsv()
    ratio = idx / max(n - 1, 1)  # 0..1

    # DO_AN: dải hue hẹp hơn (cam -> vàng -> cam đậm); PHU_KIEN: dải hue rộng hơn (xanh -> cyan -> xanh đậm)
    base_hex = base.name().lower()
    orange_hex = QColor(THEME.stat_orange).name().lower()
    hue_span = 34 if base_hex == orange_hex else 48

    h2 = int(h - hue_span / 2 + ratio * hue_span) % 360
    # Nhích độ bão hòa/độ sáng theo vị trí slice để tránh quá đồng nhất
    s2 = int(min(255, max(90, s * (0.88 + 0.18 * (1 - abs(2 * ratio - 1))))))
    v2 = int(min(255, max(70, v * (0.86 + 0.22 * ratio))))
    return QColor.fromHsv(h2, s2, v2, a)


def _colors_for_retail_rows(items: list[RetailProductRevenue]) -> list[QColor]:
    n_do = sum(1 for i in items if i.category_code == "DO_AN")
    n_pk = sum(1 for i in items if i.category_code == "PHU_KIEN")
    i_do = i_pk = 0
    out: list[QColor] = []
    for it in items:
        if it.category_code == "KHAC":
            out.append(QColor("#94A3B8"))
        elif it.category_code == "DO_AN":
            out.append(_vary_category_color(QColor(THEME.stat_orange), i_do, max(n_do, 1)))
            i_do += 1
        else:
            out.append(_vary_category_color(QColor(THEME.accent), i_pk, max(n_pk, 1)))
            i_pk += 1
    return out


class _PieCanvas(QWidget):
    """Ve hinh tron tu (gia tri, mau)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._segments: list[tuple[float, QColor]] = []
        self.setFixedSize(258, 258)

    def set_segments(self, segments: list[tuple[float, QColor]]) -> None:
        self._segments = list(segments)
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if not self._segments:
            painter.setPen(QColor(100, 116, 139))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Chưa có dữ liệu bán lẻ trong khoảng",
            )
            painter.end()
            return
        total = sum(s[0] for s in self._segments)
        if total <= 0:
            painter.end()
            return
        m = 8
        side = min(self.width(), self.height()) - 2 * m
        side = max(side, 80)
        x0 = (self.width() - side) // 2
        y0 = (self.height() - side) // 2
        rect = QRect(x0, y0, side, side)
        angle = 90 * 16
        for val, color in self._segments:
            span = int(round(16 * 360 * val / total))
            if span <= 0:
                continue
            painter.setPen(QPen(QColor(255, 255, 255, 210), 2))
            painter.setBrush(QBrush(color))
            painter.drawPie(rect, angle, -span)
            angle -= span
        painter.end()


class RetailProductPieChart(QWidget):
    """Tron + chu thich cuon: moi mat hang mot slice, mau theo nhom do an / phu kien."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._canvas = _PieCanvas(self)
        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setMinimumHeight(280)
        self._scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._legend_root = QWidget()
        self._legend_lay = QVBoxLayout(self._legend_root)
        self._legend_lay.setContentsMargins(4, 0, 0, 0)
        self._legend_lay.setSpacing(4)
        self._legend_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._legend_root)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(self._canvas, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(self._scroll, 1)

        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def set_data(self, items: list[RetailProductRevenue]) -> None:
        while self._legend_lay.count():
            it = self._legend_lay.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()

        if not items:
            self._canvas.set_segments([])
            return

        vals = [float(i.total_revenue) for i in items]
        colors = _colors_for_retail_rows(items)
        total = sum(vals)
        self._canvas.set_segments(list(zip(vals, colors)))

        for it, color in zip(items, colors):
            row_w = QWidget()
            rlay = QHBoxLayout(row_w)
            rlay.setContentsMargins(0, 2, 0, 2)
            swatch = QFrame()
            swatch.setFixedSize(12, 12)
            swatch.setStyleSheet(
                f"QFrame{{background:{color.name()};border-radius:3px;border:none;}}"
            )
            rlay.addWidget(swatch, 0, Qt.AlignmentFlag.AlignTop)
            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            name_l = QLabel(it.product_name)
            name_l.setWordWrap(True)
            name_l.setStyleSheet("font:600 9pt 'Segoe UI';")
            pct = 100.0 * float(it.total_revenue) / total if total > 0 else 0.0
            sub = QLabel(f"{it.category_label} · {_VND(it.total_revenue)} ({pct:.0f}%)")
            sub.setStyleSheet(f"color:{THEME.muted}; font:8pt 'Segoe UI';")
            text_col.addWidget(name_l)
            text_col.addWidget(sub)
            rlay.addLayout(text_col, 1)
            self._legend_lay.addWidget(row_w)


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

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(16)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll)
        scroll.setWidget(content)

        # Header + reload button
        refresh_btn = QPushButton("⟳ Làm mới")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(
            f"QPushButton{{background:{THEME.primary};color:white;border:none;"
            "padding:6px 14px;border-radius:8px;font:700 9pt 'Segoe UI';}"
            f"QPushButton:hover{{background:{THEME.primary_hover};}}"
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
            f"QPushButton{{background:{THEME.accent};color:white;border:none;"
            "padding:6px 14px;border-radius:8px;font:700 9pt 'Segoe UI';}"
            f"QPushButton:hover{{background:{THEME.accent_strong};}}"
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
            "Doanh thu (khoảng đã chọn)", THEME.primary
        )
        self._card_revenue_today, self._lbl_revenue_today = _stat_card(
            "Doanh thu hôm nay", THEME.success
        )
        self._card_revenue_month, self._lbl_revenue_month = _stat_card(
            "Doanh thu tháng này", THEME.accent
        )
        self._card_customers, self._lbl_customers = _stat_card(
            "Khách hàng", THEME.stat_green
        )
        self._card_new_customers, self._lbl_new_customers = _stat_card(
            "KH mới trong tháng", THEME.stat_orange
        )
        self._card_appt_today, self._lbl_appt_today = _stat_card(
            "Lịch hẹn hôm nay", THEME.stat_pink
        )

        stats.addWidget(self._card_revenue_range, 0, 0)
        stats.addWidget(self._card_revenue_today, 0, 1)
        stats.addWidget(self._card_revenue_month, 0, 2)
        stats.addWidget(self._card_customers, 1, 0)
        stats.addWidget(self._card_new_customers, 1, 1)
        stats.addWidget(self._card_appt_today, 1, 2)
        root.addLayout(stats)

        # --- Bieu do cot + duong ban le ---
        charts_row = QHBoxLayout()
        charts_row.setSpacing(14)

        chart_card = Card()
        chart_lay = QVBoxLayout(chart_card)
        chart_lay.setContentsMargins(18, 14, 18, 14)
        chart_lay.setSpacing(8)
        self._chart_title = QLabel("Doanh thu theo ngày")
        self._chart_title.setStyleSheet("font:800 10pt 'Segoe UI';")
        chart_lay.addWidget(self._chart_title)
        self._chart = RevenueBarChart()
        self._chart.setMinimumHeight(280)
        self._chart.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        chart_lay.addWidget(self._chart)
        charts_row.addWidget(chart_card, 2)

        pie_card = Card()
        pie_lay = QVBoxLayout(pie_card)
        pie_lay.setContentsMargins(18, 14, 18, 14)
        pie_lay.setSpacing(8)
        self._pie_title = QLabel("Bán lẻ — đồ ăn & phụ kiện theo ngày")
        self._pie_title.setStyleSheet("font:800 10pt 'Segoe UI';")
        pie_lay.addWidget(self._pie_title)
        self._retail_line = RetailCategoryLineChart()
        pie_lay.addWidget(self._retail_line)
        detail_row = QHBoxLayout()
        detail_row.setSpacing(8)
        btn_detail_style = (
            f"QPushButton {{ padding:6px 12px; border-radius:6px; border:1px solid {THEME.border}; "
            f"background:{THEME.surface_alt}; font:9pt 'Segoe UI'; }}"
            f"QPushButton:hover {{ background:{THEME.primary_soft}; border-color:{THEME.primary}; }}"
        )
        btn_do = QPushButton("Chi tiết đồ ăn")
        btn_do.setStyleSheet(btn_detail_style)
        btn_do.clicked.connect(lambda: self._show_retail_detail("DO_AN"))
        btn_pk = QPushButton("Chi tiết phụ kiện")
        btn_pk.setStyleSheet(btn_detail_style)
        btn_pk.clicked.connect(lambda: self._show_retail_detail("PHU_KIEN"))
        detail_row.addWidget(btn_do)
        detail_row.addWidget(btn_pk)
        detail_row.addStretch(1)
        pie_lay.addLayout(detail_row)
        charts_row.addWidget(pie_card, 1)

        root.addLayout(charts_row)

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
        _sync_rank_table_height(self._svc_table)
        svc_lay.addWidget(self._svc_table)
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
        _sync_rank_table_height(self._vip_table)
        vip_lay.addWidget(self._vip_table)
        bottom_grid.addWidget(vip_card, 0, 1)

        root.addLayout(bottom_grid)

        # --- Doanh so theo nhan vien ---
        emp_card = Card()
        emp_lay = QVBoxLayout(emp_card)
        emp_lay.setContentsMargins(18, 14, 18, 14)
        emp_lay.setSpacing(8)
        emp_head = QHBoxLayout()
        emp_title = QLabel("Doanh số theo nhân viên")
        emp_title.setStyleSheet("font:800 10pt 'Segoe UI';")
        emp_head.addWidget(emp_title)
        emp_head.addStretch(1)
        self._emp_summary = QLabel()
        self._emp_summary.setStyleSheet("color:#475569; font:700 9pt 'Segoe UI';")
        emp_head.addWidget(self._emp_summary)
        emp_lay.addLayout(emp_head)

        self._emp_table = QTableWidget(0, 7)
        self._emp_table.setHorizontalHeaderLabels([
            "#",
            "Nhân viên",
            "Lịch hẹn",
            "Hoàn thành",
            "HĐ dịch vụ",
            "HĐ bán lẻ",
            "Tổng doanh thu",
        ])
        _prepare_table(self._emp_table)
        _sync_rank_table_height(self._emp_table)
        emp_lay.addWidget(self._emp_table)
        root.addWidget(emp_card)

        self._apply_preset(self.PRESET_7D)
        # Khong tu reload o __init__ - de tranh query DB truoc khi user login.
        # `_set_stack_page` (app.py) se goi reload() khi mo trang dashboard.

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
        self._safe_call(self._reload_employees)

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
        ov: DashboardOverview = report_service.dashboard_overview(top_n=DASHBOARD_RANK_ROWS)
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

        daily_cat = report_service.retail_category_revenue_by_day(start, end)
        self._retail_line.set_data(daily_cat)
        self._pie_title.setText(
            f"Bán lẻ — đồ ăn & phụ kiện — {start.strftime('%d/%m/%Y')} → {end.strftime('%d/%m/%Y')}"
        )

    def _show_retail_detail(self, category: RetailCategory) -> None:
        start, end = self._selected_range()
        try:
            items = report_service.retail_product_revenue_in_category(start, end, category)
        except ReportError as exc:
            QMessageBox.warning(self, "Chi tiết bán lẻ", str(exc))
            return
        if category == "DO_AN":
            title = "Chi tiết đồ ăn (theo sản phẩm)"
        else:
            title = "Chi tiết phụ kiện (theo sản phẩm)"
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setMinimumSize(560, 480)
        dl = QVBoxLayout(dlg)
        range_lbl = QLabel(f"{start.strftime('%d/%m/%Y')} — {end.strftime('%d/%m/%Y')}")
        range_lbl.setStyleSheet(f"color:{THEME.muted}; font:9pt 'Segoe UI';")
        dl.addWidget(range_lbl)
        pie = RetailProductPieChart()
        pie.set_data(items)
        dl.addWidget(pie)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(dlg.reject)
        dl.addWidget(box)
        dlg.exec()

    def _reload_top_services(self) -> None:
        by = self._svc_by_combo.currentData() or "quantity"
        start, end = self._selected_range()
        items = report_service.top_services(limit=DASHBOARD_RANK_ROWS, by=by, start=start, end=end)
        if not items:
            items = report_service.top_services(limit=DASHBOARD_RANK_ROWS, by=by)
        self._fill_services_table(items)

    def _fill_services_table(self, items: list[ServiceStat]) -> None:
        self._svc_table.clearSpans()
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
        self._svc_table.resizeRowsToContents()
        _sync_rank_table_height(self._svc_table)

    def _reload_vip(self) -> None:
        start, end = self._selected_range()
        stats = report_service.customer_stats(
            vip_limit=DASHBOARD_RANK_ROWS, vip_period=(start, end)
        )
        items: list[VipCustomer] = list(stats.vip_customers)
        if not items:
            stats2 = report_service.customer_stats(vip_limit=DASHBOARD_RANK_ROWS)
            items = list(stats2.vip_customers)
        self._fill_vip_table(items)

    def _fill_vip_table(self, items: list[VipCustomer]) -> None:
        self._vip_table.clearSpans()
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
        self._vip_table.resizeRowsToContents()
        _sync_rank_table_height(self._vip_table)

    def _reload_employees(self) -> None:
        start, end = self._selected_range()
        report = report_service.employee_performance_stats(start, end)
        items = list(report.employees)
        non_zero = [e for e in items if e.total_revenue or e.appointment_count]
        if not non_zero:
            fallback = report_service.employee_performance_stats()
            items = list(fallback.employees)[:DASHBOARD_RANK_ROWS]
            self._emp_summary.setText(
                "(không có dữ liệu trong khoảng — hiển thị toàn thời gian)"
            )
        else:
            items = non_zero[:DASHBOARD_RANK_ROWS]
            self._emp_summary.setText(
                f"Tổng doanh thu NV: {_VND(report.total_revenue)}"
            )
        self._fill_employee_table(items)

    def _fill_employee_table(self, items: list[EmployeePerformance]) -> None:
        self._emp_table.clearSpans()
        self._emp_table.setRowCount(len(items))
        for r, e in enumerate(items):
            self._emp_table.setItem(r, 0, _cell(str(r + 1), center=True))
            self._emp_table.setItem(r, 1, _cell(e.full_name))
            self._emp_table.setItem(r, 2, _cell(str(e.appointment_count), center=True))
            self._emp_table.setItem(
                r,
                3,
                _cell(f"{e.appointment_done}/{e.appointment_count}", center=True),
            )
            self._emp_table.setItem(r, 4, _cell(_VND(e.service_revenue), right=True))
            self._emp_table.setItem(r, 5, _cell(_VND(e.retail_revenue), right=True))
            total_item = _cell(_VND(e.total_revenue), right=True)
            total_item.setForeground(QColor(THEME.text_strong))
            self._emp_table.setItem(r, 6, total_item)
        if not items:
            self._emp_table.setRowCount(1)
            self._emp_table.setSpan(0, 0, 1, self._emp_table.columnCount())
            self._emp_table.setItem(
                0, 0, _cell("Chưa có dữ liệu nhân viên", center=True, muted=True)
            )
        self._emp_table.resizeRowsToContents()
        _sync_rank_table_height(self._emp_table)


# ---------------------------------------------------------------------------
# Local table helpers
# ---------------------------------------------------------------------------

def _prepare_table(t: QTableWidget) -> None:
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    t.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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
