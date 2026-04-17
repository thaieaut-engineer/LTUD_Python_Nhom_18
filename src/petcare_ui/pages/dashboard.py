from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from ..theme import THEME
from ..widgets import Card, StatCard, page_header


class DashboardPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(18)

        root.addWidget(page_header("Trang chủ", emoji="📊"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.addWidget(StatCard("Doanh thu hôm nay", "0đ", THEME.stat_blue), 0, 0)
        grid.addWidget(StatCard("Thú cưng", "0", THEME.stat_orange), 0, 1)
        grid.addWidget(StatCard("Khách hàng", "0", THEME.stat_green), 1, 0)
        grid.addWidget(StatCard("Lịch hẹn hôm nay", "0", THEME.stat_pink), 1, 1)
        root.addLayout(grid)

        chart = Card()
        lay = QVBoxLayout(chart)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(14)

        title = QLabel("Doanh thu 7 ngày gần nhất")
        title.setStyleSheet("font-size: 14px; font-weight: 800;")
        lay.addWidget(title)

        empty = QLabel("0          0          0          0          0          0          0\n\n04-07     04-08     04-09     04-10     04-11     04-12     04-13")
        empty.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        empty.setStyleSheet("color: rgba(15,23,42,0.35); font-weight: 700;")
        empty.setMinimumHeight(220)
        lay.addWidget(empty)

        root.addWidget(chart, 1)

