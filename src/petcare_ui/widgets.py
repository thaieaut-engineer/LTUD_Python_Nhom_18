from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
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

