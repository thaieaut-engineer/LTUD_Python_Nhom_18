from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Theme:
    # ----- Nền ứng dụng: xám nhạt (nhịp KiotViet / lịch) -----
    bg_app: str = "#F4F5F7"
    text: str = "#1F2937"
    text_strong: str = "#111827"
    text_soft: str = "#4B5563"
    muted: str = "#6B7280"

    # ----- Sidebar / header: xanh thương hiệu -----
    sidebar_top: str = "#006848"
    sidebar_mid: str = "#008056"
    sidebar_bottom: str = "#00965E"
    sidebar_item: str = "rgba(255,255,255,0.08)"
    sidebar_item_active: str = "rgba(255,255,255,0.18)"

    # ----- Bề mặt -----
    card: str = "#FFFFFF"
    surface: str = "#FFFFFF"
    surface_alt: str = "#F0F2F1"
    surface_pink: str = "#F3F6F4"
    border: str = "#E2E5E4"
    border_strong: str = "#CBD0CF"
    border_pink: str = "#D1E8DF"

    # ----- Primary: xanh KiotViet -----
    primary: str = "#00965E"
    primary_hover: str = "#007D4F"
    primary_pressed: str = "#006B44"
    primary_left: str = "#00B078"
    primary_right: str = "#00965E"
    primary_soft: str = "rgba(0,150,94,0.12)"
    focus_ring: str = "rgba(0,150,94,0.38)"

    # ----- Phụ: xanh footer / tab phụ -----
    accent: str = "#005EB8"
    accent_soft: str = "rgba(0,94,184,0.10)"
    accent_strong: str = "#004A94"

    # ----- Trạng thái -----
    danger: str = "#B34D52"
    danger_soft: str = "#FCE8E9"
    success: str = "#007D56"
    success_soft: str = "#D1F0E8"
    warning: str = "#D97706"
    warning_soft: str = "#FEF3C7"

    # ----- Stat cards (Dashboard) -----
    stat_blue: str = "#005EB8"
    stat_orange: str = "#D97706"
    stat_green: str = "#00965E"
    stat_pink: str = "#B34D52"


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
      font-family: "Segoe UI", "Roboto", "Open Sans", "Arial";
      color: {t.text};
    }}

    QWidget {{
      background: transparent;
    }}

    QMainWindow, QDialog {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
          stop:0 #F4F5F7, stop:1 #EEEFEF);
    }}

    QToolTip {{
      background: {t.text_strong};
      color: #F9FAFB;
      border: 1px solid rgba(255,255,255,0.08);
      padding: 6px 10px;
      border-radius: 8px;
      font: 600 9pt "Segoe UI";
    }}

    QWidget#AppRoot {{
      background-color: {t.bg_app};
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
          stop:0 rgba(255,255,255,0.14), stop:1 rgba(255,255,255,0.06));
      border-left: 3px solid #7FDEC0;
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
          stop:0 {t.primary_left}, stop:1 {t.primary});
    }}

    QPushButton#PrimaryButton:hover {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 {t.primary}, stop:1 {t.primary_hover});
    }}

    QPushButton#PrimaryButton:pressed {{
      background: {t.primary_pressed};
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
      color: {t.accent_strong};
      font-weight: 700;
      background: {t.accent_soft};
    }}

    QPushButton#PinkButton:hover {{
      background: rgba(0,94,184,0.16);
      color: {t.accent};
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
      background: #923D41;
    }}

    QPushButton#DangerButton:pressed {{
      background: #7A3438;
    }}

    /* ============ CARDS & FRAMES ============ */
    QFrame#Card {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
          stop:0 #FFFFFF, stop:1 #F8FAF9);
      border: 1px solid {t.border};
      border-radius: 16px;
    }}

    QFrame[card="true"] {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
          stop:0 #FFFFFF, stop:1 #F8FAF9);
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
          stop:0 #E8EEEB, stop:1 #F0F4F2);
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
      background: #E8EEEB;
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
          stop:0 rgba(0,150,94,0.14), stop:1 rgba(0,94,184,0.10));
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
          stop:0 rgba(0,150,94,0.16), stop:1 rgba(0,94,184,0.12));
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
      background: {t.accent};
      border-top: 0px;
      color: rgba(255,255,255,0.92);
      min-height: 22px;
    }}

    QStatusBar QLabel {{
      color: rgba(255,255,255,0.92);
      background: transparent;
    }}

    QStatusBar::item {{
      border: 0px;
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
          stop:0 {t.primary_left}, stop:1 {t.primary});
      color: #FFFFFF;
      border: 0px;
      font-weight: 700;
    }}

    QDialogButtonBox QPushButton:default:hover {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 {t.primary}, stop:1 {t.primary_hover});
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
          stop:0 rgba(0,150,94,0.50), stop:1 rgba(0,94,184,0.45));
      border-radius: 4px;
      min-height: 36px;
    }}

    QScrollBar::handle:vertical:hover {{
      background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
          stop:0 rgba(0,120,75,0.75), stop:1 rgba(0,74,140,0.70));
    }}

    QScrollBar:horizontal {{
      background: transparent;
      height: 10px;
      margin: 2px;
      border-radius: 5px;
    }}

    QScrollBar::handle:horizontal {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 rgba(0,150,94,0.50), stop:1 rgba(0,94,184,0.45));
      border-radius: 4px;
      min-width: 36px;
    }}

    QScrollBar::handle:horizontal:hover {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
          stop:0 rgba(0,120,75,0.75), stop:1 rgba(0,74,140,0.70));
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
