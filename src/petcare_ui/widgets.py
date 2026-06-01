from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from .theme import THEME

DEFAULT_PAGE_SIZE = 10
PAGE_SIZE_OPTIONS = (5, 10, 20, 50)


class Paginator:
    """Trạng thái phân trang phía client (1-based page index)."""

    def __init__(self, page_size: int = DEFAULT_PAGE_SIZE) -> None:
        self.page_size = max(1, int(page_size))
        self.current_page = 1
        self.total_items = 0

    @property
    def total_pages(self) -> int:
        if self.total_items <= 0:
            return 1
        return max(1, (self.total_items + self.page_size - 1) // self.page_size)

    def reset_page(self) -> None:
        self.current_page = 1

    def clamp_page(self) -> None:
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        if self.current_page < 1:
            self.current_page = 1

    def page_slice(self, items: list) -> tuple[list, int, int]:
        self.total_items = len(items)
        self.clamp_page()
        start = (self.current_page - 1) * self.page_size
        end = min(start + self.page_size, self.total_items)
        return items[start:end], start, end


class PaginationBar(QWidget):
    """Thanh điều hướng trang: Trước / Sau, thông tin trang, chọn số dòng."""

    page_changed = pyqtSignal(int)
    page_size_changed = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PaginationBar")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        size_lbl = QLabel("Hiển thị:")
        size_lbl.setStyleSheet(f"color:{THEME.text_soft}; font:600 9pt 'Segoe UI';")
        lay.addWidget(size_lbl)

        self._size_combo = QComboBox()
        self._size_combo.setMinimumWidth(72)
        for n in PAGE_SIZE_OPTIONS:
            self._size_combo.addItem(str(n), n)
        self._size_combo.setCurrentIndex(PAGE_SIZE_OPTIONS.index(DEFAULT_PAGE_SIZE))
        self._size_combo.currentIndexChanged.connect(self._on_size_changed)
        lay.addWidget(self._size_combo)

        lay.addStretch(1)

        self._info = QLabel("")
        self._info.setStyleSheet(f"color:{THEME.text_soft}; font:600 9pt 'Segoe UI';")
        lay.addWidget(self._info)

        self._btn_prev = QPushButton("◀ Trước")
        self._btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_prev.clicked.connect(self._go_prev)
        lay.addWidget(self._btn_prev)

        self._btn_next = QPushButton("Sau ▶")
        self._btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_next.clicked.connect(self._go_next)
        lay.addWidget(self._btn_next)

        self._paginator: Paginator | None = None
        self._apply_style()

    def _apply_style(self) -> None:
        btn_qss = (
            f"QPushButton{{background:#FFFFFF;color:{THEME.text};"
            f"border:1px solid {THEME.border};padding:6px 14px;border-radius:8px;"
            f"font:700 9pt 'Segoe UI';min-width:72px;}}"
            f"QPushButton:hover{{background:{THEME.primary_soft};border-color:{THEME.primary};}}"
            f"QPushButton:disabled{{color:{THEME.muted};background:#F8FAFC;}}"
        )
        self._btn_prev.setStyleSheet(btn_qss)
        self._btn_next.setStyleSheet(btn_qss)
        self.setStyleSheet(
            f"QWidget#PaginationBar{{background:transparent;border-top:1px solid {THEME.border};}}"
        )

    def bind(self, paginator: Paginator) -> None:
        self._paginator = paginator
        idx = PAGE_SIZE_OPTIONS.index(paginator.page_size) if paginator.page_size in PAGE_SIZE_OPTIONS else 1
        self._size_combo.blockSignals(True)
        self._size_combo.setCurrentIndex(idx)
        self._size_combo.blockSignals(False)
        self.refresh()

    def refresh(self) -> None:
        pag = self._paginator
        if pag is None:
            self._info.setText("")
            self._btn_prev.setEnabled(False)
            self._btn_next.setEnabled(False)
            self.setVisible(False)
            return

        total = pag.total_items
        if total <= 0:
            self.setVisible(False)
            return

        self.setVisible(True)
        start = (pag.current_page - 1) * pag.page_size + 1
        end = min(pag.current_page * pag.page_size, total)
        self._info.setText(
            f"Trang {pag.current_page}/{pag.total_pages}  ·  {start}–{end} / {total} mục"
        )
        self._btn_prev.setEnabled(pag.current_page > 1)
        self._btn_next.setEnabled(pag.current_page < pag.total_pages)

    def _go_prev(self) -> None:
        if self._paginator and self._paginator.current_page > 1:
            self.page_changed.emit(self._paginator.current_page - 1)

    def _go_next(self) -> None:
        if self._paginator and self._paginator.current_page < self._paginator.total_pages:
            self.page_changed.emit(self._paginator.current_page + 1)

    def _on_size_changed(self) -> None:
        data = self._size_combo.currentData()
        if isinstance(data, int):
            self.page_size_changed.emit(data)


class Sidebar(QWidget):
    navigate = pyqtSignal(str)
    logout = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)

        paw = QLabel("🐾")
        paw.setStyleSheet("font-size: 16px; color: rgba(255,255,255,0.92);")
        title = QLabel("Pet Care Man...")
        title.setObjectName("SidebarTitle")
        header.addWidget(paw)
        header.addWidget(title)
        header.addStretch(1)
        root.addLayout(header)

        root.addSpacing(8)

        self._items: dict[str, QPushButton] = {}
        for key, label, icon in [
            ("dashboard", "Trang chủ", QIcon.fromTheme("view-dashboard")),
            ("customers", "Khách hàng", QIcon.fromTheme("user-group")),
            ("pets", "Thú cưng", QIcon.fromTheme("face-smile")),
            ("services", "Dịch vụ", QIcon.fromTheme("tools")),
            ("appointments", "Đặt lịch", QIcon.fromTheme("x-office-calendar")),
            ("invoices", "Hóa đơn", QIcon.fromTheme("document-new")),
        ]:
            btn = QPushButton(f"  {label}")
            btn.setObjectName("NavItem")
            btn.setProperty("active", False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(icon)
            btn.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
            root.addWidget(btn)
            self._items[key] = btn

        root.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        logout_btn = QPushButton("  Đăng xuất")
        logout_btn.setObjectName("Logout")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setIcon(QIcon.fromTheme("system-log-out"))
        logout_btn.clicked.connect(self.logout.emit)
        root.addWidget(logout_btn)

        self.setFixedWidth(240)

    def set_active(self, key: str) -> None:
        for k, btn in self._items.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")


class StatCard(Card):
    def __init__(self, title: str, value: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame#Card{{ background: {color}; border: 0px; border-radius: 18px; }}"
            "QLabel{ color: white; }"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)

        t = QLabel(title)
        t.setStyleSheet("font-size: 12px; font-weight: 700; color: rgba(255,255,255,0.86);")
        v = QLabel(value)
        v.setStyleSheet("font-size: 24px; font-weight: 900;")
        lay.addWidget(t)
        lay.addWidget(v)
        lay.addStretch(1)


def page_header(title: str, right_widget: QWidget | None = None, emoji: str | None = None) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)

    if emoji:
        icon = QLabel(emoji)
        icon.setStyleSheet("font-size: 18px;")
        lay.addWidget(icon)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    lay.addWidget(t)
    lay.addStretch(1)
    if right_widget:
        lay.addWidget(right_widget)
    return w

