from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    bg_app: str = "#EEF2FF"
    text: str = "#0F172A"
    muted: str = "#64748B"

    sidebar_top: str = "#1e1b4b"
    sidebar_bottom: str = "#4338ca"
    sidebar_item: str = "rgba(255,255,255,0.10)"
    sidebar_item_active: str = "rgba(255,255,255,0.18)"

    card: str = "rgba(255,255,255,0.92)"
    surface: str = "#FFFFFF"
    border: str = "rgba(15,23,42,0.07)"

    primary_left: str = "#6366F1"
    primary_right: str = "#A855F7"

    stat_blue: str = "#6366F1"
    stat_orange: str = "#F59E0B"
    stat_green: str = "#10B981"
    stat_pink: str = "#EC4899"


THEME = Theme()


def qss() -> str:
    t = THEME
    return f"""
    * {{
      font-family: "Segoe UI";
      color: {t.text};
    }}

    QWidget#AppRoot {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
          stop:0 #EEF2FF, stop:0.45 #F8FAFC, stop:1 #FDF4FF);
    }}

    QWidget#Sidebar {{
      background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
          stop:0 {t.sidebar_top}, stop:0.55 #3730a3, stop:1 {t.sidebar_bottom});
      border-right: 1px solid rgba(255,255,255,0.06);
    }}

    QLabel#SidebarTitle {{
      color: rgba(255,255,255,0.95);
      font-size: 16px;
      font-weight: 800;
      letter-spacing: 0.3px;
    }}

    QPushButton#NavItem {{
      text-align: left;
      padding: 12px 14px 12px 11px;
      border: 0px;
      border-left: 3px solid transparent;
      border-radius: 14px;
      color: rgba(255,255,255,0.90);
      background: transparent;
      font-size: 13px;
      font-weight: 600;
    }}

    QPushButton#NavItem:hover {{
      background: {t.sidebar_item};
      color: white;
    }}

    QPushButton#NavItem[active="true"] {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 rgba(165,180,252,0.28), stop:1 rgba(255,255,255,0.10));
      border-left: 3px solid #C7D2FE;
      color: white;
    }}

    QPushButton#Logout {{
      text-align: left;
      padding: 10px 14px;
      border: 0px;
      border-radius: 12px;
      color: rgba(255,255,255,0.78);
      background: transparent;
      font-size: 12px;
      font-weight: 600;
    }}

    QPushButton#Logout:hover {{
      background: rgba(255,255,255,0.10);
      color: rgba(255,255,255,0.95);
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
          stop:0 #4F46E5, stop:1 #9333EA);
    }}

    QPushButton#PrimaryButton:pressed {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 #4338CA, stop:1 #7E22CE);
    }}

    QPushButton#GhostButton {{
      border: 1px solid {t.border};
      border-radius: 14px;
      padding: 10px 14px;
      color: {t.text};
      font-weight: 700;
      background: rgba(255,255,255,0.88);
    }}

    QPushButton#GhostButton:hover {{
      background: rgba(255,255,255,1);
      border: 1px solid rgba(99,102,241,0.25);
    }}

    QFrame#Card {{
      background: {t.surface};
      border: 1px solid {t.border};
      border-radius: 20px;
    }}

    QLabel#PageTitle {{
      font-size: 21px;
      font-weight: 800;
      letter-spacing: -0.3px;
      color: #0f172a;
    }}

    QLabel#Muted {{
      color: {t.muted};
    }}

    QTableWidget {{
      background: rgba(255,255,255,0.45);
      border: 1px solid rgba(15,23,42,0.06);
      border-radius: 14px;
      gridline-color: rgba(15,23,42,0.06);
    }}

    QHeaderView::section {{
      background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
          stop:0 rgba(99,102,241,0.08), stop:1 rgba(99,102,241,0.02));
      border: 0px;
      border-bottom: 1px solid rgba(15,23,42,0.06);
      padding: 11px 12px;
      font-weight: 800;
      font-size: 11px;
      color: rgba(15,23,42,0.72);
    }}

    QTableWidget::item {{
      padding-left: 10px;
      padding-right: 10px;
      height: 42px;
    }}

    QTableWidget::item:selected {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 rgba(99,102,241,0.18), stop:1 rgba(168,85,247,0.12));
      color: {t.text};
    }}

    QTableWidget::item:hover {{
      background: rgba(99,102,241,0.07);
    }}

    QListWidget {{
      outline: none;
    }}

    QListWidget::item {{
      padding: 8px 10px;
      border-radius: 8px;
    }}

    QListWidget::item:hover {{
      background: rgba(99,102,241,0.08);
    }}

    QListWidget::item:selected {{
      background: rgba(99,102,241,0.14);
      color: {t.text};
    }}

    QScrollBar:vertical {{
      background: rgba(15,23,42,0.04);
      width: 10px;
      margin: 0px;
      border-radius: 5px;
    }}

    QScrollBar::handle:vertical {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 rgba(99,102,241,0.45), stop:1 rgba(168,85,247,0.45));
      border-radius: 5px;
      min-height: 36px;
    }}

    QScrollBar::handle:vertical:hover {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 rgba(79,70,229,0.65), stop:1 rgba(147,51,234,0.55));
    }}

    QScrollBar:horizontal {{
      background: rgba(15,23,42,0.04);
      height: 10px;
      margin: 0px;
      border-radius: 5px;
    }}

    QScrollBar::handle:horizontal {{
      background: rgba(99,102,241,0.45);
      border-radius: 5px;
      min-width: 36px;
    }}

    QScrollBar::add-line, QScrollBar::sub-line {{
      width: 0px;
      height: 0px;
    }}
    """

