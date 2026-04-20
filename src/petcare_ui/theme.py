from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    bg_app: str = "#F3F4F8"
    text: str = "#0F172A"
    muted: str = "#64748B"

    sidebar_top: str = "#1A1B4F"
    sidebar_bottom: str = "#2A2B6B"
    sidebar_item: str = "rgba(255,255,255,0.08)"
    sidebar_item_active: str = "rgba(255,255,255,0.14)"

    card: str = "rgba(255,255,255,0.86)"
    surface: str = "#FFFFFF"
    border: str = "rgba(15,23,42,0.08)"

    primary_left: str = "#6366F1"
    primary_right: str = "#8B5CF6"

    stat_blue: str = "#7C83FF"
    stat_orange: str = "#F5B523"
    stat_green: str = "#21C58E"
    stat_pink: str = "#FF67B3"


THEME = Theme()


def qss() -> str:
    t = THEME
    return f"""
    * {{
      font-family: "Segoe UI";
      color: {t.text};
    }}

    QWidget#AppRoot {{
      background: {t.bg_app};
    }}

    QWidget#Sidebar {{
      background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                  stop:0 {t.sidebar_top}, stop:1 {t.sidebar_bottom});
    }}

    QLabel#SidebarTitle {{
      color: rgba(255,255,255,0.92);
      font-size: 16px;
      font-weight: 700;
    }}

    QPushButton#NavItem {{
      text-align: left;
      padding: 12px 14px;
      border: 0px;
      border-radius: 12px;
      color: rgba(255,255,255,0.92);
      background: transparent;
      font-size: 13px;
      font-weight: 600;
    }}

    QPushButton#NavItem:hover {{
      background: {t.sidebar_item};
    }}

    QPushButton#NavItem[active="true"] {{
      background: {t.sidebar_item_active};
    }}

    QPushButton#Logout {{
      text-align: left;
      padding: 10px 14px;
      border: 0px;
      border-radius: 12px;
      color: rgba(255,255,255,0.82);
      background: transparent;
      font-size: 12px;
      font-weight: 600;
    }}

    QPushButton#Logout:hover {{
      background: {t.sidebar_item};
    }}

    QLineEdit, QComboBox, QDateTimeEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
      background: rgba(255,255,255,0.95);
      border: 1px solid {t.border};
      border-radius: 12px;
      padding: 10px 12px;
      min-height: 40px;
      selection-background-color: {t.primary_left};
    }}

    QTextEdit {{
      padding-top: 10px;
      padding-bottom: 10px;
      min-height: 92px;
    }}

    QLineEdit:focus, QComboBox:focus, QDateTimeEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
      border: 1px solid rgba(99,102,241,0.55);
    }}

    QSpinBox, QDoubleSpinBox {{
      padding-right: 34px; /* room for buttons */
    }}

    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
      subcontrol-origin: border;
      width: 28px;
      background: rgba(15,23,42,0.03);
      border-left: 1px solid {t.border};
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button {{
      subcontrol-position: top right;
      border-top-right-radius: 12px;
    }}

    QSpinBox::down-button, QDoubleSpinBox::down-button {{
      subcontrol-position: bottom right;
      border-bottom-right-radius: 12px;
    }}

    QSpinBox::up-button:hover, QSpinBox::down-button:hover,
    QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
      background: rgba(99,102,241,0.10);
    }}

    QComboBox::drop-down {{
      border: 0px;
      width: 26px;
    }}

    QDateTimeEdit::drop-down {{
      border: 0px;
      width: 30px;
    }}

    QPushButton#PrimaryButton {{
      border: 0px;
      border-radius: 14px;
      padding: 12px 14px;
      color: white;
      font-weight: 700;
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                  stop:0 {t.primary_left}, stop:1 {t.primary_right});
    }}

    QPushButton#PrimaryButton:hover {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                  stop:0 #5B61EA, stop:1 #7C4EF0);
    }}

    QPushButton#GhostButton {{
      border: 1px solid {t.border};
      border-radius: 14px;
      padding: 10px 14px;
      color: {t.text};
      font-weight: 700;
      background: rgba(255,255,255,0.75);
    }}

    QFrame#Card {{
      background: {t.surface};
      border: 1px solid {t.border};
      border-radius: 18px;
    }}

    QLabel#PageTitle {{
      font-size: 20px;
      font-weight: 800;
    }}

    QLabel#Muted {{
      color: {t.muted};
    }}

    QTableWidget {{
      background: transparent;
      border: 0px;
      gridline-color: rgba(15,23,42,0.08);
    }}

    QHeaderView::section {{
      background: rgba(15,23,42,0.03);
      border: 0px;
      padding: 10px 12px;
      font-weight: 700;
      color: rgba(15,23,42,0.70);
    }}

    QTableWidget::item {{
      padding-left: 10px;
      padding-right: 10px;
      height: 40px;
    }}
    """

