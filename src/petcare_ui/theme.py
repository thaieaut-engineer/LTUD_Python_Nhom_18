from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Theme:
    # ----- Nền ứng dụng: xanh dương rất nhạt pha chút hồng -----
    bg_app: str = "#EFF6FF"
    text: str = "#0C1F4A"
    text_strong: str = "#0A1A3F"
    text_soft: str = "#334E7B"
    muted: str = "#64748B"

    # ----- Sidebar: navy sâu → xanh dương royal -----
    sidebar_top: str = "#0B1E3F"
    sidebar_mid: str = "#15306B"
    sidebar_bottom: str = "#1E4FB3"
    sidebar_item: str = "rgba(255,255,255,0.08)"
    sidebar_item_active: str = "rgba(255,255,255,0.18)"

    # ----- Bề mặt: card tone ngà xanh, không phải trắng phẳng -----
    card: str = "#FFFFFF"
    surface: str = "#FDFEFF"
    surface_alt: str = "#F1F6FF"
    surface_pink: str = "#FFF3F8"
    border: str = "#D6E2F7"
    border_strong: str = "#B7CAEB"
    border_pink: str = "#F9D6E4"

    # ----- Primary: Blue royal -----
    primary: str = "#2563EB"
    primary_hover: str = "#1D4ED8"
    primary_pressed: str = "#1E40AF"
    primary_left: str = "#3B82F6"
    primary_right: str = "#60A5FA"
    primary_soft: str = "rgba(37,99,235,0.12)"
    focus_ring: str = "rgba(59,130,246,0.40)"

    # ----- Accent: Hồng nhạt -----
    accent: str = "#F472B6"
    accent_soft: str = "#FCE7F3"
    accent_strong: str = "#EC4899"

    # ----- Trạng thái -----
    danger: str = "#E11D48"
    danger_soft: str = "#FEE2E8"
    success: str = "#059669"
    success_soft: str = "#D1FAE5"
    warning: str = "#D97706"
    warning_soft: str = "#FEF3C7"

    # ----- Stat cards (Dashboard) -----
    stat_blue: str = "#3B82F6"
    stat_orange: str = "#F59E0B"
    stat_green: str = "#10B981"
    stat_pink: str = "#F472B6"


THEME = Theme()


def background_image_path() -> str:
    """Đường dẫn tuyệt đối (POSIX) tới ảnh nền thú cưng, dùng trong Qt stylesheet."""
    p = Path(__file__).resolve().parents[2] / "Images_Design" / "bg_pets.png"
    return p.as_posix()


