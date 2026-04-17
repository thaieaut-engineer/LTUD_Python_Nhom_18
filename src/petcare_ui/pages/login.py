from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from ..theme import THEME


class LoginPage(QWidget):
    logged_in = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LoginPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._bg = QWidget()
        self._bg.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {THEME.sidebar_top}, stop:1 #3B3CC9);"
        )
        root.addWidget(self._bg, 1)

        center = QVBoxLayout(self._bg)
        center.setContentsMargins(40, 34, 40, 34)
        center.setSpacing(14)
        center.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        logo = QFrame()
        logo.setFixedSize(70, 70)
        logo.setStyleSheet("background: rgba(255,255,255,0.14); border-radius: 18px;")
        logo_l = QVBoxLayout(logo)
        logo_l.setContentsMargins(0, 0, 0, 0)
        icon = QLabel("🐾")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 22px; color: rgba(255,255,255,0.85);")
        logo_l.addWidget(icon)
        center.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("Pet Care Management")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setStyleSheet("color: rgba(255,255,255,0.95); font-size: 28px; font-weight: 900;")
        subtitle = QLabel("Hệ thống quản lý chăm sóc thú cưng")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        subtitle.setStyleSheet("color: rgba(255,255,255,0.70); font-size: 12px; font-weight: 600;")
        center.addWidget(title)
        center.addWidget(subtitle)

        center.addSpacing(8)

        card = QFrame()
        card.setFixedWidth(520)
        card.setStyleSheet(
            "background: rgba(255,255,255,0.12);"
            "border: 1px solid rgba(255,255,255,0.10);"
            "border-radius: 18px;"
        )
        c = QVBoxLayout(card)
        c.setContentsMargins(28, 22, 28, 22)
        c.setSpacing(12)

        u_label = QLabel("Tên đăng nhập")
        u_label.setStyleSheet("color: rgba(255,255,255,0.75); font-weight: 700; font-size: 12px;")
        self.username = QLineEdit()
        self.username.setPlaceholderText("")
        self.username.setStyleSheet(
            "background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.10);"
            "border-radius: 12px; padding: 10px 12px; color: rgba(255,255,255,0.92);"
        )

        p_label = QLabel("Mật khẩu")
        p_label.setStyleSheet("color: rgba(255,255,255,0.75); font-weight: 700; font-size: 12px;")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setStyleSheet(
            "background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.10);"
            "border-radius: 12px; padding: 10px 12px; color: rgba(255,255,255,0.92);"
        )

        btn = QPushButton("Đăng nhập")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(44)
        btn.setStyleSheet(
            f"border: 0px; border-radius: 14px; color: white; font-weight: 800;"
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME.primary_left}, stop:1 {THEME.primary_right});"
        )
        btn.clicked.connect(self._on_login)

        hint = QLabel("Demo: nhập bất kỳ để đăng nhập")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        hint.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 11px; font-weight: 600;")

        c.addWidget(u_label)
        c.addWidget(self.username)
        c.addSpacing(4)
        c.addWidget(p_label)
        c.addWidget(self.password)
        c.addSpacing(6)
        c.addWidget(btn)
        c.addWidget(hint)

        center.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        center.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.username.returnPressed.connect(self._on_login)
        self.password.returnPressed.connect(self._on_login)

    def _on_login(self) -> None:
        user = (self.username.text() or "").strip()
        self.logged_in.emit(user or "demo")