def qss() -> str:
    t = THEME
    return f"""
    /* ============ GLOBAL ============ */
    * {{
      font-family: "Segoe UI", "Inter", "Arial";
      color: {t.text};
    }}

    QWidget {{
      background: transparent;
    }}

    QMainWindow, QDialog {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
          stop:0 #EAF2FF, stop:0.55 #F5F8FF, stop:1 #FFF1F6);
    }}

    QToolTip {{
      background: {t.text_strong};
      color: #F1F5FF;
      border: 1px solid rgba(255,255,255,0.08);
      padding: 6px 10px;
      border-radius: 8px;
      font: 600 9pt "Segoe UI";
    }}

    QWidget#AppRoot {{
      background-color: #EFF6FF;
    }}

    /* ============ SIDEBAR ============ */
    QWidget#Sidebar {{
      background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
          stop:0 {t.sidebar_top}, stop:0.55 {t.sidebar_mid}, stop:1 {t.sidebar_bottom});
      border-right: 1px solid rgba(255,255,255,0.05);
    }}

    QWidget#Sidebar QLabel {{
      background: transparent;
      color: rgba(255,255,255,0.88);
    }}

    QLabel#SidebarTitle {{
      color: #FFFFFF;
      font-size: 15px;
      font-weight: 800;
      letter-spacing: 0.3px;
    }}

    QPushButton#NavItem {{
      text-align: left;
      padding: 11px 14px 11px 14px;
      border: 0px;
      border-left: 3px solid transparent;
      border-radius: 12px;
      color: rgba(255,255,255,0.82);
      background: transparent;
      font-size: 13px;
      font-weight: 600;
    }}

    QPushButton#NavItem:hover {{
      background: {t.sidebar_item};
      color: #FFFFFF;
    }}

    QPushButton#NavItem:pressed {{
      background: rgba(255,255,255,0.06);
    }}

    QPushButton#NavItem[active="true"] {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 rgba(147,197,253,0.32), stop:0.7 rgba(244,114,182,0.18), stop:1 rgba(255,255,255,0.06));
      border-left: 3px solid #93C5FD;
      color: #FFFFFF;
      font-weight: 700;
    }}

    QPushButton#Logout {{
      text-align: left;
      padding: 10px 14px;
      border: 1px solid rgba(255,255,255,0.10);
      border-radius: 12px;
      color: rgba(255,255,255,0.80);
      background: rgba(255,255,255,0.04);
      font-size: 12px;
      font-weight: 600;
    }}

    QPushButton#Logout:hover {{
      background: rgba(244,63,94,0.22);
      border: 1px solid rgba(251,113,133,0.45);
      color: #FECDD3;
    }}

    /* ============ INPUTS ============ */
    QLineEdit, QComboBox, QDateTimeEdit, QDateEdit, QTimeEdit,
    QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
      background: {t.surface};
      border: 1px solid {t.border};
      border-radius: 10px;
      padding: 9px 12px;
      min-height: 38px;
      color: {t.text};
      selection-background-color: {t.primary};
      selection-color: #FFFFFF;
    }}

    QTextEdit, QPlainTextEdit {{
      padding-top: 10px;
      padding-bottom: 10px;
      min-height: 92px;
    }}

    QLineEdit:hover, QComboBox:hover, QDateTimeEdit:hover, QDateEdit:hover,
    QTimeEdit:hover, QTextEdit:hover, QPlainTextEdit:hover,
    QSpinBox:hover, QDoubleSpinBox:hover {{
      border: 1px solid {t.border_strong};
      background: #FFFFFF;
    }}

    QLineEdit:focus, QComboBox:focus, QDateTimeEdit:focus, QDateEdit:focus,
    QTimeEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus {{
      border: 1px solid {t.primary};
      background: #FFFFFF;
    }}

    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
    QDoubleSpinBox:disabled, QTextEdit:disabled {{
      background: {t.surface_alt};
      color: {t.muted};
      border: 1px solid {t.border};
    }}

    QLineEdit::placeholder {{
      color: {t.muted};
    }}

    QSpinBox, QDoubleSpinBox {{
      padding-right: 34px;
    }}

    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
      subcontrol-origin: border;
      width: 26px;
      background: {t.surface_alt};
      border-left: 1px solid {t.border};
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button {{
      subcontrol-position: top right;
      border-top-right-radius: 10px;
    }}

    QSpinBox::down-button, QDoubleSpinBox::down-button {{
      subcontrol-position: bottom right;
      border-bottom-right-radius: 10px;
    }}

    QSpinBox::up-button:hover, QSpinBox::down-button:hover,
    QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
      background: {t.primary_soft};
    }}

    QComboBox::drop-down {{
      border: 0px;
      width: 28px;
      subcontrol-origin: padding;
      subcontrol-position: center right;
    }}

    QComboBox::down-arrow {{
      image: none;
      width: 0;
      height: 0;
      border-left: 5px solid transparent;
      border-right: 5px solid transparent;
      border-top: 6px solid {t.primary};
      margin-right: 10px;
    }}

    QComboBox:on {{
      border: 1px solid {t.primary};
    }}

    QComboBox QAbstractItemView {{
      background: #FFFFFF;
      border: 1px solid {t.border};
      border-radius: 10px;
      padding: 6px;
      outline: 0px;
      selection-background-color: {t.primary_soft};
      selection-color: {t.text_strong};
    }}

    QComboBox QAbstractItemView::item {{
      padding: 8px 10px;
      border-radius: 6px;
      min-height: 24px;
    }}

    QComboBox QAbstractItemView::item:hover {{
      background: {t.primary_soft};
    }}

    QDateTimeEdit::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down {{
      border: 0px;
      width: 30px;
    }}

    /* ============ BUTTONS ============ */
    QPushButton {{
      background: #FFFFFF;
      border: 1px solid {t.border};
      border-radius: 10px;
      padding: 9px 16px;
      color: {t.text};
      font-weight: 600;
      min-height: 34px;
    }}

    QPushButton:hover {{
      background: {t.surface_alt};
      border: 1px solid {t.primary};
      color: {t.primary};
    }}

    QPushButton:pressed {{
      background: {t.primary_soft};
      border: 1px solid {t.primary};
    }}

    QPushButton:disabled {{
      background: {t.surface_alt};
      color: {t.muted};
      border: 1px solid {t.border};
    }}

    QPushButton#PrimaryButton {{
      border: 0px;
      border-radius: 12px;
      padding: 11px 18px;
      color: #FFFFFF;
      font-weight: 700;
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 #2563EB, stop:0.6 #3B82F6, stop:1 #F472B6);
    }}

    QPushButton#PrimaryButton:hover {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 #1D4ED8, stop:0.6 #2563EB, stop:1 #EC4899);
    }}

    QPushButton#PrimaryButton:pressed {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 #1E40AF, stop:1 #DB2777);
    }}

    QPushButton#PrimaryButton:disabled {{
      background: #E2E8F0;
      color: #94A3B8;
    }}

    QPushButton#GhostButton {{
      border: 1px solid {t.border};
      border-radius: 12px;
      padding: 9px 16px;
      color: {t.primary};
      font-weight: 700;
      background: #FFFFFF;
    }}

    QPushButton#GhostButton:hover {{
      background: {t.surface_alt};
      border: 1px solid {t.primary};
      color: {t.primary_hover};
    }}

    QPushButton#GhostButton:pressed {{
      background: {t.primary_soft};
    }}

    QPushButton#PinkButton {{
      border: 0px;
      border-radius: 12px;
      padding: 9px 16px;
      color: #9D174D;
      font-weight: 700;
      background: {t.accent_soft};
    }}

    QPushButton#PinkButton:hover {{
      background: #FBCFE8;
      color: #831843;
    }}

    QPushButton#DangerButton {{
      border: 0px;
      border-radius: 12px;
      padding: 9px 16px;
      color: #FFFFFF;
      font-weight: 700;
      background: {t.danger};
    }}

    QPushButton#DangerButton:hover {{
      background: #BE123C;
    }}

    QPushButton#DangerButton:pressed {{
      background: #9F1239;
    }}

    /* ============ CARDS & FRAMES ============ */
    QFrame#Card {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
          stop:0 #FFFFFF, stop:0.6 #F6FAFF, stop:1 #FFF3F8);
      border: 1px solid {t.border};
      border-radius: 16px;
    }}

    QFrame[card="true"] {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
          stop:0 #FFFFFF, stop:0.6 #F6FAFF, stop:1 #FFF3F8);
      border: 1px solid {t.border};
      border-radius: 16px;
    }}

    QLabel#PageTitle {{
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.3px;
      color: {t.text_strong};
      background: transparent;
    }}

    QLabel#SectionTitle {{
      font-size: 13px;
      font-weight: 700;
      color: {t.text_soft};
      background: transparent;
    }}

    QLabel#Muted {{
      color: {t.muted};
      background: transparent;
    }}

    QLabel {{
      background: transparent;
    }}

    /* ============ TABLES ============ */
    QTableWidget, QTableView {{
      background: #FFFFFF;
      alternate-background-color: {t.surface_alt};
      border: 1px solid {t.border};
      border-radius: 12px;
      gridline-color: transparent;
      selection-background-color: {t.primary_soft};
      selection-color: {t.text_strong};
      outline: 0px;
    }}

    QHeaderView {{
      background: transparent;
      border: 0px;
    }}

    QHeaderView::section {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 #E7EEFC, stop:1 #FCE7F3);
      border: 0px;
      border-bottom: 1px solid {t.border};
      padding: 11px 14px;
      font-weight: 700;
      font-size: 11px;
      color: {t.text_soft};
      letter-spacing: 0.3px;
    }}

    QHeaderView::section:first {{
      border-top-left-radius: 12px;
    }}

    QHeaderView::section:last {{
      border-top-right-radius: 12px;
    }}

    QTableCornerButton::section {{
      background: #E7EEFC;
      border: 0px;
      border-bottom: 1px solid {t.border};
    }}

    QTableWidget::item, QTableView::item {{
      padding: 10px 12px;
      border: 0px;
      border-bottom: 1px solid {t.surface_alt};
    }}

    QTableWidget::item:selected, QTableView::item:selected {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 rgba(59,130,246,0.16), stop:1 rgba(244,114,182,0.12));
      color: {t.text_strong};
    }}

    QTableWidget::item:hover, QTableView::item:hover {{
      background: {t.primary_soft};
    }}

    /* ============ LIST ============ */
    QListWidget, QListView {{
      background: #FFFFFF;
      border: 1px solid {t.border};
      border-radius: 12px;
      padding: 6px;
      outline: 0px;
    }}

    QListWidget::item, QListView::item {{
      padding: 9px 12px;
      border-radius: 8px;
      margin: 2px 0px;
      color: {t.text};
    }}

    QListWidget::item:hover, QListView::item:hover {{
      background: {t.primary_soft};
    }}

    QListWidget::item:selected, QListView::item:selected {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 rgba(59,130,246,0.18), stop:1 rgba(244,114,182,0.14));
      color: {t.text_strong};
    }}

    /* ============ CHECKBOX / RADIO ============ */
    QCheckBox, QRadioButton {{
      background: transparent;
      color: {t.text};
      spacing: 8px;
      padding: 2px;
    }}

    QCheckBox::indicator, QRadioButton::indicator {{
      width: 18px;
      height: 18px;
    }}

    QCheckBox::indicator {{
      border: 1.5px solid {t.border_strong};
      border-radius: 5px;
      background: #FFFFFF;
    }}

    QCheckBox::indicator:hover {{
      border: 1.5px solid {t.primary};
    }}

    QCheckBox::indicator:checked {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
          stop:0 {t.primary}, stop:1 {t.accent});
      border: 1.5px solid {t.primary};
      image: none;
    }}

    QRadioButton::indicator {{
      border: 1.5px solid {t.border_strong};
      border-radius: 9px;
      background: #FFFFFF;
    }}

    QRadioButton::indicator:hover {{
      border: 1.5px solid {t.primary};
    }}

    QRadioButton::indicator:checked {{
      border: 5px solid {t.primary};
      background: #FFFFFF;
    }}

    /* ============ TABS ============ */
    QTabWidget::pane {{
      border: 1px solid {t.border};
      border-radius: 12px;
      background: #FFFFFF;
      top: -1px;
    }}

    QTabBar {{
      background: transparent;
    }}

    QTabBar::tab {{
      background: transparent;
      color: {t.muted};
      padding: 8px 16px;
      border: 0px;
      border-bottom: 2px solid transparent;
      font-weight: 600;
      margin-right: 4px;
    }}

    QTabBar::tab:hover {{
      color: {t.primary};
    }}

    QTabBar::tab:selected {{
      color: {t.primary};
      border-bottom: 2px solid {t.primary};
    }}

    /* ============ GROUPBOX ============ */
    QGroupBox {{
      background: #FFFFFF;
      border: 1px solid {t.border};
      border-radius: 12px;
      margin-top: 14px;
      padding: 14px;
      font-weight: 700;
      color: {t.text_soft};
    }}

    QGroupBox::title {{
      subcontrol-origin: margin;
      subcontrol-position: top left;
      left: 14px;
      padding: 0px 6px;
      background: #FFFFFF;
      color: {t.primary};
    }}

    /* ============ PROGRESS ============ */
    QProgressBar {{
      background: {t.surface_alt};
      border: 0px;
      border-radius: 8px;
      height: 10px;
      text-align: center;
      color: {t.text};
    }}

    QProgressBar::chunk {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 {t.primary_left}, stop:1 {t.accent});
      border-radius: 8px;
    }}

    /* ============ STACKED / STATUSBAR ============ */
    QStackedWidget {{
      background: transparent;
    }}

    QStatusBar {{
      background: #FFFFFF;
      border-top: 1px solid {t.border};
      color: {t.muted};
    }}

    /* ============ MENU ============ */
    QMenu {{
      background: #FFFFFF;
      border: 1px solid {t.border};
      border-radius: 10px;
      padding: 6px;
    }}

    QMenu::item {{
      padding: 8px 14px;
      border-radius: 6px;
      color: {t.text};
    }}

    QMenu::item:selected {{
      background: {t.primary_soft};
      color: {t.text_strong};
    }}

    QMenu::separator {{
      height: 1px;
      background: {t.border};
      margin: 4px 8px;
    }}

    /* ============ DIALOG BUTTON BOX ============ */
    QDialogButtonBox QPushButton {{
      min-width: 100px;
      padding: 9px 18px;
      border-radius: 10px;
    }}

    QDialogButtonBox QPushButton:default {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 #2563EB, stop:0.6 #3B82F6, stop:1 #F472B6);
      color: #FFFFFF;
      border: 0px;
      font-weight: 700;
    }}

    QDialogButtonBox QPushButton:default:hover {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 #1D4ED8, stop:0.6 #2563EB, stop:1 #EC4899);
    }}

    /* ============ MESSAGEBOX ============ */
    QMessageBox {{
      background: #FFFFFF;
    }}

    QMessageBox QLabel {{
      color: {t.text};
      font-size: 11pt;
    }}

    /* ============ SCROLLAREA ============ */
    QScrollArea {{
      background: transparent;
      border: 0px;
    }}

    QScrollArea > QWidget > QWidget {{
      background: transparent;
    }}

    /* ============ SCROLLBAR ============ */
    QScrollBar:vertical {{
      background: transparent;
      width: 10px;
      margin: 2px;
      border-radius: 5px;
    }}

    QScrollBar::handle:vertical {{
      background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
          stop:0 rgba(59,130,246,0.45), stop:1 rgba(244,114,182,0.45));
      border-radius: 4px;
      min-height: 36px;
    }}

    QScrollBar::handle:vertical:hover {{
      background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
          stop:0 rgba(29,78,216,0.70), stop:1 rgba(236,72,153,0.60));
    }}

    QScrollBar:horizontal {{
      background: transparent;
      height: 10px;
      margin: 2px;
      border-radius: 5px;
    }}

    QScrollBar::handle:horizontal {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 rgba(59,130,246,0.45), stop:1 rgba(244,114,182,0.45));
      border-radius: 4px;
      min-width: 36px;
    }}

    QScrollBar::handle:horizontal:hover {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 rgba(29,78,216,0.70), stop:1 rgba(236,72,153,0.60));
    }}

    QScrollBar::add-line, QScrollBar::sub-line {{
      width: 0px;
      height: 0px;
      background: transparent;
      border: 0px;
    }}

    QScrollBar::add-page, QScrollBar::sub-page {{
      background: transparent;
    }}
    """
