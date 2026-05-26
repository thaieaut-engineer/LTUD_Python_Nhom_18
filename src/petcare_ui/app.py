from __future__ import annotations

import os
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt, QDateTime, QEvent, QObject, QThread, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QIcon, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSizePolicy,
    QPlainTextEdit,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .theme import THEME, background_image_path, qss
from .pages.dashboard import DashboardView
from src.petcare_backend.services import auth_service
from src.petcare_backend.services import customer_service, pet_service, service_service
from src.petcare_backend.services import user_service
from src.petcare_backend.services import appointment_service
from src.petcare_backend.services import invoice_service, payment_service
from src.petcare_backend.services import product_service
from src.petcare_backend.services import report_service
from src.petcare_backend.models import Customer, Pet, Product, Service
from src.petcare_backend.session import Session


APPOINTMENT_STATUSES = ("Chờ xử lý", "Đang thực hiện", "Hoàn thành", "Hủy")
APPOINTMENT_ACTIVE_STATUSES = ("Chờ xử lý", "Đang thực hiện")
APPOINTMENT_HISTORY_STATUSES = ("Hoàn thành", "Hủy")

_APPT_TAB_BTN_QSS = f"""
QPushButton {{
  background: rgba(255,255,255,0.85);
  border: 1px solid {THEME.border_pink};
  border-radius: 10px;
  padding: 6px 16px;
  font: 700 9pt 'Segoe UI';
  color: {THEME.text_soft};
  min-width: 96px;
}}
QPushButton:checked {{
  background: {THEME.accent};
  border: 1px solid {THEME.accent_strong};
  color: #FFFFFF;
}}
QPushButton:hover {{
  border: 1px solid {THEME.accent};
}}
"""

_APPT_STATUS_COLORS = {
    "Chờ xử lý": THEME.warning,
    "Đang thực hiện": THEME.accent,
    "Hoàn thành": THEME.success,
    "Hủy": THEME.danger,
}

_APPT_STATUS_ICONS = {
    "Chờ xử lý": "🟡",
    "Đang thực hiện": "🔵",
    "Hoàn thành": "🟢",
    "Hủy": "🔴",
}

_APPT_STATUS_TOGGLE_SPECS: dict[str, tuple[str, str, str]] = {
    "Đang thực hiện": ("▶ Đang TH", THEME.accent, THEME.accent_soft),
    "Hoàn thành": ("✓ Hoàn thành", THEME.success, THEME.success_soft),
    "Hủy": ("✕ Hủy", THEME.danger, THEME.danger_soft),
}

_APPT_STATUS_COMBO_QSS = """
QComboBox#AppointmentStatusCombo {
  min-height: 28px;
  max-height: 32px;
  padding: 2px 8px 2px 10px;
  font: 600 10pt 'Segoe UI';
  border-radius: 8px;
}
QComboBox#AppointmentStatusCombo::drop-down {
  width: 22px;
}
QComboBox#AppointmentStatusCombo QAbstractItemView::item {
  min-height: 28px;
  padding: 6px 10px;
}
"""


def _status_display(label: str) -> str:
    return f"{_APPT_STATUS_ICONS.get(label, '⚪')}  {label}"


def _populate_appointment_status_combo(combo: QComboBox) -> None:
    combo.clear()
    for label in APPOINTMENT_STATUSES:
        combo.addItem(_status_display(label), label)


def _status_toggle_btn_qss(fg: str, bg_soft: str, *, active: bool) -> str:
    if active:
        return (
            f"QPushButton{{background:{fg};color:#FFFFFF;border:1px solid {fg};"
            f"border-radius:10px;padding:6px 8px;font:700 10pt 'Segoe UI';"
            f"min-height:34px;max-height:38px;}}"
            f"QPushButton:hover{{background:{fg};color:#FFFFFF;}}"
        )
    return (
        f"QPushButton{{background:{bg_soft};color:{fg};border:1px solid {fg}66;"
        f"border-radius:10px;padding:6px 8px;font:700 10pt 'Segoe UI';"
        f"min-height:34px;max-height:38px;}}"
        f"QPushButton:hover{{border:1px solid {fg};background:{fg}18;}}"
    )


def _appointment_info_chip(icon: str, text: str) -> QLabel:
    lbl = QLabel(f"{icon}  {text}")
    lbl.setStyleSheet(
        "color:#334155;font:600 9pt 'Segoe UI';"
        "background:rgba(255,255,255,0.94);border:1px solid #E2E8F0;"
        "border-radius:8px;padding:5px 10px;"
    )
    lbl.setWordWrap(True)
    return lbl

# Nut thao tac trong bang nhan vien: global QPushButton co min-height 34px + padding lon;
# dat trong QTableWidget de bi cat neu hang khong du cao — gon lai va can giua doc.
_EMPLOYEE_ROW_BTN_QSS = f"""
QPushButton {{
  background: #FFFFFF;
  border: 1px solid {THEME.border};
  border-radius: 8px;
  padding: 4px 10px;
  color: {THEME.text};
  font: 600 9pt 'Segoe UI';
  min-height: 24px;
  max-height: 30px;
}}
QPushButton:hover {{
  background: {THEME.surface_alt};
  border: 1px solid {THEME.primary};
  color: {THEME.primary};
}}
QPushButton:pressed {{
  background: {THEME.primary_soft};
  border: 1px solid {THEME.primary};
}}
"""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ui_path(name: str) -> str:
    return str(_repo_root() / "ui" / name)


def _clear_grid_layout(grid: QGridLayout) -> None:
    while grid.count():
        item = grid.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()


_ACTION_ICON_PIX = 20
_BITMAP_ICON_CACHE: dict[tuple[str, str, int], QIcon] = {}


def _tinted_bitmap_icon(filename: str, fg_hex: str, px: int = _ACTION_ICON_PIX) -> QIcon | None:
    """Tai PNG den-trang tu ui/icons, to mau fg_hex, scale px (cache)."""
    cache_key = (filename, fg_hex, px)
    if cache_key in _BITMAP_ICON_CACHE:
        return _BITMAP_ICON_CACHE[cache_key]

    path = _repo_root() / "ui" / "icons" / filename
    if not path.is_file():
        return None

    raw = QPixmap(str(path))
    if raw.isNull():
        return None

    scaled = raw.scaled(
        px * 2,
        px * 2,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    img = scaled.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    w, h = img.width(), img.height()
    fg = QColor(fg_hex) if fg_hex.startswith("#") and len(fg_hex) == 7 else QColor("#334155")
    out = QImage(w, h, QImage.Format.Format_ARGB32)
    out.fill(0)

    for y in range(h):
        for x in range(w):
            c = QColor(img.pixelColor(x, y))
            if c.alpha() < 8:
                continue
            lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0
            strength = 1.0 - lum
            if strength < 0.04:
                continue
            a = int(min(255, strength * (c.alpha() / 255.0) * 255))
            out.setPixelColor(x, y, QColor(fg.red(), fg.green(), fg.blue(), a))

    icon = QIcon(QPixmap.fromImage(out))
    _BITMAP_ICON_CACHE[cache_key] = icon
    return icon


def _action_icon(kind: str, fg_hex: str) -> QIcon:
    """Icon thao tac: edit/trash uu tien file ui/icons; view/hide ve vector."""
    if kind == "edit":
        ic = _tinted_bitmap_icon("action_edit.png", fg_hex)
        if ic is not None:
            return ic
    elif kind == "trash":
        ic = _tinted_bitmap_icon("action_trash.png", fg_hex)
        if ic is not None:
            return ic
    return _vector_action_icon(kind, fg_hex)


def _vector_action_icon(kind: str, fg_hex: str) -> QIcon:
    """Icon don sac ~22px: but, thung rac, mat, mat gach (an)."""
    hx = fg_hex.strip()
    c = QColor(hx) if hx.startswith("#") and len(hx) == 7 else QColor("#334155")
    d = 22
    pix = QPixmap(d, d)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(c)
    pen.setWidthF(1.75)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if kind == "edit":
        painter.drawLine(5, 15, 14, 6)
        painter.drawLine(14, 6, 17, 4)
        painter.drawLine(5, 15, 3, 17)
    elif kind == "trash":
        painter.drawLine(8, 6, 8, 7)
        painter.drawLine(14, 6, 14, 7)
        painter.drawLine(7, 7, 15, 7)
        painter.drawLine(7, 7, 7, 17)
        painter.drawLine(15, 7, 15, 17)
        painter.drawLine(7, 17, 15, 17)
        painter.drawLine(9, 10, 9, 15)
        painter.drawLine(13, 10, 13, 15)
    elif kind == "view":
        painter.drawEllipse(3, 7, 16, 10)
        painter.setBrush(c)
        painter.drawEllipse(9, 10, 4, 4)
        painter.setBrush(Qt.BrushStyle.NoBrush)
    elif kind == "hide":
        painter.drawEllipse(3, 7, 16, 10)
        painter.setBrush(c)
        painter.drawEllipse(9, 10, 4, 4)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        slash = QPen(c)
        slash.setWidthF(2.35)
        slash.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(slash)
        painter.drawLine(4, 5, 18, 19)
    painter.end()
    return QIcon(pix)


def _build_action_icon_button(
    icon: QIcon,
    tooltip: str,
    bg: str,
    fg: str,
    *,
    hover: str | None = None,
    hover_fg: str | None = None,
) -> QPushButton:
    btn = QPushButton()
    btn.setIcon(icon)
    btn.setIconSize(QSize(_ACTION_ICON_PIX, _ACTION_ICON_PIX))
    btn.setToolTip(tooltip)
    btn.setAccessibleName(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    hover_bg = hover or bg
    hover_color = hover_fg or fg
    btn.setStyleSheet(
        "QPushButton{"
        f"background:{bg};color:{fg};border:none;"
        "padding:6px;border-radius:8px;"
        "min-height:32px;min-width:32px;max-height:34px;max-width:40px;"
        "}"
        "QPushButton:hover{"
        f"background:{hover_bg};color:{hover_color};"
        "}"
    )
    btn.setFixedSize(36, 32)
    return btn


def _build_action_button(
    text: str,
    bg: str,
    fg: str,
    *,
    hover: str | None = None,
    hover_fg: str | None = None,
) -> QPushButton:
    """Tao nut action dung trong cot 'Thao tac' cua bang.

    - Override min-height/min-width tu QSS global (de tat min-height:34px).
    - Tinh chieu rong toi thieu theo do dai chu (font metrics) + padding,
      tranh truong hop ResizeToContents bop hep nut.
    """
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    hover_bg = hover or bg
    hover_color = hover_fg or fg
    btn.setStyleSheet(
        "QPushButton{"
        f"background:{bg};color:{fg};border:none;"
        "padding:4px 14px;border-radius:8px;"
        "font:700 10pt 'Segoe UI';"
        "min-height:32px;min-width:0;"
        "}"
        "QPushButton:hover{"
        f"background:{hover_bg};color:{hover_color};"
        "}"
    )
    btn.setMinimumHeight(32)
    fm = QFontMetrics(btn.font())
    text_w = fm.horizontalAdvance(text)
    btn.setMinimumWidth(text_w + 32)
    return btn


def _wrap_action_buttons(
    buttons: list[QPushButton],
    *,
    trailing_stretch: bool = True,
    margins: tuple[int, int, int, int] = (8, 4, 8, 4),
) -> QWidget:
    """Goi list nut action vao 1 QWidget can chinh san sang gan vao QTableWidget.

    Tinh san minimumSize de QHeaderView::ResizeToContents lam viec dung.
    """
    w = QWidget()
    lay = QHBoxLayout(w)
    m_l, m_t, m_r, m_b = margins
    lay.setContentsMargins(m_l, m_t, m_r, m_b)
    lay.setSpacing(8)
    total_w = m_l + m_r
    max_h = 0
    for b in buttons:
        lay.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        total_w += b.minimumWidth() + 8
        max_h = max(max_h, b.minimumHeight())
    if trailing_stretch:
        lay.addStretch(1)
    w.setMinimumSize(max(total_w, 60), max_h + m_t + m_b)
    return w


class _LoginWorker(QThread):
    """Dang nhap tren luong phu — tranh 'Not Responding' khi MySQL cham/khong ket noi."""

    finished_with_result = pyqtSignal(object, object)

    def __init__(self, username: str, password: str) -> None:
        super().__init__()
        self._username = username
        self._password = password

    def run(self) -> None:
        try:
            user = auth_service.login(self._username, self._password)
            self.finished_with_result.emit(user, None)
        except Exception as exc:
            self.finished_with_result.emit(None, exc)


class PetBackground(QLabel):
    """Ảnh nền thú cưng tự động scale theo kích thước parent (cover + overlay)."""

    def __init__(
        self,
        parent: QWidget,
        image_path: str,
        overlay_color: tuple[int, int, int, int] = (244, 245, 247, 170),
    ) -> None:
        super().__init__(parent)
        self._pix = QPixmap(image_path)
        self._overlay = overlay_color
        self.setScaledContents(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.lower()
        parent.installEventFilter(self)
        self._sync_geometry()

    def _sync_geometry(self) -> None:
        p = self.parentWidget()
        if p is None:
            return
        self.setGeometry(0, 0, p.width(), p.height())
        self.update()

    def eventFilter(self, obj, event):  # type: ignore[override]
        if event.type() == QEvent.Type.Resize:
            self._sync_geometry()
        return False

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if not self._pix.isNull():
            scaled = self._pix.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        r, g, b, a = self._overlay
        if a > 0:
            painter.fillRect(self.rect(), self._qcolor(r, g, b, a))
        painter.end()

    @staticmethod
    def _qcolor(r: int, g: int, b: int, a: int):
        from PyQt6.QtGui import QColor

        return QColor(r, g, b, a)


class PetCareApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pet Care Management")
        self.resize(1100, 720)

        self._apply_theme()

        self._login = uic.loadUi(_ui_path("login.ui"))
        self._main = uic.loadUi(_ui_path("main.ui"))
        self._pages: dict[str, QWidget] = {}
        # demo list cu - da thay bang DB rows (_appointments_rows)
        self._demo_appointments: list[dict[str, str | list[str]]] = []
        self._pet_images: dict[tuple[int, int], str] = {}
        self._product_images: dict[int, str] = {}
        self._customers: list[Customer] = []
        self._pets: list[Pet] = []
        self._pets_thumb: int = 56
        self._services_list: list[Service] = []
        self._products_list: list[Product] = []
        self._employees_list: list = []
        self._employees_stats: list = []
        self._per_pet_service_container: QWidget | None = None
        self._per_pet_service_rows_layout: QVBoxLayout | None = None
        self._per_pet_service_combos: dict[str, QComboBox] = {}
        self._products_viewport: QWidget | None = None
        self._invoice_payment_mode: str = "unpaid"
        self._login_worker: _LoginWorker | None = None

        self._bg_path: str = background_image_path()

        # IMPORTANT: QMainWindow.setCentralWidget will delete the previous widget.
        # Use a stacked root to switch between login/main safely.
        self._root_stack = QStackedWidget()
        self._root_stack.addWidget(self._login)
        self._root_stack.addWidget(self._main)
        self.setCentralWidget(self._root_stack)
        self._root_stack.setCurrentWidget(self._login)
        self._wire_login()
        self._wire_main()
        self._install_menubar()

        self._install_backgrounds()

        self._load_pages()
        # Chi khoi tao UI pages; du lieu se load tu MySQL sau khi dang nhap thanh cong.
        self._init_catalog_pages()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if (
            self._products_viewport is not None
            and obj is self._products_viewport
            and event.type() == QEvent.Type.Resize
        ):
            self._sync_products_grid_metrics()
        return super().eventFilter(obj, event)

    def _install_pet_background(
        self,
        widget: QWidget,
        overlay_color: tuple[int, int, int, int] = (244, 245, 247, 140),
    ) -> PetBackground | None:
        if not self._bg_path or not Path(self._bg_path).exists():
            return None
        return PetBackground(widget, self._bg_path, overlay_color=overlay_color)

    def _install_backgrounds(self) -> None:
        login_root = self._login.findChild(QWidget, "LoginPage") or self._login
        self._install_pet_background(login_root, overlay_color=(0, 104, 72, 150))

        app_root = self._main.centralWidget()
        if app_root is not None:
            app_root.setObjectName("AppRoot")
            app_root.style().unpolish(app_root)
            app_root.style().polish(app_root)
            self._install_pet_background(app_root, overlay_color=(244, 245, 247, 72))

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss())

    def _wire_login(self) -> None:
        self._login.LoginButton.clicked.connect(self._on_login)
        self._login.usernameEdit.returnPressed.connect(self._on_login)
        self._login.passwordEdit.returnPressed.connect(self._on_login)
        self._install_register_button()

    def _install_register_button(self) -> None:
        """Login UI chua co nut Dang ky -> chen runtime."""
        if hasattr(self._login, "registerButton"):
            return
        card = self._login.findChild(QWidget, "LoginCard")
        if card is None:
            return
        layout = card.layout()
        if layout is None:
            return

        btn = QPushButton("Tạo tài khoản (Nhân viên)")
        btn.setObjectName("GhostButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.10);color:rgba(255,255,255,0.85);"
            "border:1px solid rgba(255,255,255,0.22);padding:9px 12px;border-radius:12px;"
            "font:700 10pt 'Segoe UI';}"
            "QPushButton:hover{background:rgba(255,255,255,0.16);border:1px solid rgba(127,222,192,0.65);}"
        )
        btn.clicked.connect(self._show_register_dialog)

        # insert under LoginButton (best effort)
        inserted = False
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if w is not None and w.objectName() == "LoginButton":
                layout.insertWidget(i + 1, btn)
                inserted = True
                break
        if not inserted:
            layout.addWidget(btn)

        # update hint
        hint = self._login.findChild(QLabel, "Hint")
        if hint is not None:
            hint.setText("Dùng tài khoản được cấp hoặc tạo tài khoản nhân viên để đăng nhập.")

        self._login.registerButton = btn  # type: ignore[attr-defined]

    def _install_menubar(self) -> None:
        from PyQt6.QtGui import QAction

        menubar = self.menuBar()
        menubar.clear()
        account_menu = menubar.addMenu("Tài khoản")

        change_pw = QAction("Đổi mật khẩu...", self)
        change_pw.triggered.connect(self._show_change_password_dialog)
        account_menu.addAction(change_pw)

        # Admin menu (will be hidden for non-admin)
        admin_menu = menubar.addMenu("Quản trị")
        manage_users = QAction("Quản lý người dùng...", self)
        manage_users.triggered.connect(self._show_user_admin_dialog)
        admin_menu.addAction(manage_users)

        self._admin_menu = admin_menu
        self._action_manage_users = manage_users
        # mac dinh an cho den khi dang nhap admin
        admin_menu.menuAction().setVisible(False)
        manage_users.setVisible(False)

        account_menu.addSeparator()

        logout_action = QAction("Đăng xuất", self)
        logout_action.triggered.connect(self._on_logout)
        account_menu.addAction(logout_action)

    def _wire_main(self) -> None:
        self._main.navDashboard.clicked.connect(lambda: self._set_active("dashboard"))
        self._main.navCustomers.clicked.connect(lambda: self._set_active("customers"))
        self._main.navPets.clicked.connect(lambda: self._set_active("pets"))
        self._main.navServices.clicked.connect(lambda: self._set_active("services"))
        if hasattr(self._main, "navProducts"):
            self._main.navProducts.clicked.connect(lambda: self._set_active("products"))
        self._main.navAppointments.clicked.connect(lambda: self._set_active("appointments"))
        self._main.navInvoices.clicked.connect(lambda: self._set_active("invoices"))
        if hasattr(self._main, "navEmployees"):
            self._main.navEmployees.clicked.connect(lambda: self._set_active("employees"))
        self._main.logoutButton.clicked.connect(self._on_logout)

    def _load_pages(self) -> None:
        stack = self._main.stack

        def add(key: str, ui_file: str) -> None:
            w = uic.loadUi(_ui_path(ui_file))
            w.setProperty("page_key", key)
            stack.addWidget(w)
            self._pages[key] = w

        def add_widget(key: str, widget: QWidget) -> None:
            widget.setProperty("page_key", key)
            stack.addWidget(widget)
            self._pages[key] = widget

        add_widget("dashboard", DashboardView())
        add("customers", "customers.ui")
        add("pets", "pets.ui")
        add("services", "services.ui")
        add("products", "products.ui")
        add("appointments", "appointments.ui")
        ap_lay = self._pages["appointments"].layout()
        if isinstance(ap_lay, QVBoxLayout) and ap_lay.count() >= 2:
            ap_lay.setStretch(1, 1)

        add("invoices", "invoices.ui")
        add("employees", "employees.ui")

    def _init_catalog_pages(self) -> None:
        """Khoi tao cac page danh muc (B2/B3/B4) + nghiep vu (C1-C3). Du lieu se load sau login."""
        customers_page = self._pages.get("customers")
        if customers_page:
            table: QTableWidget = customers_page.customersTable
            self._setup_table(table)
            self._insert_add_customer_button(customers_page)
            customers_page.searchEdit.textChanged.connect(lambda text: self._reload_customers(text))
            customers_page.viewPetsButton.clicked.connect(self._on_view_customer_pets)

        services_page = self._pages.get("services")
        if services_page:
            table: QTableWidget = services_page.servicesTable
            self._setup_table(table)
            if hasattr(services_page, "addServiceButton"):
                services_page.addServiceButton.clicked.connect(self._on_add_service_clicked)
            if hasattr(services_page, "searchEdit"):
                services_page.searchEdit.textChanged.connect(
                    lambda text: self._reload_services(text)
                )

        products_page = self._pages.get("products")
        if products_page:
            if hasattr(products_page, "productsScrollArea"):
                psa: QScrollArea = products_page.productsScrollArea
                # widgetResizable(True) keo cao bang viewport -> QGridLayout dan doc hang,
                # thẻ neo tren nhung o noi dung bi gian -> lech hang / khoang trong lon.
                psa.setWidgetResizable(False)
                psa.setFrameShape(QFrame.Shape.NoFrame)
                self._products_viewport = psa.viewport()
                self._products_viewport.installEventFilter(self)
            if hasattr(products_page, "addProductButton"):
                products_page.addProductButton.clicked.connect(self._on_add_product_clicked)
            if hasattr(products_page, "categoryFilterCombo"):
                combo = products_page.categoryFilterCombo
                combo.clear()
                combo.addItem("Tất cả loại", "")
                combo.addItem("Đồ ăn", "DO_AN")
                combo.addItem("Phụ kiện", "PHU_KIEN")
                combo.currentIndexChanged.connect(lambda _: self._reload_products())
            if hasattr(products_page, "searchEdit"):
                products_page.searchEdit.textChanged.connect(
                    lambda text: self._reload_products(text)
                )

        pets_page = self._pages.get("pets")
        if pets_page:
            if hasattr(pets_page, "petsTable"):
                ptable: QTableWidget = pets_page.petsTable
                self._setup_table(ptable)
                ptable.setColumnCount(7)
                ptable.setHorizontalHeaderLabels(
                    ["Ảnh", "Tên", "Loài", "Giống", "Tuổi", "Chủ", "Thao tác"]
                )
                ph = ptable.horizontalHeader()
                ph.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
                ptable.setColumnWidth(0, 76)
                ph.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                ph.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
                ph.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
                ph.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
                ph.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
                ph.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
                ptable.setColumnWidth(6, 230)
                ptable.cellDoubleClicked.connect(self._on_pet_image_double_clicked)
            pets_page.customerFilterCombo.currentIndexChanged.connect(lambda _: self._reload_pets())
            pets_page.addPetButton.clicked.connect(self._on_add_pet_clicked)

        ap_page = self._pages.get("appointments")
        if ap_page:
            # services combo
            ap_page.serviceCombo.clear()
            ap_page.serviceCombo.addItem("Chọn dịch vụ", 0)
            for s in self._services_list:
                ap_page.serviceCombo.addItem(f"{s.name} ({int(s.price):,}đ)".replace(",", "."), s.id)

            self._build_per_pet_service_container(ap_page)
            ap_page.timeEdit.setDateTime(QDateTime.currentDateTime().addSecs(3600))

            ap_page.customerCombo.currentIndexChanged.connect(lambda _: self._refresh_appointment_pet_list())
            ap_page.petListWidget.itemChanged.connect(self._on_appointment_pet_check_changed)
            ap_page.confirmButton.clicked.connect(self._on_confirm_appointment_db)
            if hasattr(ap_page, "addNewCustomerButton"):
                ap_page.addNewCustomerButton.clicked.connect(self._on_quick_add_customer_for_appointment)

            table: QTableWidget = ap_page.appointmentsTable
            self._setup_appointments_table(table)
            self._appointment_list_mode = "active"
            self._setup_appointment_list_tabs(ap_page)
            table.cellClicked.connect(lambda r, c: self._on_appointment_row_clicked(r, c))

            if hasattr(ap_page, "detailTitle"):
                ap_page.detailTitle.setVisible(False)
            if hasattr(ap_page, "appointmentDetailEdit"):
                ap_page.appointmentDetailEdit.setVisible(False)

        inv_page = self._pages.get("invoices")
        if inv_page:
            if hasattr(inv_page, "createInvoiceButton"):
                inv_page.createInvoiceButton.clicked.connect(self._show_invoice_center)
            if hasattr(inv_page, "createRetailButton"):
                inv_page.createRetailButton.clicked.connect(self._show_retail_pos_dialog)
            if hasattr(inv_page, "typeFilterCombo"):
                combo = inv_page.typeFilterCombo
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("Tất cả hoá đơn", "")
                combo.addItem("HĐ Dịch vụ", "SERVICE")
                combo.addItem("HĐ Bán lẻ", "RETAIL")
                combo.blockSignals(False)
                combo.currentIndexChanged.connect(lambda _: self._reload_invoices_table())
            if hasattr(inv_page, "searchEdit"):
                inv_page.searchEdit.textChanged.connect(lambda _: self._reload_invoices_table())
            self._setup_invoice_payment_tabs(inv_page)
            self._install_invoices_table(inv_page)

        emp_page = self._pages.get("employees")
        if emp_page:
            table: QTableWidget = emp_page.employeesTable
            self._setup_table(table)
            evh = table.verticalHeader()
            evh.setDefaultSectionSize(64)
            evh.setMinimumSectionSize(62)
            if hasattr(emp_page, "searchEdit"):
                emp_page.searchEdit.textChanged.connect(lambda _: self._render_employees_table())
            if hasattr(emp_page, "addEmployeeButton"):
                emp_page.addEmployeeButton.clicked.connect(self._on_add_employee_clicked)

    @staticmethod
    def _has_active_session() -> bool:
        return Session.current() is not None

    def _reload_catalog_data(self) -> None:
        """Load khach hang/thu cung/dich vu/san pham tu MySQL va render UI."""
        if not self._has_active_session():
            return
        steps = (
            self._reload_employees,
            lambda: self._reload_customers(None),
            self._reload_services,
            self._reload_products,
            self._reload_pets,
            self._refresh_pets_customer_filter,
            self._refresh_appointments_customer_combo,
            self._refresh_appointments_employee_filter,
            self._reload_appointments_table,
            self._reload_invoices_table,
        )
        for step in steps:
            step()

        dash = self._pages.get("dashboard")
        if isinstance(dash, DashboardView):
            try:
                dash.reload()
            except Exception:
                pass

    def _strip_invoice_page_placeholders(self, inv_page: QWidget) -> None:
        """Go spacer/emptyLabel trong .ui (gay khoang trong lon truoc bang)."""
        vlay = inv_page.layout()
        if not isinstance(vlay, QVBoxLayout):
            return
        remove_idx: list[int] = []
        for i in range(vlay.count()):
            item = vlay.itemAt(i)
            if item is None:
                continue
            if item.spacerItem() is not None:
                remove_idx.append(i)
                continue
            w = item.widget()
            if w is not None and w.objectName() == "emptyLabel":
                remove_idx.append(i)
        for i in reversed(remove_idx):
            taken = vlay.takeAt(i)
            if taken is None:
                continue
            w = taken.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _install_invoices_table(self, inv_page: QWidget) -> None:
        """Chen bang hoa don; xoa placeholder spacer trong .ui."""
        layout = inv_page.layout()
        if not isinstance(layout, QVBoxLayout):
            return
        self._strip_invoice_page_placeholders(inv_page)
        if hasattr(inv_page, "invoicesTable"):
            return
        table = QTableWidget()
        table.setObjectName("invoicesTable")
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(
            [
                "Mã HĐ",
                "Loại",
                "Ngày",
                "Khách hàng",
                "Người tạo",
                "Tổng tiền",
                "Trạng thái",
                "Thao tác",
            ]
        )
        self._setup_table(table)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        layout.addWidget(table, 1)
        inv_page.invoicesTable = table  # type: ignore[attr-defined]

    def _reload_invoices_table(self) -> None:
        if not self._has_active_session():
            return
        inv_page = self._pages.get("invoices")
        if not inv_page or not hasattr(inv_page, "invoicesTable"):
            return

        # Filter: type
        invoice_type: str | None = None
        if hasattr(inv_page, "typeFilterCombo"):
            data = inv_page.typeFilterCombo.currentData()
            if isinstance(data, str) and data:
                invoice_type = data

        # Filter: search local-side (theo invoice_no / customer_name)
        rows = invoice_service.list_recent(limit=200, invoice_type=invoice_type)

        if hasattr(inv_page, "searchEdit"):
            q = (inv_page.searchEdit.text() or "").strip().lower()
            if q:
                rows = [
                    r for r in rows
                    if q in str(r.get("invoice_no") or "").lower()
                    or q in str(r.get("customer_name") or "").lower()
                ]

        want_pay = (
            "DA_TT" if getattr(self, "_invoice_payment_mode", "unpaid") == "paid" else "CHUA_TT"
        )
        rows = [
            r
            for r in rows
            if str(r.get("payment_status") or "CHUA_TT") == want_pay
        ]

        self._invoice_rows = rows  # type: ignore[attr-defined]

        table: QTableWidget = inv_page.invoicesTable
        table.setRowCount(len(rows))
        for r, i in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(str(i.get("invoice_no", ""))))
            inv_type = str(i.get("invoice_type") or "SERVICE")
            type_label = "Bán lẻ" if inv_type == "RETAIL" else "Dịch vụ"
            type_item = QTableWidgetItem(type_label)
            type_item.setForeground(QColor(THEME.accent if inv_type == "RETAIL" else THEME.success))
            table.setItem(r, 1, type_item)
            issued = i.get("issued_at")
            issued_txt = issued.strftime("%d/%m/%Y %H:%M") if issued else ""
            table.setItem(r, 2, QTableWidgetItem(issued_txt))
            table.setItem(r, 3, QTableWidgetItem(str(i.get("customer_name") or "(khách lẻ)")))
            creator = i.get("created_by_name") or ""
            table.setItem(r, 4, QTableWidgetItem(str(creator)))
            total = float(i.get("total_amount") or 0)
            table.setItem(r, 5, QTableWidgetItem(f"{int(total):,}đ".replace(",", ".")))
            status = str(i.get("payment_status", "CHUA_TT"))
            status_label = "Đã TT" if status == "DA_TT" else ("Chưa TT" if status == "CHUA_TT" else status)
            table.setItem(r, 6, QTableWidgetItem(status_label))

            invoice_id = int(i["invoice_id"])
            table.setCellWidget(
                r,
                7,
                self._make_invoice_actions(
                    invoice_id=invoice_id, payment_status=status
                ),
            )

        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(7, 260)

    def _make_invoice_actions(
        self, *, invoice_id: int, payment_status: str = "CHUA_TT"
    ) -> QWidget:
        btn_view = _build_action_icon_button(
            _action_icon("view", "#3730A3"),
            "Xem chi tiết",
            "#EEF2FF",
            "#3730A3",
            hover="#E0E7FF",
        )
        btn_view.clicked.connect(lambda: self._show_invoice_detail(invoice_id))

        actions: list[QWidget] = [btn_view]
        if payment_status != "DA_TT":
            btn_pay = _build_action_button(
                "Thanh toán", "#DCFCE7", "#166534", hover="#BBF7D0"
            )
            btn_pay.clicked.connect(lambda: self._show_payment_dialog(invoice_id))
            actions.append(btn_pay)

        return _wrap_action_buttons(actions)

    def _setup_invoice_payment_tabs(self, inv_page: QWidget) -> None:
        if getattr(inv_page, "_invoice_pay_tabs_ready", False):
            return
        vlay = inv_page.layout()
        if not isinstance(vlay, QVBoxLayout):
            return

        tab_bar = QWidget()
        tab_lay = QHBoxLayout(tab_bar)
        tab_lay.setContentsMargins(0, 0, 0, 0)
        tab_lay.setSpacing(8)

        btn_unpaid = QPushButton("Chưa thanh toán")
        btn_unpaid.setObjectName("tabInvoiceUnpaidButton")
        btn_unpaid.setCheckable(True)
        btn_unpaid.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_unpaid.setStyleSheet(_APPT_TAB_BTN_QSS)

        btn_paid = QPushButton("Đã thanh toán")
        btn_paid.setObjectName("tabInvoicePaidButton")
        btn_paid.setCheckable(True)
        btn_paid.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_paid.setStyleSheet(_APPT_TAB_BTN_QSS)

        tab_lay.addWidget(btn_unpaid)
        tab_lay.addWidget(btn_paid)
        tab_lay.addStretch(1)

        insert_at = 1
        if hasattr(inv_page, "invoiceFilterLayout"):
            for i in range(vlay.count()):
                item = vlay.itemAt(i)
                if item and item.layout() is inv_page.invoiceFilterLayout:  # type: ignore[attr-defined]
                    insert_at = i
                    break
        vlay.insertWidget(insert_at, tab_bar)

        inv_page.tabInvoiceUnpaidButton = btn_unpaid  # type: ignore[attr-defined]
        inv_page.tabInvoicePaidButton = btn_paid  # type: ignore[attr-defined]
        inv_page._invoice_pay_tabs_ready = True  # type: ignore[attr-defined]

        btn_unpaid.setChecked(True)
        btn_unpaid.clicked.connect(lambda: self._set_invoice_payment_mode("unpaid"))
        btn_paid.clicked.connect(lambda: self._set_invoice_payment_mode("paid"))

    def _set_invoice_payment_mode(self, mode: str) -> None:
        self._invoice_payment_mode = mode
        inv_page = self._pages.get("invoices")
        if inv_page:
            is_unpaid = mode == "unpaid"
            if hasattr(inv_page, "tabInvoiceUnpaidButton"):
                inv_page.tabInvoiceUnpaidButton.setChecked(is_unpaid)  # type: ignore[attr-defined]
            if hasattr(inv_page, "tabInvoicePaidButton"):
                inv_page.tabInvoicePaidButton.setChecked(not is_unpaid)  # type: ignore[attr-defined]
        self._reload_invoices_table()

    def _show_invoice_center(self) -> None:
        """Nut 'Tao hoa don' -> mo dialog chon appointment hoan thanh chua co invoice."""
        self._show_create_invoice_dialog()

    def _show_create_invoice_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Tạo hoá đơn từ lịch hẹn")
        dlg.resize(860, 520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        root = QVBoxLayout(dlg)
        root.setSpacing(10)

        info = QLabel("Chọn lịch hẹn đã Hoàn thành, chưa có hoá đơn.")
        info.setStyleSheet("color:#334155; font:700 9pt 'Segoe UI';")
        root.addWidget(info)

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["ID", "Thời gian", "Khách hàng", "Thú cưng", "Dịch vụ", "Trạng thái"])
        self._setup_table(table)
        root.addWidget(table, 1)

        empty_lbl = QLabel("")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl.setStyleSheet("color:#64748B;font:700 10pt 'Segoe UI';padding:24px;")
        empty_lbl.setVisible(False)
        root.addWidget(empty_lbl)

        from src.petcare_backend.dao import invoice_dao

        invoiced_ids = set(invoice_dao.list_appointment_ids_with_invoice())

        def _load_candidates() -> list[dict]:
            rows = appointment_service.list_recent(limit=200)
            out: list[dict] = []
            for a in rows:
                if a.get("status") != "HOAN_THANH":
                    continue
                appt_id = int(a["appointment_id"])
                if appt_id in invoiced_ids:
                    continue
                out.append(a)
            return out

        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Tạo hoá đơn")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _fill_table(candidates: list[dict]) -> None:
            table.setRowCount(len(candidates))
            for r, a in enumerate(candidates):
                appt_id = int(a["appointment_id"])
                table.setItem(r, 0, QTableWidgetItem(str(appt_id)))
                when_txt = (
                    a["scheduled_at"].strftime("%d/%m/%Y %H:%M")
                    if a.get("scheduled_at")
                    else ""
                )
                table.setItem(r, 1, QTableWidgetItem(when_txt))
                table.setItem(r, 2, QTableWidgetItem(str(a.get("customer_name", ""))))
                table.setItem(r, 3, QTableWidgetItem(str(a.get("pet_name", ""))))
                table.setItem(r, 4, QTableWidgetItem(str(a.get("service_name", ""))))
                table.setItem(r, 5, QTableWidgetItem(str(a.get("status_label", ""))))
                table.item(r, 0).setData(Qt.ItemDataRole.UserRole, appt_id)

            has_rows = len(candidates) > 0
            table.setVisible(has_rows)
            empty_lbl.setVisible(not has_rows)
            if not has_rows:
                empty_lbl.setText(
                    "Không còn lịch hẹn nào cần tạo hoá đơn.\n"
                    "(Các lịch đã Hoàn thành và đã có HĐ sẽ không hiển thị ở đây.)"
                )
            if ok_btn is not None:
                ok_btn.setEnabled(has_rows)

        candidates = _load_candidates()
        _fill_table(candidates)

        def _on_ok() -> None:
            row = table.currentRow()
            if row < 0:
                QMessageBox.warning(dlg, "Tạo hoá đơn", "Vui lòng chọn 1 lịch hẹn.")
                return
            id_item = table.item(row, 0)
            appt_id = id_item.data(Qt.ItemDataRole.UserRole) if id_item else None
            if not isinstance(appt_id, int):
                return
            try:
                inv_id = invoice_service.create_from_appointment(appt_id)
            except Exception as exc:
                QMessageBox.warning(dlg, "Tạo hoá đơn", str(exc))
                return
            invoiced_ids.add(appt_id)
            QMessageBox.information(dlg, "Tạo hoá đơn", f"Đã tạo hoá đơn #{inv_id}.")
            self._reload_invoices_table()
            _fill_table(_load_candidates())

        buttons.accepted.connect(_on_ok)
        root.addWidget(buttons)

        dlg.exec()

    def _show_retail_pos_dialog(self) -> None:
        """Dialog tao hoa don ban le (POS): chon SP + so luong, tinh tong, tao."""
        try:
            products = list(product_service.list_products(active_only=True))
        except Exception as exc:
            QMessageBox.warning(self, "Bán lẻ", f"Không tải được sản phẩm: {exc}")
            return
        if not products:
            QMessageBox.information(
                self, "Bán lẻ", "Chưa có sản phẩm nào. Hãy thêm sản phẩm trước."
            )
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Tạo hoá đơn bán lẻ (POS)")
        dlg.resize(820, 580)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        root = QVBoxLayout(dlg)
        root.setSpacing(12)

        title = QLabel("Bán đồ ăn / phụ kiện cho khách hàng")
        title.setStyleSheet("font: 800 12pt 'Segoe UI'; color:#0F172A;")
        root.addWidget(title)

        # KH (tuy chon - khach vang lai)
        cust_row = QHBoxLayout()
        cust_lbl = QLabel("Khách hàng (tuỳ chọn)")
        cust_lbl.setStyleSheet("color: rgba(15,23,42,0.65); font: 700 9pt 'Segoe UI';")
        cust_row.addWidget(cust_lbl)
        cust_combo = QComboBox()
        cust_combo.addItem("— Khách vãng lai —", 0)
        for c in self._customers:
            cust_combo.addItem(f"{c.full_name} ({c.phone})", int(c.id))
        cust_row.addWidget(cust_combo, 1)
        root.addLayout(cust_row)

        # Form them dong
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        prod_combo = QComboBox()
        prod_combo.setMinimumWidth(380)
        for p in products:
            prod_combo.addItem(
                f"{p.name} — {int(p.price):,}đ (kho: {p.stock})".replace(",", "."),
                int(p.id),
            )
        qty_spin = QSpinBox()
        qty_spin.setRange(1, 100)
        qty_spin.setValue(1)
        btn_add = QPushButton("＋ Thêm")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(
            "QPushButton{background:#DCFCE7;color:#166534;border:none;padding:6px 14px;border-radius:8px;font:800 9pt 'Segoe UI';}"
            "QPushButton:hover{background:#BBF7D0;}"
        )
        add_row.addWidget(prod_combo, 1)
        add_row.addWidget(qty_spin)
        add_row.addWidget(btn_add)
        root.addLayout(add_row)

        # Bang gio hang
        cart_table = QTableWidget()
        cart_table.setColumnCount(6)
        cart_table.setHorizontalHeaderLabels(
            ["Tên sản phẩm", "Loại", "SL", "Đơn giá", "Thành tiền", ""]
        )
        self._setup_table(cart_table)
        cart_table.setMinimumHeight(220)
        root.addWidget(cart_table, 1)

        # Tom tat tong
        total_lbl = QLabel("Tổng: 0đ")
        total_lbl.setStyleSheet("font: 900 12pt 'Segoe UI'; color:#0F172A;")
        total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(total_lbl)

        cart: list[dict] = []  # {pid, name, category, qty, price}

        def _recompute() -> None:
            cart_table.setRowCount(len(cart))
            total = 0
            for r, line in enumerate(cart):
                cart_table.setItem(r, 0, QTableWidgetItem(line["name"]))
                cat_label = product_service.CATEGORY_LABELS.get(line["category"], line["category"])
                cart_table.setItem(r, 1, QTableWidgetItem(cat_label))
                cart_table.setItem(r, 2, QTableWidgetItem(str(line["qty"])))
                cart_table.setItem(r, 3, QTableWidgetItem(f"{int(line['price']):,}đ".replace(",", ".")))
                line_total = int(line["price"]) * int(line["qty"])
                total += line_total
                cart_table.setItem(r, 4, QTableWidgetItem(f"{line_total:,}đ".replace(",", ".")))

                btn_del = _build_action_icon_button(
                    _action_icon("trash", "#B91C1C"),
                    "Xoá",
                    "#FEE2E2",
                    "#B91C1C",
                    hover="#FCA5A5",
                    hover_fg="#7F1D1D",
                )
                btn_del.clicked.connect(lambda _, idx=r: _remove_line(idx))
                cart_table.setCellWidget(r, 5, _wrap_action_buttons([btn_del]))
            total_lbl.setText(f"Tổng: {total:,}đ".replace(",", "."))

            hdr2 = cart_table.horizontalHeader()
            hdr2.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            hdr2.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            hdr2.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            hdr2.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            hdr2.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            hdr2.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        def _remove_line(idx: int) -> None:
            if 0 <= idx < len(cart):
                cart.pop(idx)
                _recompute()

        def _on_add() -> None:
            pid = prod_combo.currentData()
            if not isinstance(pid, int):
                return
            p = next((x for x in products if x.id == pid), None)
            if p is None:
                return
            qty = int(qty_spin.value())
            existing = next((c for c in cart if c["pid"] == pid), None)
            new_total = (existing["qty"] if existing else 0) + qty
            if new_total > p.stock:
                QMessageBox.warning(
                    dlg,
                    "Tồn kho",
                    f"Sản phẩm '{p.name}' chỉ còn {p.stock} trong kho.",
                )
                return
            if existing:
                existing["qty"] = new_total
            else:
                cart.append(
                    {
                        "pid": pid,
                        "name": p.name,
                        "category": p.category,
                        "qty": qty,
                        "price": int(p.price),
                    }
                )
            qty_spin.setValue(1)
            _recompute()

        btn_add.clicked.connect(_on_add)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Tạo hoá đơn")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            if not cart:
                QMessageBox.warning(dlg, "Bán lẻ", "Vui lòng chọn ít nhất một sản phẩm.")
                return
            cust_id = cust_combo.currentData()
            cust_id_val = int(cust_id) if isinstance(cust_id, int) and cust_id > 0 else None
            try:
                inv_id = invoice_service.create_retail_invoice(
                    customer_id=cust_id_val,
                    items=[(int(c["pid"]), int(c["qty"])) for c in cart],
                )
            except invoice_service.InvoiceError as exc:
                QMessageBox.warning(dlg, "Bán lẻ", str(exc))
                return
            QMessageBox.information(dlg, "Bán lẻ", f"Đã tạo hoá đơn bán lẻ #{inv_id}.")
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        root.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_invoices_table()
            self._reload_products()

    def _show_invoice_detail(self, invoice_id: int) -> None:
        from src.petcare_backend.dao import invoice_dao, invoice_item_dao
        from src.petcare_backend.invoice_export import export_invoice_pdf, ExportError

        inv = invoice_dao.get_by_id(invoice_id)
        if inv is None:
            QMessageBox.warning(self, "Hoá đơn", "Hoá đơn không tồn tại.")
            return

        is_retail = str(inv.get("invoice_type") or "SERVICE") == "RETAIL"
        is_paid = str(inv.get("payment_status") or "") == "DA_TT"

        dlg = QDialog(self)
        title_kind = "bán lẻ" if is_retail else "dịch vụ"
        dlg.setWindowTitle(f"Chi tiết hoá đơn {title_kind} #{invoice_id}")
        dlg.resize(820, 580)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        root = QVBoxLayout(dlg)
        root.setSpacing(10)

        # Top bar: them san pham + xuat PDF
        top_bar = QHBoxLayout()
        if not is_paid:
            btn_add_prod = QPushButton("＋  Thêm sản phẩm")
            btn_add_prod.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_add_prod.setStyleSheet(
                "QPushButton{background:#DCFCE7;color:#166534;border:none;padding:6px 12px;border-radius:8px;font:800 9pt 'Segoe UI';}"
                "QPushButton:hover{background:#BBF7D0;}"
            )
            top_bar.addWidget(btn_add_prod)
        else:
            btn_add_prod = None
        top_bar.addStretch(1)
        btn_export = QPushButton("Xuất PDF")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet(
            f"QPushButton{{background:{THEME.primary};color:white;border:none;padding:6px 14px;border-radius:8px;font:800 9pt 'Segoe UI';}}"
            f"QPushButton:hover{{background:{THEME.primary_hover};}}"
        )
        top_bar.addWidget(btn_export)
        root.addLayout(top_bar)

        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(
            ["Loại", "Thú cưng", "Tên dịch vụ / sản phẩm", "SL", "Đơn giá", "Thành tiền", ""]
        )
        self._setup_table(table)
        table.setIconSize(QSize(26, 26))
        table.verticalHeader().setDefaultSectionSize(50)
        root.addWidget(table, 1)

        # Tom tat
        summary = QLabel("")
        summary.setStyleSheet("font:700 10pt 'Segoe UI'; color:#0F172A;")
        root.addWidget(summary)

        def _refresh() -> None:
            items = invoice_item_dao.list_by_invoice(invoice_id)
            table.setRowCount(len(items))
            for r, it in enumerate(items):
                t = str(it.get("item_type") or "SERVICE")
                t_label = "Sản phẩm" if t == "PRODUCT" else "Dịch vụ"
                t_item = QTableWidgetItem(t_label)
                t_item.setForeground(QColor(THEME.accent if t == "PRODUCT" else THEME.success))
                table.setItem(r, 0, t_item)
                table.setItem(r, 1, QTableWidgetItem(str(it.get("pet_name") or "—")))
                name_txt = str(it.get("item_name") or it.get("service_name") or it.get("product_name") or "")
                name_item = QTableWidgetItem(name_txt)
                if t == "PRODUCT":
                    pid_raw = it.get("product_id")
                    pid = int(pid_raw) if pid_raw is not None else None
                    name_item.setIcon(
                        self._product_thumb_icon(
                            pid, str(it.get("product_category") or ""), 26
                        )
                    )
                table.setItem(r, 2, name_item)
                table.setItem(r, 3, QTableWidgetItem(str(it.get("quantity", ""))))
                table.setItem(r, 4, QTableWidgetItem(f"{int(float(it.get('unit_price') or 0)):,}đ".replace(",", ".")))
                table.setItem(r, 5, QTableWidgetItem(f"{int(float(it.get('line_total') or 0)):,}đ".replace(",", ".")))

                if not is_paid and t == "PRODUCT":
                    btn_del = _build_action_icon_button(
                        _action_icon("trash", "#B91C1C"),
                        "Xoá",
                        "#FEE2E2",
                        "#B91C1C",
                        hover="#FCA5A5",
                        hover_fg="#7F1D1D",
                    )
                    btn_del.clicked.connect(
                        lambda _, iid=int(it["id"]): self._remove_invoice_product(iid, dlg, _refresh)
                    )
                    table.setCellWidget(r, 6, _wrap_action_buttons([btn_del]))
                else:
                    table.setCellWidget(r, 6, QWidget())
            inv_now = invoice_dao.get_by_id(invoice_id)
            if inv_now:
                summary.setText(
                    f"Tạm tính: {int(float(inv_now.get('subtotal_amount') or 0)):,}đ"
                    f"  •  Giảm giá: {int(float(inv_now.get('discount_amount') or 0)):,}đ"
                    f"  •  Thuế: {int(float(inv_now.get('tax_amount') or 0)):,}đ"
                    f"  •  Tổng: {int(float(inv_now.get('total_amount') or 0)):,}đ"
                    .replace(",", ".")
                )

        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        _refresh()

        def _on_export() -> None:
            default_name = f"invoice_{invoice_id}.pdf"
            path, _ = QFileDialog.getSaveFileName(dlg, "Lưu hóa đơn PDF", default_name, "PDF (*.pdf)")
            if not path:
                return
            try:
                export_invoice_pdf(invoice_id, path)
            except ExportError as exc:
                QMessageBox.warning(dlg, "Xuất PDF", str(exc))
                return
            except Exception as exc:
                QMessageBox.critical(dlg, "Xuất PDF", str(exc))
                return
            QMessageBox.information(dlg, "Xuất PDF", f"Đã xuất PDF:\n{path}")

        btn_export.clicked.connect(_on_export)
        if btn_add_prod is not None:
            btn_add_prod.clicked.connect(
                lambda: self._add_product_to_invoice_dialog(invoice_id, dlg, _refresh)
            )

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        root.addWidget(buttons)
        dlg.exec()
        # Reload bang chinh sau khi dong dialog (du lieu co the doi)
        self._reload_invoices_table()
        self._reload_products()

    def _remove_invoice_product(self, item_id: int, parent: QWidget, on_done) -> None:
        confirm = QMessageBox.question(parent, "Xoá sản phẩm", "Xoá sản phẩm khỏi hoá đơn? (số tồn kho sẽ được hoàn lại)")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            invoice_service.remove_invoice_item(item_id)
        except invoice_service.InvoiceError as exc:
            QMessageBox.warning(parent, "Xoá sản phẩm", str(exc))
            return
        on_done()

    def _add_product_to_invoice_dialog(self, invoice_id: int, parent: QWidget, on_done) -> None:
        try:
            products = list(product_service.list_products(active_only=True))
        except Exception as exc:
            QMessageBox.warning(parent, "Sản phẩm", f"Không tải được sản phẩm: {exc}")
            return
        if not products:
            QMessageBox.information(parent, "Sản phẩm", "Chưa có sản phẩm nào.")
            return

        prod_by_id = {int(p.id): p for p in products}

        dlg = QDialog(parent)
        dlg.setWindowTitle("Thêm sản phẩm vào hoá đơn")
        dlg.setMinimumWidth(560)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        pick_row = QHBoxLayout()
        pick_row.setSpacing(14)
        preview = QLabel()
        preview.setFixedSize(76, 76)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setStyleSheet(
            "background:#FFFFFF;border:1px solid #D6E2F7;border-radius:12px;"
        )
        pick_row.addWidget(preview, 0, Qt.AlignmentFlag.AlignTop)

        form_wrap = QWidget()
        form = QFormLayout(form_wrap)
        form.setContentsMargins(0, 0, 0, 0)
        prod_combo = QComboBox()
        prod_combo.setIconSize(QSize(28, 28))
        prod_combo.setStyleSheet(
            "QComboBox{min-height:36px;padding:4px 8px 4px 6px;font:600 10pt 'Segoe UI';}"
        )
        for p in products:
            cat_lbl = product_service.CATEGORY_LABELS.get(p.category, p.category)
            prod_combo.addItem(
                f"{self._product_placeholder_emoji(p.category)} {p.name} — "
                f"{int(p.price):,}đ (kho: {p.stock})".replace(",", "."),
                int(p.id),
            )
            ix = prod_combo.count() - 1
            prod_combo.setItemIcon(
                ix, self._product_thumb_icon(p.id, p.category, 28)
            )
            prod_combo.setItemData(ix, cat_lbl, Qt.ItemDataRole.UserRole + 1)
        qty = QSpinBox()
        qty.setRange(1, 100)
        qty.setValue(1)
        cat_hint = QLabel("")
        cat_hint.setStyleSheet(
            f"color:{THEME.muted};font:600 9pt 'Segoe UI';"
        )
        form.addRow("Sản phẩm *", prod_combo)
        form.addRow("", cat_hint)
        form.addRow("Số lượng *", qty)
        pick_row.addWidget(form_wrap, 1)
        layout.addLayout(pick_row)

        img_note = QLabel(
            "Ảnh lấy từ trang Sản phẩm (nút ảnh trên thẻ). Chưa có ảnh thì hiện 🍖 đồ ăn / 🎀 phụ kiện."
        )
        img_note.setWordWrap(True)
        img_note.setStyleSheet("color:#64748B;font:600 8pt 'Segoe UI';")
        layout.addWidget(img_note)

        def _sync_product_preview() -> None:
            pid = prod_combo.currentData()
            p = prod_by_id.get(int(pid)) if isinstance(pid, int) else None
            if p is None:
                preview.clear()
                cat_hint.setText("")
                return
            preview.setPixmap(self._product_thumb_pixmap(p.id, p.category, 72))
            cat_hint.setText(
                product_service.CATEGORY_LABELS.get(p.category, p.category)
            )

        prod_combo.currentIndexChanged.connect(lambda _i: _sync_product_preview())
        _sync_product_preview()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Thêm")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            pid = prod_combo.currentData()
            if not isinstance(pid, int):
                return
            try:
                invoice_service.add_product_to_invoice(invoice_id, pid, int(qty.value()))
            except invoice_service.InvoiceError as exc:
                QMessageBox.warning(dlg, "Thêm sản phẩm", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            on_done()

    def _show_payment_dialog(self, invoice_id: int) -> None:
        from decimal import Decimal

        from src.petcare_backend.dao import invoice_dao, payment_dao

        inv = invoice_dao.get_by_id(invoice_id)
        if inv is None:
            QMessageBox.warning(self, "Thanh toán", "Hóa đơn không tồn tại.")
            return
        total_amt = Decimal(str(inv.get("total_amount") or 0))
        paid_amt = Decimal(str(payment_dao.sum_paid(invoice_id)))
        default_pay = total_amt - paid_amt
        if default_pay < 0:
            default_pay = Decimal(0)
        default_int = int(default_pay)
        default_txt = f"{default_int:,}".replace(",", ".")

        if default_int <= 0:
            QMessageBox.information(
                self,
                "Thanh toán",
                "Hóa đơn này không còn số tiền cần thanh toán.",
            )
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Thanh toán hoá đơn #{invoice_id}")
        dlg.setMinimumWidth(520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        root = QVBoxLayout(dlg)
        form = QFormLayout()
        amount = QLineEdit()
        amount.setText(default_txt)
        method = QComboBox()
        method.addItem("Tiền mặt")
        method.addItem("Chuyển khoản")
        method.addItem("Thẻ")
        note = QLineEdit()
        form.addRow("Số tiền *", amount)
        form.addRow("Phương thức", method)
        form.addRow("Ghi chú", note)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Thanh toán")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                payment_service.add_payment(invoice_id, amount.text(), method.currentText(), note.text())
            except Exception as exc:
                QMessageBox.warning(dlg, "Thanh toán", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        root.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            inv_after = invoice_dao.get_by_id(invoice_id)
            if inv_after and str(inv_after.get("payment_status") or "") == "DA_TT":
                self._set_invoice_payment_mode("paid")
                QMessageBox.information(
                    self,
                    "Thanh toán",
                    "Đã thanh toán xong. Hóa đơn chuyển sang tab 「Đã thanh toán」.",
                )
            else:
                self._reload_invoices_table()

    def _insert_add_customer_button(self, customers_page: QWidget) -> None:
        """CustomersPage khong co nut 'Them' trong .ui, nen chen runtime."""
        if hasattr(customers_page, "addCustomerButton"):
            return

        try:
            header_layout = customers_page.headerLayout  # type: ignore[attr-defined]
        except Exception:
            return

        btn = QPushButton("＋  Thêm khách hàng")
        btn.setObjectName("PrimaryButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._on_add_customer_clicked)
        header_layout.insertWidget(max(0, header_layout.count() - 1), btn)
        customers_page.addCustomerButton = btn  # type: ignore[attr-defined]

    def _setup_table(self, table: QTableWidget) -> None:
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        vh = table.verticalHeader()
        vh.setVisible(False)
        vh.setDefaultSectionSize(58)
        vh.setMinimumSectionSize(58)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setMinimumSectionSize(80)

    def _filter_table(self, table: QTableWidget, query: str, cols: tuple[int, ...]) -> None:
        q = (query or "").strip().lower()
        for r in range(table.rowCount()):
            if not q:
                table.setRowHidden(r, False)
                continue
            text = " ".join((table.item(r, c).text() if table.item(r, c) else "") for c in cols).lower()
            table.setRowHidden(r, q not in text)

    def _setup_appointment_list_tabs(self, ap_page: QWidget) -> None:
        """Tab Đang xử lý / Lịch sử + ô tìm kiếm."""
        if hasattr(ap_page, "tabActiveButton"):
            ap_page.tabActiveButton.setStyleSheet(_APPT_TAB_BTN_QSS)
            ap_page.tabHistoryButton.setStyleSheet(_APPT_TAB_BTN_QSS)
            ap_page.tabActiveButton.clicked.connect(
                lambda: self._set_appointment_list_mode("active")
            )
            ap_page.tabHistoryButton.clicked.connect(
                lambda: self._set_appointment_list_mode("history")
            )
        if hasattr(ap_page, "appointmentSearchEdit"):
            ap_page.appointmentSearchEdit.setVisible(False)
            ap_page.appointmentSearchEdit.textChanged.connect(
                lambda _: self._apply_appointment_search_filter()
            )

    def _set_appointment_list_mode(self, mode: str) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        self._appointment_list_mode = mode
        is_active = mode == "active"
        if hasattr(ap_page, "tabActiveButton"):
            ap_page.tabActiveButton.setChecked(is_active)
            ap_page.tabHistoryButton.setChecked(not is_active)
        if hasattr(ap_page, "recentTitle"):
            ap_page.recentTitle.setText(
                "Danh sách lịch hẹn" if is_active else "Lịch sử lịch hẹn"
            )
        if hasattr(ap_page, "appointmentSearchEdit"):
            ap_page.appointmentSearchEdit.setVisible(not is_active)
            if is_active:
                ap_page.appointmentSearchEdit.clear()
        self._reload_appointments_table()

    @staticmethod
    def _format_vnd(amount) -> str:
        try:
            return f"{int(float(amount or 0)):,}đ".replace(",", ".")
        except (TypeError, ValueError):
            return "0đ"

    def _apply_appointment_search_filter(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        table: QTableWidget = ap_page.appointmentsTable
        query = ""
        if hasattr(ap_page, "appointmentSearchEdit"):
            query = ap_page.appointmentSearchEdit.text()
        self._filter_table(table, query, cols=(0, 1, 2, 3, 4, 5, 6))

    def _update_appointment_status_badges(self, rows: list) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page or not hasattr(ap_page, "statusBadgesLayout"):
            return
        layout: QHBoxLayout = ap_page.statusBadgesLayout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        mode = getattr(self, "_appointment_list_mode", "active")
        if mode == "active":
            specs = [
                ("Chờ xử lý", THEME.warning, THEME.warning_soft),
                ("Đang thực hiện", THEME.accent, THEME.accent_soft),
            ]
        else:
            specs = [
                ("Hoàn thành", THEME.success, THEME.success_soft),
                ("Hủy", THEME.danger, THEME.danger_soft),
            ]

        counts = {label: 0 for label, _, _ in specs}
        for row in rows:
            label = str(row.get("status_label") or "")
            if label in counts:
                counts[label] += 1

        for label, fg, bg in specs:
            icon = _APPT_STATUS_ICONS.get(label, "")
            badge = QLabel(f"  {icon} {label}: {counts[label]}  ")
            badge.setStyleSheet(
                f"background:{bg}; color:{fg}; font:800 9pt 'Segoe UI';"
                f"border:1px solid {fg}; border-radius:10px; padding:4px 8px;"
            )
            layout.addWidget(badge)
        layout.addStretch(1)

    @staticmethod
    def _colorize_status_item(item: QTableWidgetItem, status_label: str) -> None:
        color = _APPT_STATUS_COLORS.get(status_label)
        if color:
            item.setForeground(QColor(color))
            item.setData(Qt.ItemDataRole.UserRole + 1, status_label)

    def _setup_appointments_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        vh = table.verticalHeader()
        vh.setVisible(False)
        vh.setDefaultSectionSize(58)
        vh.setMinimumSectionSize(58)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed
        )

    def _refresh_appointment_pet_list(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        ap_page.petListWidget.blockSignals(True)
        ap_page.petListWidget.clear()
        cid = ap_page.customerCombo.currentData()
        if isinstance(cid, int) and cid:
            pets = pet_service.list_pets(customer_id=cid)
            for p in pets:
                item = QListWidgetItem(p.name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, p.id)
                ap_page.petListWidget.addItem(item)
        ap_page.petListWidget.blockSignals(False)
        self._update_per_pet_service_ui()

    def _build_per_pet_service_container(self, ap_page: QWidget) -> None:
        create_layout = ap_page.createCard.layout()
        if create_layout is None:
            return

        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        title = QLabel("Dịch vụ cho từng thú cưng")
        title.setStyleSheet(
            "color: rgba(15,23,42,0.65); font: 700 9pt \"Segoe UI\";"
        )
        outer.addWidget(title)

        rows = QWidget()
        rows_layout = QVBoxLayout(rows)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(6)
        outer.addWidget(rows)

        idx = create_layout.indexOf(ap_page.labelService)
        if idx < 0:
            idx = create_layout.count()
        create_layout.insertWidget(idx, container)
        container.setVisible(False)

        self._per_pet_service_container = container
        self._per_pet_service_rows_layout = rows_layout

    def _on_appointment_pet_check_changed(self, _item: QListWidgetItem) -> None:
        self._update_per_pet_service_ui()

    def _update_per_pet_service_ui(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        layout = self._per_pet_service_rows_layout
        container = self._per_pet_service_container
        if layout is None or container is None:
            return

        checked_pets: list[str] = []
        for i in range(ap_page.petListWidget.count()):
            it = ap_page.petListWidget.item(i)
            if it and it.checkState() == Qt.CheckState.Checked:
                checked_pets.append(it.text())

        previous_selection = {
            name: combo.currentData()
            for name, combo in self._per_pet_service_combos.items()
        }

        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._per_pet_service_combos.clear()

        multi = len(checked_pets) >= 2
        container.setVisible(multi)
        ap_page.labelService.setVisible(not multi)
        ap_page.serviceCombo.setVisible(not multi)

        if not multi:
            return

        for name in checked_pets:
            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(10)

            lbl = QLabel(f"🐾 {name}")
            lbl.setStyleSheet(
                "font: 700 9pt \"Segoe UI\"; color: #0F172A;"
            )
            lbl.setMinimumWidth(110)

            combo = QComboBox()
            combo.addItem("Chọn dịch vụ", 0)
            for s in self._services_list:
                combo.addItem(
                    f"{s.name} ({int(s.price):,}đ)".replace(",", "."), s.id
                )
            prev = previous_selection.get(name)
            if isinstance(prev, int) and prev > 0:
                idx = combo.findData(prev)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

            hl.addWidget(lbl)
            hl.addWidget(combo, 1)
            layout.addWidget(row)
            self._per_pet_service_combos[name] = combo

    def _render_appointments_table(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        # backward compat: call DB renderer
        self._render_appointments_table_db()

    def _format_appointment_detail_text(self, row: int) -> str:
        a = self._demo_appointments[row]
        cid = str(a.get("customer_id", ""))
        cust = next((c for c in self._customers if c.id == cid), None)
        phone = cust.phone if cust else "—"
        address = cust.address if cust else "—"
        cust_id_display = cid or "—"
        pets_list = a.get("pets")
        if isinstance(pets_list, list) and pets_list:
            pets_txt = ", ".join(str(x) for x in pets_list)
        else:
            pets_txt = str(a.get("pet", ""))
        result = str(a.get("result", "")).strip() or "(chưa có)"
        lines = [
            f"Thời gian: {a['when']}",
            f"Khách hàng: {a['customer']}",
            f"Mã khách hàng: {cust_id_display}",
            f"Số điện thoại: {phone}",
            f"Địa chỉ: {address}",
            f"Thú cưng: {pets_txt}",
            f"Dịch vụ: {a['service']}",
            f"Trạng thái: {a['status']}",
            "",
            "Kết quả dịch vụ:",
            result,
        ]
        return "\n".join(lines)

    def _sync_appointment_detail_panel(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        edit = ap_page.appointmentDetailEdit
        row = ap_page.appointmentsTable.currentRow()
        if row < 0 or row >= len(self._demo_appointments):
            edit.clear()
            return
        edit.setPlainText(self._format_appointment_detail_text(row))

    def _sync_appointment_detail_if_current_row(self, row: int) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        if ap_page.appointmentsTable.currentRow() == row:
            self._sync_appointment_detail_panel()

    def _on_appointment_selection_changed(self) -> None:
        self._sync_appointment_detail_panel()

    def _appointment_status_column_width_px(self, table: QTableWidget) -> int:
        fm = QFontMetrics(table.font())
        pad = 52
        longest = max(fm.horizontalAdvance(s) for s in APPOINTMENT_STATUSES)
        return max(longest + pad, 210)

    def _on_appt_status_changed(self, row: int, text: str) -> None:
        if 0 <= row < len(self._demo_appointments):
            self._demo_appointments[row]["status"] = text
        self._sync_appointment_detail_if_current_row(row)

    def _on_appointment_result_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 5:
            return
        row = item.row()
        if 0 <= row < len(self._demo_appointments):
            self._demo_appointments[row]["result"] = item.text()
        self._sync_appointment_detail_if_current_row(row)

    def _reload_appointments_table(self) -> None:
        if not self._has_active_session():
            return
        ap_page = self._pages.get("appointments")
        employee_id: int | None = None
        only_unassigned = False
        if ap_page and hasattr(ap_page, "employeeFilterCombo"):
            data = ap_page.employeeFilterCombo.currentData()
            if isinstance(data, int):
                employee_id = data
            elif data == "NONE":
                only_unassigned = True

        if not getattr(self, "_is_admin", False):
            current = Session.current()
            if current is not None:
                employee_id = int(current.id)
            only_unassigned = False

        scope = "active" if getattr(self, "_appointment_list_mode", "active") == "active" else "history"
        self._appointments_rows = appointment_service.list_filtered(  # type: ignore[attr-defined]
            limit=150,
            employee_id=employee_id,
            only_unassigned=only_unassigned,
            status_scope=scope,
        )
        self._render_appointments_table_db()
        self._apply_appointment_search_filter()

    def _render_appointments_table_db(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        table: QTableWidget = ap_page.appointmentsTable
        rows = getattr(self, "_appointments_rows", [])
        table.blockSignals(True)
        table.setRowCount(len(rows))
        for r, a in enumerate(rows):
            appt_id = int(a["appointment_id"])
            when_txt = a["scheduled_at"].strftime("%d/%m/%Y %H:%M") if a.get("scheduled_at") else ""
            table.setItem(r, 0, QTableWidgetItem(when_txt))
            table.setItem(r, 1, QTableWidgetItem(str(a.get("customer_name", ""))))
            table.setItem(r, 2, QTableWidgetItem(str(a.get("pet_name", ""))))
            table.setItem(r, 3, QTableWidgetItem(str(a.get("service_name", ""))))

            emp_name = a.get("employee_name")
            emp_text = str(emp_name) if emp_name else "— Chưa phân công"
            emp_item = QTableWidgetItem(emp_text)
            if not emp_name:
                emp_item.setForeground(QColor("#94A3B8"))
            table.setItem(r, 4, emp_item)

            status_label = str(a.get("status_label") or "")
            status_item = QTableWidgetItem(_status_display(status_label))
            status_item.setData(Qt.ItemDataRole.UserRole, appt_id)
            self._colorize_status_item(status_item, status_label)
            table.setItem(r, 5, status_item)

            res_item = QTableWidgetItem(str(a.get("note") or ""))
            res_item.setData(Qt.ItemDataRole.UserRole, appt_id)
            table.setItem(r, 6, res_item)

        table.blockSignals(False)

        hdr = table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        # ensure table is read-only
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._update_appointment_status_badges(rows)

    def _on_appointment_selection_changed_db(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        row = ap_page.appointmentsTable.currentRow()
        rows = getattr(self, "_appointments_rows", [])
        if row < 0 or row >= len(rows):
            ap_page.appointmentDetailEdit.clear()
            return
        a = rows[row]
        st = str(a.get("status_label") or "")
        st_icon = _APPT_STATUS_ICONS.get(st, "⚪")
        lines = [
            f"📅 {a['scheduled_at'].strftime('%d/%m/%Y %H:%M') if a.get('scheduled_at') else ''}",
            f"👤 {a.get('customer_name','')}",
            f"📞 {a.get('customer_phone','—')}",
            f"📍 {a.get('customer_address','—')}",
            f"🐾 {a.get('pet_name','')}",
            f"Dịch vụ: {a.get('service_name','')}",
            f"{st_icon} Trạng thái: {st}",
            "",
            "Kết quả dịch vụ:",
            str(a.get("note") or "(chưa có)"),
        ]
        ap_page.appointmentDetailEdit.setPlainText("\n".join(lines))

    def _on_appointment_row_clicked(self, row: int, col: int) -> None:
        try:
            self._show_appointment_detail_dialog(row)
        except Exception as exc:
            QMessageBox.warning(self, "Chi tiết lịch hẹn", f"Không mở được chi tiết:\n{exc}")

    def _create_appointment_retail_section(
        self, appt_id: int, dlg: QDialog
    ) -> tuple[QFrame, object]:
        """Khối đồ ăn / phụ kiện trên HĐ dịch vụ (chỉ lịch Hoàn thành). Trả về (card, refresh)."""
        from src.petcare_backend.dao import invoice_dao, invoice_item_dao

        _CAT_LABELS = {"DO_AN": "Đồ ăn", "PHU_KIEN": "Phụ kiện"}

        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:rgba(255,255,255,0.94);border:1px solid #D6E2F7;border-radius:12px;}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title = QLabel("🛒 Đồ ăn & phụ kiện")
        title.setStyleSheet("font:800 11pt 'Segoe UI'; color:#0F172A;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        inv_meta = QLabel("")
        inv_meta.setStyleSheet("font:700 9pt 'Segoe UI'; color:#64748B;")
        title_row.addWidget(inv_meta)
        layout.addLayout(title_row)

        hint = QLabel("")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#64748B;font:600 9pt 'Segoe UI';")
        layout.addWidget(hint)

        prod_table = QTableWidget()
        prod_table.setColumnCount(5)
        prod_table.setHorizontalHeaderLabels(
            ["Loại", "Sản phẩm", "SL", "Đơn giá", "T.Tiền"]
        )
        self._setup_table(prod_table)
        prod_table.setVisible(False)
        layout.addWidget(prod_table)

        total_lbl = QLabel("")
        total_lbl.setStyleSheet(
            f"font:800 10pt 'Segoe UI'; color:{THEME.accent_strong};"
        )
        layout.addWidget(total_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        layout.addLayout(btn_row)

        _btn_primary = (
            f"QPushButton{{background:{THEME.primary};color:#FFF;border:none;"
            f"padding:8px 14px;border-radius:8px;font:800 9pt 'Segoe UI';}}"
            f"QPushButton:hover{{background:{THEME.primary_hover};}}"
        )
        _btn_secondary = (
            f"QPushButton{{background:#FFFFFF;color:{THEME.accent};"
            f"border:1px solid {THEME.accent};padding:8px 14px;border-radius:8px;"
            f"font:800 9pt 'Segoe UI';}}"
            f"QPushButton:hover{{background:{THEME.accent_soft};}}"
        )
        _btn_ghost = (
            "QPushButton{background:#F8FAFC;color:#334155;border:1px solid #CBD5E1;"
            "padding:8px 14px;border-radius:8px;font:700 9pt 'Segoe UI';}"
            "QPushButton:hover{background:#E2E8F0;}"
        )

        def _clear_buttons() -> None:
            while btn_row.count():
                item = btn_row.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        def refresh() -> None:
            _clear_buttons()
            prod_table.setRowCount(0)
            prod_table.setVisible(False)
            prod_table.setFixedHeight(0)
            prod_table.setMaximumHeight(0)
            hint.setVisible(True)
            total_lbl.setText("")
            total_lbl.setVisible(False)
            inv_meta.setText("")

            inv = invoice_dao.get_by_appointment(appt_id)
            if inv is None:
                hint.setText(
                    "Chưa có hóa đơn. Tạo hóa đơn dịch vụ để thêm đồ ăn / phụ kiện kèm theo lịch hẹn."
                )
                btn_create = QPushButton("Tạo hóa đơn")
                btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_create.setStyleSheet(_btn_primary)

                def _on_create() -> None:
                    try:
                        inv_id = invoice_service.create_from_appointment(appt_id)
                    except invoice_service.InvoiceError as exc:
                        QMessageBox.warning(dlg, "Tạo hóa đơn", str(exc))
                        return
                    except Exception as exc:
                        QMessageBox.warning(dlg, "Tạo hóa đơn", str(exc))
                        return
                    QMessageBox.information(
                        dlg, "Tạo hóa đơn", f"Đã tạo hóa đơn #{inv_id}."
                    )
                    self._reload_invoices_table()
                    refresh()

                btn_create.clicked.connect(_on_create)
                btn_row.addWidget(btn_create)
                btn_row.addStretch(1)
                return

            inv_id = int(inv["id"])
            inv_no = str(inv.get("invoice_no") or inv_id)
            pay = str(inv.get("payment_status") or "")
            pay_txt = "Đã TT" if pay == "DA_TT" else "Chưa TT"
            pay_color = THEME.success if pay == "DA_TT" else THEME.warning
            inv_meta.setText(f"HĐ {inv_no}  •  {pay_txt}")
            inv_meta.setStyleSheet(f"font:700 9pt 'Segoe UI'; color:{pay_color};")

            items = [
                it
                for it in invoice_item_dao.list_by_invoice(inv_id)
                if str(it.get("item_type") or "") == "PRODUCT"
            ]

            if not items:
                if pay == "DA_TT":
                    hint.setText(
                        "Hóa đơn đã thanh toán — không thể thêm đồ ăn / phụ kiện sau khi đã TT. "
                        "Lần sau: bấm 「＋ Thêm sản phẩm」 trước khi thanh toán."
                    )
                    hint.setStyleSheet(
                        f"color:{THEME.warning};font:600 9pt 'Segoe UI';"
                        "background:#FEF3C7;border:1px solid #FCD34D;border-radius:8px;padding:8px 10px;"
                    )
                else:
                    hint.setText(
                        "Chưa có sản phẩm. Bấm nút 「＋ Thêm sản phẩm」 bên dưới "
                        "(hoặc 「Mở hóa đơn」 → Thêm sản phẩm)."
                    )
                    hint.setStyleSheet("color:#64748B;font:600 9pt 'Segoe UI';")
            else:
                hint.setVisible(False)
                prod_table.setVisible(True)
                prod_table.setMaximumHeight(16777215)
                prod_vh = prod_table.verticalHeader()
                prod_vh.setDefaultSectionSize(52)
                prod_table.setIconSize(QSize(26, 26))
                prod_table.setRowCount(len(items))
                prod_subtotal = 0.0
                for r, it in enumerate(items):
                    cat = _CAT_LABELS.get(
                        str(it.get("product_category") or ""), "Sản phẩm"
                    )
                    qty = int(it.get("quantity") or 1)
                    unit = float(it.get("unit_price") or 0)
                    line = float(it.get("line_total") or qty * unit)
                    prod_subtotal += line
                    cat_item = QTableWidgetItem(cat)
                    cat_item.setForeground(
                        QColor(
                            THEME.stat_orange
                            if str(it.get("product_category")) == "DO_AN"
                            else THEME.accent
                        )
                    )
                    prod_table.setItem(r, 0, cat_item)
                    pid_raw = it.get("product_id")
                    pid = int(pid_raw) if pid_raw is not None else None
                    cat_key = str(it.get("product_category") or "")
                    name_item = QTableWidgetItem(str(it.get("item_name") or ""))
                    name_item.setIcon(
                        self._product_thumb_icon(pid, cat_key, 26)
                    )
                    prod_table.setItem(r, 1, name_item)
                    prod_table.setItem(r, 2, QTableWidgetItem(str(qty)))
                    prod_table.setItem(r, 3, QTableWidgetItem(self._format_vnd(unit)))
                    prod_table.setItem(r, 4, QTableWidgetItem(self._format_vnd(line)))

                ph = prod_table.horizontalHeader()
                ph.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                ph.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                ph.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
                ph.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
                ph.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
                row_h = max(len(items), 1)
                prod_table.setFixedHeight(40 + row_h * 44)

                total_lbl.setVisible(True)
                total_lbl.setText(
                    f"Tổng sản phẩm: {self._format_vnd(prod_subtotal)}  •  "
                    f"Tổng HĐ: {self._format_vnd(inv.get('total_amount'))}  ({pay_txt})"
                )

            if pay != "DA_TT":
                btn_add = QPushButton("＋ Thêm sản phẩm")
                btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_add.setStyleSheet(_btn_secondary)
                btn_add.clicked.connect(
                    lambda: self._add_product_to_invoice_dialog(
                        inv_id, dlg, refresh
                    )
                )
                btn_row.addWidget(btn_add)

                btn_pay = QPushButton("Thanh toán")
                btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_pay.setStyleSheet(_btn_primary)

                def _on_pay() -> None:
                    self._show_payment_dialog(inv_id)
                    refresh()

                btn_pay.clicked.connect(_on_pay)
                btn_row.addWidget(btn_pay)

            btn_open = QPushButton("Mở hóa đơn")
            btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_open.setStyleSheet(_btn_ghost)

            def _on_open() -> None:
                self._show_invoice_detail(inv_id)
                refresh()

            btn_open.clicked.connect(_on_open)
            btn_row.addWidget(btn_open)

            btn_row.addStretch(1)

        refresh()
        return card, refresh

    def _show_appointment_detail_dialog(self, row: int) -> None:
        from src.petcare_backend.dao import appointment_service_dao

        rows = getattr(self, "_appointments_rows", [])
        if row < 0 or row >= len(rows):
            return
        a = rows[row]
        appt_id = int(a.get("appointment_id") or 0)
        current_status = str(a.get("status_label") or "Chờ xử lý")
        is_history = current_status in APPOINTMENT_HISTORY_STATUSES
        is_admin = bool(getattr(self, "_is_admin", False))
        current_emp = a.get("employee_id")

        dlg = QDialog(self)
        dlg.setWindowTitle(
            f"{'Xem chi tiết' if is_history else 'Chi tiết lịch hẹn'} #{a.get('appointment_id', '')}"
        )
        dlg.setFixedWidth(780)
        dlg.setMaximumHeight(860)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 175))

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        root = QVBoxLayout(body)
        root.setSpacing(14)
        root.setContentsMargins(2, 2, 2, 2)

        # Header panel (style tham khảo POS bida)
        header_frame = QFrame()
        header_frame.setStyleSheet(
            f"QFrame{{background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {THEME.accent_strong}, stop:1 {THEME.accent});"
            f"border-radius:14px; border:1px solid {THEME.accent_strong};}}"
        )
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_layout.setSpacing(6)

        title_row = QHBoxLayout()
        title = QLabel(f"{'📋 Chi tiết lịch sử' if is_history else '⚙ Lịch hẹn'} #{a.get('appointment_id','')}")
        title.setStyleSheet("font:900 12pt 'Segoe UI'; color:#FFFFFF;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        status_badge = QLabel(
            f" {_APPT_STATUS_ICONS.get(current_status, '⚪')} {current_status} "
        )
        status_badge.setStyleSheet(
            "background:rgba(255,255,255,0.18); color:#FFFFFF; font:800 8pt 'Segoe UI';"
            "border:1px solid rgba(255,255,255,0.45); border-radius:8px; padding:1px 6px;"
        )
        title_row.addWidget(status_badge)
        header_layout.addLayout(title_row)

        cust_name = str(a.get("customer_name") or "").strip() or "—"
        meta = QLabel(f"👤 {cust_name}")
        meta.setStyleSheet("color:rgba(255,255,255,0.92); font:700 10pt 'Segoe UI';")
        header_layout.addWidget(meta)
        root.addWidget(header_frame)

        info_card = QFrame()
        info_card.setStyleSheet(
            "QFrame{background:rgba(255,255,255,0.55);border:1px solid #D6E2F7;border-radius:10px;}"
        )
        info_grid = QGridLayout(info_card)
        info_grid.setContentsMargins(10, 8, 10, 8)
        info_grid.setHorizontalSpacing(8)
        info_grid.setVerticalSpacing(6)
        scheduled_txt = self._fmt_dt_safe(a.get("scheduled_at")) or "—"
        phone_txt = str(a.get("customer_phone") or "").strip() or "—"
        emp_txt = str(a.get("employee_name") or "").strip() or "Chưa phân công"
        address = str(a.get("customer_address") or "").strip()
        info_grid.addWidget(_appointment_info_chip("📅", f"Ngày hẹn: {scheduled_txt}"), 0, 0)
        info_grid.addWidget(_appointment_info_chip("📞", f"SĐT: {phone_txt}"), 0, 1)
        info_grid.addWidget(_appointment_info_chip("👤", f"NV: {emp_txt}"), 1, 0)
        if address:
            info_grid.addWidget(_appointment_info_chip("📍", address), 1, 1)
        else:
            info_grid.addWidget(_appointment_info_chip("📍", "Chưa có địa chỉ"), 1, 1)
        info_grid.setColumnStretch(0, 1)
        info_grid.setColumnStretch(1, 1)
        root.addWidget(info_card)

        # Thao tác nhanh (chỉ lịch đang xử lý)
        status_combo = QComboBox()
        status_combo.setObjectName("AppointmentStatusCombo")
        status_combo.setStyleSheet(_APPT_STATUS_COMBO_QSS)
        _populate_appointment_status_combo(status_combo)
        idx = status_combo.findData(current_status)
        if idx >= 0:
            status_combo.setCurrentIndex(idx)

        emp_combo = QComboBox()
        emp_combo.addItem("— Chưa phân công —", 0)
        for u in self._employees_list:
            emp_combo.addItem(f"{u.full_name} ({u.username})", int(u.id))
        if current_emp:
            cur_idx = emp_combo.findData(int(current_emp))
            if cur_idx < 0:
                emp_name = a.get("employee_name") or f"User #{current_emp}"
                emp_combo.addItem(str(emp_name), int(current_emp))
                cur_idx = emp_combo.findData(int(current_emp))
            emp_combo.setCurrentIndex(cur_idx)
        emp_combo.setEnabled(is_admin and not is_history)

        can_edit = not is_history
        if not is_admin and not is_history:
            current_user = Session.current()
            if current_user is not None and current_emp and int(current_emp) != int(current_user.id):
                can_edit = False

        if not is_history:
            actions_card = QFrame()
            actions_card.setStyleSheet(
                f"QFrame{{background:{THEME.accent_soft}; border:1px solid #D6E2F7; border-radius:10px;}}"
            )
            actions_layout = QVBoxLayout(actions_card)
            actions_layout.setContentsMargins(12, 10, 12, 10)
            actions_layout.setSpacing(8)

            quick_grid = QGridLayout()
            quick_grid.setSpacing(6)
            status_toggle_btns: dict[str, QPushButton] = {}

            def _sync_status_toggle_styles(selected: str) -> None:
                for status_label, btn in status_toggle_btns.items():
                    spec = _APPT_STATUS_TOGGLE_SPECS[status_label]
                    _, fg, bg_soft = spec
                    btn.setStyleSheet(
                        _status_toggle_btn_qss(
                            fg, bg_soft, active=(status_label == selected)
                        )
                    )

            def _set_status(label: str) -> None:
                si = status_combo.findData(label)
                if si >= 0:
                    status_combo.setCurrentIndex(si)
                _sync_status_toggle_styles(label)

            for i, (status_label, (btn_text, fg, bg_soft)) in enumerate(
                _APPT_STATUS_TOGGLE_SPECS.items()
            ):
                btn = QPushButton(btn_text)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setEnabled(can_edit)
                btn.setStyleSheet(
                    _status_toggle_btn_qss(
                        fg, bg_soft, active=(status_label == current_status)
                    )
                )
                btn.clicked.connect(
                    lambda _checked=False, s=status_label: _set_status(s)
                )
                status_toggle_btns[status_label] = btn
                quick_grid.addWidget(btn, 0, i)

            status_combo.currentIndexChanged.connect(
                lambda _ix: _sync_status_toggle_styles(
                    str(status_combo.currentData() or "")
                )
            )

            actions_layout.addLayout(quick_grid)

            ctrl_row = QHBoxLayout()
            ctrl_row.setSpacing(6)
            status_lbl = QLabel("Trạng thái")
            status_lbl.setStyleSheet("color:rgba(15,23,42,0.65); font:700 10pt 'Segoe UI';")
            ctrl_row.addWidget(status_lbl)
            status_combo.setEnabled(can_edit)
            status_combo.setFixedHeight(32)
            ctrl_row.addWidget(status_combo, 1)
            emp_lbl = QLabel("👤 NV phụ trách")
            emp_lbl.setStyleSheet("color:rgba(15,23,42,0.65); font:700 10pt 'Segoe UI';")
            ctrl_row.addWidget(emp_lbl)
            emp_combo.setFixedHeight(32)
            emp_combo.setStyleSheet(
                "QComboBox{min-height:28px;max-height:32px;padding:2px 8px;font:600 10pt 'Segoe UI';}"
            )
            ctrl_row.addWidget(emp_combo, 1)
            actions_layout.addLayout(ctrl_row)

            if not can_edit:
                hint = QLabel("Bạn không phải nhân viên phụ trách — chỉ xem, không chỉnh sửa.")
                hint.setStyleSheet(f"color:{THEME.danger}; font:700 9pt 'Segoe UI';")
                hint.setWordWrap(True)
                actions_layout.addWidget(hint)

            root.addWidget(actions_card)

        # Dịch vụ + tổng tiền (style bảng kê POS)
        try:
            svc_items = appointment_service_dao.list_by_appointment(appt_id)
        except Exception:
            svc_items = []

        svc_card = QFrame()
        svc_card.setStyleSheet(
            "QFrame{background:rgba(255,255,255,0.94); border:1px solid #D6E2F7; border-radius:12px;}"
        )
        svc_layout = QVBoxLayout(svc_card)
        svc_layout.setContentsMargins(16, 14, 16, 14)
        svc_layout.setSpacing(12)

        svc_title = QLabel("Thú cưng & dịch vụ")
        svc_title.setStyleSheet("font:800 11pt 'Segoe UI'; color:#0F172A;")
        svc_layout.addWidget(svc_title)

        svc_table = QTableWidget()
        svc_table.setColumnCount(5)
        svc_table.setHorizontalHeaderLabels(["Thú cưng", "Dịch vụ", "SL", "Đơn giá", "T.Tiền"])
        self._setup_table(svc_table)
        svc_vh = svc_table.verticalHeader()
        svc_vh.setDefaultSectionSize(50)
        svc_vh.setMinimumSectionSize(50)
        total_amount = 0.0
        svc_table.setRowCount(len(svc_items))
        for r, it in enumerate(svc_items):
            qty = int(it.get("quantity") or 1)
            unit_price = float(it.get("unit_price") or 0)
            line_total = qty * unit_price
            total_amount += line_total
            svc_name = str(it.get("service_name") or "")
            pet_name = str(it.get("pet_name") or "—")
            svc_table.setItem(r, 0, QTableWidgetItem(pet_name))
            svc_table.setItem(r, 1, QTableWidgetItem(svc_name))
            svc_table.setItem(r, 2, QTableWidgetItem(str(qty)))
            svc_table.setItem(r, 3, QTableWidgetItem(self._format_vnd(unit_price)))
            svc_table.setItem(r, 4, QTableWidgetItem(self._format_vnd(line_total)))
        hdr = svc_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setDefaultSectionSize(34)
        visible_rows = max(len(svc_items), 3)
        table_h = 40 + visible_rows * 50
        svc_table.setMinimumHeight(table_h)
        svc_table.setFixedHeight(table_h)
        svc_layout.addWidget(svc_table)

        summary_frame = QFrame()
        summary_frame.setStyleSheet(
            f"QFrame{{background:{THEME.accent_strong}; border-radius:8px;}}"
        )
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(16, 12, 16, 12)
        total_lbl = QLabel(f"Tổng dịch vụ: {self._format_vnd(total_amount or a.get('total_amount'))}")
        total_lbl.setStyleSheet("font:900 12pt 'Segoe UI'; color:#FFFFFF;")
        summary_layout.addWidget(total_lbl)
        summary_layout.addStretch(1)
        svc_layout.addWidget(summary_frame)
        root.addWidget(svc_card)

        if current_status == "Hoàn thành" and appt_id > 0:
            retail_card, _refresh_retail = self._create_appointment_retail_section(
                appt_id, dlg
            )
            root.addWidget(retail_card)

        result_row = QHBoxLayout()
        result_row.setSpacing(6)
        result_lbl = QLabel("Kết quả dịch vụ")
        result_lbl.setStyleSheet("font:800 11pt 'Segoe UI'; color:#0F172A;")
        result_row.addWidget(result_lbl)
        root.addLayout(result_row)

        result_edit = QPlainTextEdit()
        result_edit.setPlaceholderText("Nhập kết quả dịch vụ..." if not is_history else "")
        result_edit.setPlainText(str(a.get("note") or ""))
        result_edit.setReadOnly(is_history or not can_edit)
        result_edit.setFixedHeight(100)
        root.addWidget(result_edit)

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        if is_history or not can_edit:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
            if close_btn is not None:
                close_btn.setText("Đóng")
            buttons.rejected.connect(dlg.reject)
        else:
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close
            )
            save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
            if save_btn is not None:
                save_btn.setText("Lưu thay đổi")

            def _on_save() -> None:
                if appt_id <= 0:
                    QMessageBox.warning(dlg, "Lưu", "ID lịch hẹn không hợp lệ.")
                    return
                new_status = str(status_combo.currentData() or status_combo.currentText())
                try:
                    if is_admin:
                        new_emp = emp_combo.currentData()
                        new_emp_id = int(new_emp) if isinstance(new_emp, int) and new_emp > 0 else None
                        if new_emp_id != (int(current_emp) if current_emp else None):
                            appointment_service.assign_employee(appt_id, new_emp_id)
                    appointment_service.update_status(appt_id, new_status)
                    appointment_service.update_result_note(appt_id, result_edit.toPlainText())
                except Exception as exc:
                    QMessageBox.warning(dlg, "Lưu", str(exc))
                    return
                self._reload_appointments_table()
                if new_status in APPOINTMENT_HISTORY_STATUSES:
                    QMessageBox.information(
                        dlg,
                        "Hoàn tất",
                        f"Lịch hẹn đã chuyển sang tab Lịch sử ({new_status}).",
                    )
                dlg.accept()

            buttons.accepted.connect(_on_save)
            buttons.rejected.connect(dlg.reject)

        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(0, 6, 0, 0)
        btn_bar.addStretch(1)
        btn_bar.addWidget(buttons)
        outer.addLayout(btn_bar)

        dlg.adjustSize()
        dlg.setFixedHeight(min(dlg.sizeHint().height() + 8, 860))
        dlg.exec()

    @staticmethod
    def _fmt_dt_safe(dt) -> str:
        try:
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(dt or "")

    def _on_confirm_appointment_db(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return

        cid = ap_page.customerCombo.currentData()
        if not isinstance(cid, int) or not cid:
            QMessageBox.warning(self, "Đặt lịch", "Vui lòng chọn khách hàng.")
            return

        scheduled_at = ap_page.timeEdit.dateTime().toPyDateTime()

        # thu thap pet da check (giu nguyen thu tu theo widget)
        checked_items: list[tuple[int, str]] = []
        for i in range(ap_page.petListWidget.count()):
            it = ap_page.petListWidget.item(i)
            if it and it.checkState() == Qt.CheckState.Checked:
                pid = it.data(Qt.ItemDataRole.UserRole)
                if isinstance(pid, int):
                    checked_items.append((pid, it.text()))

        if not checked_items:
            QMessageBox.warning(self, "Đặt lịch", "Vui lòng chọn ít nhất một thú cưng.")
            return

        # Xay dung plan (pet_id, service_id, qty=1) cho 1 appointment gop nhieu pet
        plan: list[tuple[int, int, int]] = []
        per_pet = len(checked_items) >= 2
        if per_pet:
            missing: list[str] = []
            for pid, name in checked_items:
                combo = self._per_pet_service_combos.get(name)
                sid = combo.currentData() if combo else 0
                if not isinstance(sid, int) or sid <= 0:
                    missing.append(name)
                else:
                    plan.append((pid, sid, 1))
            if missing:
                QMessageBox.warning(
                    self, "Đặt lịch", "Vui lòng chọn dịch vụ cho: " + ", ".join(missing)
                )
                return
        else:
            sid = ap_page.serviceCombo.currentData()
            if not isinstance(sid, int) or sid <= 0:
                QMessageBox.warning(self, "Đặt lịch", "Vui lòng chọn dịch vụ.")
                return
            plan.append((checked_items[0][0], sid, 1))

        try:
            appt_id = appointment_service.create_appointment_multi(
                customer_id=cid,
                scheduled_at=scheduled_at,
                plan=plan,
            )
        except appointment_service.AppointmentError as exc:
            QMessageBox.warning(self, "Đặt lịch", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Đặt lịch", str(exc))
            return

        pet_names = ", ".join(n for _, n in checked_items)
        QMessageBox.information(
            self,
            "Đặt lịch",
            f"Đã tạo lịch hẹn #{appt_id} cho {len(checked_items)} thú cưng ({pet_names}).",
        )
        self._reload_appointments_table()
        self._reset_appointment_form()

    def _reset_appointment_form(self) -> None:
        """Reset form dat lich ve trang thai ban dau sau khi tao thanh cong."""
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return

        ap_page.customerCombo.blockSignals(True)
        if ap_page.customerCombo.count() > 0:
            ap_page.customerCombo.setCurrentIndex(0)
        ap_page.customerCombo.blockSignals(False)

        ap_page.petListWidget.blockSignals(True)
        ap_page.petListWidget.clear()
        ap_page.petListWidget.blockSignals(False)

        if ap_page.serviceCombo.count() > 0:
            ap_page.serviceCombo.setCurrentIndex(0)

        for combo in list(self._per_pet_service_combos.values()):
            if combo.count() > 0:
                combo.setCurrentIndex(0)
        self._update_per_pet_service_ui()

        ap_page.timeEdit.setDateTime(QDateTime.currentDateTime().addSecs(3600))

    def _on_quick_add_customer_for_appointment(self) -> None:
        """Mo dialog them khach hang moi (kem nhieu thu cung) ngay tu trang dat lich.

        Sau khi tao xong, tu dong refresh combo khach hang va select khach moi.
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm khách hàng mới")
        dlg.setMinimumWidth(640)
        dlg.resize(680, 600)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        title = QLabel("Nhập thông tin khách hàng")
        title.setStyleSheet("font: 800 12pt 'Segoe UI'; color: #0F172A;")
        layout.addWidget(title)

        cust_form = QFormLayout()
        cust_form.setSpacing(10)
        name_edit = QLineEdit()
        phone_edit = QLineEdit()
        address_edit = QLineEdit()
        email_edit = QLineEdit()
        name_edit.setPlaceholderText("VD: Nguyễn Văn A")
        phone_edit.setPlaceholderText("VD: 0901234567")
        address_edit.setPlaceholderText("Địa chỉ (tuỳ chọn)")
        email_edit.setPlaceholderText("Email (tuỳ chọn)")
        cust_form.addRow("Tên khách hàng *", name_edit)
        cust_form.addRow("Số điện thoại *", phone_edit)
        cust_form.addRow("Địa chỉ", address_edit)
        cust_form.addRow("Email", email_edit)
        layout.addLayout(cust_form)

        pet_title = QLabel("Thú cưng (tuỳ chọn — có thể thêm nhiều con)")
        pet_title.setStyleSheet("font: 800 10pt 'Segoe UI'; color:#0F172A; margin-top:6px;")
        layout.addWidget(pet_title)

        # --- Form nhap 1 thu cung ---
        pet_row = QHBoxLayout()
        pet_row.setSpacing(8)
        pet_name = QLineEdit()
        pet_name.setPlaceholderText("Tên *")
        pet_species = QLineEdit()
        pet_species.setPlaceholderText("Loài * (VD: Chó, Mèo)")
        pet_breed = QLineEdit()
        pet_breed.setPlaceholderText("Giống")
        pet_age = QSpinBox()
        pet_age.setRange(0, 50)
        pet_age.setSuffix(" tuổi")
        pet_row.addWidget(pet_name, 2)
        pet_row.addWidget(pet_species, 2)
        pet_row.addWidget(pet_breed, 2)
        pet_row.addWidget(pet_age, 1)

        add_pet_btn = QPushButton("＋ Thêm vào danh sách")
        add_pet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_pet_btn.setStyleSheet(
            "QPushButton{background:#DCFCE7;color:#166534;border:none;padding:6px 12px;border-radius:8px;font:700 9pt 'Segoe UI';}"
            "QPushButton:hover{background:#BBF7D0;}"
        )
        pet_row.addWidget(add_pet_btn)
        layout.addLayout(pet_row)

        # --- Bang danh sach pet se tao ---
        pets_table = QTableWidget()
        pets_table.setColumnCount(5)
        pets_table.setHorizontalHeaderLabels(["Tên", "Loài", "Giống", "Tuổi", ""])
        self._setup_table(pets_table)
        pets_table.setMinimumHeight(160)
        pets_table.horizontalHeader().setStretchLastSection(False)
        pets_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        pets_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        pets_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        pets_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        pets_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(pets_table, 1)

        pending_pets: list[dict] = []

        def _refresh_pets_table() -> None:
            pets_table.setRowCount(len(pending_pets))
            for r, p in enumerate(pending_pets):
                pets_table.setItem(r, 0, QTableWidgetItem(p["name"]))
                pets_table.setItem(r, 1, QTableWidgetItem(p["species"]))
                pets_table.setItem(r, 2, QTableWidgetItem(p["breed"] or ""))
                pets_table.setItem(r, 3, QTableWidgetItem(str(p["age"])))
                btn_del = _build_action_icon_button(
                    _action_icon("trash", "#B91C1C"),
                    "Xóa",
                    "#FEE2E2",
                    "#B91C1C",
                    hover="#FCA5A5",
                    hover_fg="#7F1D1D",
                )
                btn_del.clicked.connect(lambda _=False, idx=r: _remove_pending_pet(idx))
                pets_table.setCellWidget(r, 4, btn_del)

        def _remove_pending_pet(idx: int) -> None:
            if 0 <= idx < len(pending_pets):
                pending_pets.pop(idx)
                _refresh_pets_table()

        def _on_add_pet_to_list() -> None:
            nm = pet_name.text().strip()
            sp = pet_species.text().strip()
            if not nm or not sp:
                QMessageBox.warning(dlg, "Thêm thú cưng", "Vui lòng nhập Tên và Loài.")
                return
            pending_pets.append(
                {
                    "name": nm,
                    "species": sp,
                    "breed": pet_breed.text().strip() or None,
                    "age": int(pet_age.value()),
                }
            )
            _refresh_pets_table()
            pet_name.clear()
            pet_species.clear()
            pet_breed.clear()
            pet_age.setValue(0)
            pet_name.setFocus()

        add_pet_btn.clicked.connect(_on_add_pet_to_list)

        hint = QLabel(
            "Lưu ý: điền thông tin 1 thú cưng rồi bấm “＋ Thêm vào danh sách”. "
            "Sau khi bấm “Thêm” ở dưới, khách hàng và tất cả thú cưng trong danh sách sẽ được tạo."
        )
        hint.setStyleSheet("color:#64748B; font:600 8.5pt 'Segoe UI';")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Thêm")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        created = {"customer_id": None, "pet_count": 0}

        def _on_ok() -> None:
            # Neu con du lieu trong o nhap thu cung thi tu dong day vao list truoc khi luu
            if pet_name.text().strip() or pet_species.text().strip():
                nm = pet_name.text().strip()
                sp = pet_species.text().strip()
                if not nm or not sp:
                    QMessageBox.warning(
                        dlg,
                        "Thêm thú cưng",
                        "Ô nhập thú cưng còn thiếu Tên hoặc Loài. Hãy bấm “＋ Thêm vào danh sách” hoặc xoá các ô đó.",
                    )
                    return
                pending_pets.append(
                    {
                        "name": nm,
                        "species": sp,
                        "breed": pet_breed.text().strip() or None,
                        "age": int(pet_age.value()),
                    }
                )

            try:
                cust_id = customer_service.create_customer(
                    name_edit.text(),
                    phone_edit.text(),
                    address_edit.text(),
                    email_edit.text(),
                )
            except customer_service.CustomerError as exc:
                QMessageBox.warning(dlg, "Thêm khách hàng", str(exc))
                return
            except Exception as exc:
                QMessageBox.critical(dlg, "Thêm khách hàng", str(exc))
                return

            created_pets = 0
            failed: list[str] = []
            for p in pending_pets:
                try:
                    pet_service.create_pet(
                        int(cust_id),
                        p["name"],
                        p["species"],
                        p["breed"],
                        int(p["age"]),
                    )
                    created_pets += 1
                except pet_service.PetError as exc:
                    failed.append(f"{p['name']}: {exc}")
                except Exception as exc:
                    failed.append(f"{p['name']}: {exc}")

            created["customer_id"] = int(cust_id)
            created["pet_count"] = created_pets

            if failed:
                QMessageBox.warning(
                    dlg,
                    "Thêm thú cưng",
                    "Đã tạo khách hàng và "
                    f"{created_pets}/{len(pending_pets)} thú cưng.\nLỗi:\n- "
                    + "\n- ".join(failed),
                )
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        new_cid = created.get("customer_id")
        if not isinstance(new_cid, int):
            return

        self._reload_customers(None)
        self._reload_pets()

        ap_page = self._pages.get("appointments")
        if ap_page is not None:
            combo = ap_page.customerCombo
            idx = combo.findData(new_cid)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        QMessageBox.information(
            self,
            "Thêm khách hàng",
            f"Đã thêm khách hàng mới (ID: {new_cid}) kèm {created.get('pet_count', 0)} thú cưng.",
        )

    # ===================== GROUP B: CATALOG (Customer/Pet/Service) =====================

    def _reload_customers(self, query: str | None) -> None:
        if not self._has_active_session():
            return
        q = (query or "").strip()
        self._customers = list(customer_service.list_customers(q or None))
        self._render_customers_table()
        self._refresh_pets_customer_filter()
        self._refresh_appointments_customer_combo()

    def _reload_services(self, query: str | None = None) -> None:
        if not self._has_active_session():
            return
        q = (query or "").strip() or None
        services_page = self._pages.get("services")
        # Trang dich vu: ho tro tim kiem
        if q is None and services_page and hasattr(services_page, "searchEdit"):
            q = (services_page.searchEdit.text() or "").strip() or None
        # Cho dropdown trong dat lich, luon load tat ca dich vu hoat dong
        all_active = list(service_service.list_services(active_only=True))
        if q:
            ql = q.lower()
            visible = [
                s for s in all_active
                if ql in (s.name or "").lower()
                or ql in (s.description or "").lower()
            ]
        else:
            visible = all_active
        self._services_list = all_active
        self._services_visible = visible  # dung de render bang
        self._render_services_table()
        self._refresh_appointment_services_combo()

    def _refresh_appointment_services_combo(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        ap_page.serviceCombo.blockSignals(True)
        ap_page.serviceCombo.clear()
        ap_page.serviceCombo.addItem("Chọn dịch vụ", 0)
        for s in self._services_list:
            ap_page.serviceCombo.addItem(f"{s.name} ({int(s.price):,}đ)".replace(",", "."), s.id)
        ap_page.serviceCombo.blockSignals(False)

    def _reload_pets(self) -> None:
        if not self._has_active_session():
            return
        pets_page = self._pages.get("pets")
        selected = None
        if pets_page:
            data = pets_page.customerFilterCombo.currentData()
            if isinstance(data, int):
                selected = data
        self._pets = list(pet_service.list_pets(customer_id=selected))
        self._render_pets_table()
        self._refresh_appointment_pet_list()

    def _render_customers_table(self) -> None:
        customers_page = self._pages.get("customers")
        if not customers_page:
            return
        table: QTableWidget = customers_page.customersTable
        table.setRowCount(len(self._customers))
        for r, c in enumerate(self._customers):
            table.setItem(r, 0, QTableWidgetItem(str(c.id)))
            table.setItem(r, 1, QTableWidgetItem(c.full_name))
            table.setItem(r, 2, QTableWidgetItem(c.phone))
            table.setItem(r, 3, QTableWidgetItem(c.address or ""))
            table.setCellWidget(r, 4, self._make_row_actions(
                on_edit=lambda _, cid=c.id: self._on_edit_customer_clicked(cid),
                on_delete=lambda _, cid=c.id: self._on_delete_customer_clicked(cid),
            ))

        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(4, 220)

    # ===================== PRODUCTS (do an / phu kien) =====================

    def _reload_employees(self) -> None:
        if not self._has_active_session():
            return
        try:
            self._employees_list = list(user_service.list_employees(active_only=True))
        except Exception:
            self._employees_list = []

    # ======= Trang quan ly nhan vien + thong ke doanh so =======================

    def _reload_employees_stats(self) -> None:
        """Tai bao cao quan ly nhan vien (toan thoi gian) + render bang.

        Doanh so theo khoang thoi gian da chuyen sang Dashboard.
        """
        if not Session.is_admin():
            self._employees_stats = []
            self._render_employees_table()
            return
        try:
            report = report_service.employee_performance_stats()
        except Exception as exc:
            QMessageBox.warning(self, "Nhân viên", f"Không tải được danh sách nhân viên: {exc}")
            self._employees_stats = []
            self._render_employees_table()
            return

        self._employees_stats = list(report.employees)
        self._render_employees_table()

    def _render_employees_table(self) -> None:
        emp_page = self._pages.get("employees")
        if not emp_page or not hasattr(emp_page, "employeesTable"):
            return
        table: QTableWidget = emp_page.employeesTable

        keyword = ""
        if hasattr(emp_page, "searchEdit"):
            keyword = (emp_page.searchEdit.text() or "").strip().lower()

        rows = self._employees_stats
        if keyword:
            def _match(e) -> bool:
                blob = " ".join([
                    (e.full_name or ""),
                    (e.username or ""),
                    (e.phone or ""),
                ]).lower()
                return keyword in blob
            rows = [e for e in rows if _match(e)]

        table.setRowCount(len(rows))
        for r, e in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(e.full_name))
            table.setItem(r, 1, QTableWidgetItem(e.username))
            table.setItem(r, 2, QTableWidgetItem(e.phone or ""))
            status_item = QTableWidgetItem(
                "Đang làm" if e.is_active else "Đã khoá"
            )
            status_item.setForeground(
                QColor("#15803D") if e.is_active else QColor("#B91C1C")
            )
            table.setItem(r, 3, status_item)
            table.setItem(r, 4, QTableWidgetItem(str(e.appointment_count)))
            done_item = QTableWidgetItem(
                f"{e.appointment_done}/{e.appointment_count}"
            )
            table.setItem(r, 5, done_item)
            table.setCellWidget(
                r,
                6,
                self._make_employee_row_actions(e),
            )

        for r in range(table.rowCount()):
            table.resizeRowToContents(r)
            cw = table.cellWidget(r, 6)
            if cw is not None:
                need = cw.sizeHint().height() + 12
                if table.rowHeight(r) < need:
                    table.setRowHeight(r, need)

        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(6, 320)

    def _make_employee_row_actions(self, emp) -> QWidget:
        """Tao cum nut hanh dong cho 1 nhan vien."""
        wrap = QWidget()
        h = QHBoxLayout(wrap)
        h.setContentsMargins(8, 6, 8, 6)
        h.setSpacing(6)
        h.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        btn_detail = QPushButton("Chi tiết")
        btn_detail.setStyleSheet(_EMPLOYEE_ROW_BTN_QSS)
        btn_detail.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_detail.clicked.connect(lambda _=False, eid=emp.employee_id: self._show_employee_detail_dialog(eid))
        h.addWidget(btn_detail, 0, Qt.AlignmentFlag.AlignVCenter)

        btn_edit = QPushButton("Sửa")
        btn_edit.setStyleSheet(_EMPLOYEE_ROW_BTN_QSS)
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.clicked.connect(lambda _=False, eid=emp.employee_id: self._on_edit_employee_clicked(eid))
        h.addWidget(btn_edit, 0, Qt.AlignmentFlag.AlignVCenter)

        btn_pw = QPushButton("Reset MK")
        btn_pw.setStyleSheet(_EMPLOYEE_ROW_BTN_QSS)
        btn_pw.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pw.clicked.connect(lambda _=False, eid=emp.employee_id: self._on_reset_employee_password(eid))
        h.addWidget(btn_pw, 0, Qt.AlignmentFlag.AlignVCenter)

        btn_lock = QPushButton("Khoá" if emp.is_active else "Mở khoá")
        btn_lock.setStyleSheet(_EMPLOYEE_ROW_BTN_QSS)
        btn_lock.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_lock.clicked.connect(
            lambda _=False, eid=emp.employee_id, active=emp.is_active:
            self._on_toggle_employee_active(eid, active)
        )
        h.addWidget(btn_lock, 0, Qt.AlignmentFlag.AlignVCenter)

        h.addStretch(1)
        return wrap

    def _on_add_employee_clicked(self) -> None:
        if not Session.is_admin():
            QMessageBox.warning(self, "Thêm nhân viên", "Chỉ Admin mới được thực hiện.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm nhân viên")
        dlg.setMinimumWidth(520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        username = QLineEdit()
        full_name = QLineEdit()
        phone = QLineEdit()
        pw = QLineEdit()
        pw.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username *", username)
        form.addRow("Họ tên *", full_name)
        form.addRow("SĐT", phone)
        form.addRow("Mật khẩu *", pw)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Thêm")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                user_service.admin_create_user(
                    role_name="EMPLOYEE",
                    username=username.text(),
                    password=pw.text(),
                    full_name=full_name.text(),
                    phone=phone.text(),
                )
            except user_service.UserError as exc:
                QMessageBox.warning(dlg, "Thêm nhân viên", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_employees()
            self._reload_employees_stats()

    def _on_edit_employee_clicked(self, user_id: int) -> None:
        if not Session.is_admin():
            return
        try:
            users = user_service.list_users(active_only=False)
        except Exception as exc:
            QMessageBox.warning(self, "Sửa nhân viên", str(exc))
            return
        u = next((x for x in users if int(x["id"]) == int(user_id)), None)
        if u is None:
            QMessageBox.warning(self, "Sửa nhân viên", "Không tìm thấy nhân viên.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Sửa nhân viên #{user_id}")
        dlg.setMinimumWidth(520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        full_name = QLineEdit(u["full_name"])
        phone = QLineEdit(u.get("phone") or "")
        form.addRow("Họ tên *", full_name)
        form.addRow("SĐT", phone)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Lưu")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                user_service.admin_update_user(int(user_id), full_name.text(), phone.text())
            except user_service.UserError as exc:
                QMessageBox.warning(dlg, "Sửa nhân viên", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_employees()
            self._reload_employees_stats()

    def _on_reset_employee_password(self, user_id: int) -> None:
        if not Session.is_admin():
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Reset mật khẩu #{user_id}")
        dlg.setMinimumWidth(420)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        pw = QLineEdit()
        pw.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Mật khẩu mới *", pw)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Lưu")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                user_service.admin_reset_password(int(user_id), pw.text())
            except user_service.UserError as exc:
                QMessageBox.warning(dlg, "Reset mật khẩu", str(exc))
                return
            QMessageBox.information(dlg, "Reset mật khẩu", "Đã cập nhật mật khẩu.")
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)
        dlg.exec()

    def _on_toggle_employee_active(self, user_id: int, currently_active: bool) -> None:
        if not Session.is_admin():
            return
        action = "khoá" if currently_active else "mở khoá"
        confirm = QMessageBox.question(
            self,
            f"{action.capitalize()} nhân viên",
            f"Bạn có chắc muốn {action} nhân viên #{user_id}?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            user_service.admin_set_active(int(user_id), not currently_active)
        except user_service.UserError as exc:
            QMessageBox.warning(self, f"{action.capitalize()} nhân viên", str(exc))
            return
        self._reload_employees()
        self._reload_employees_stats()

    def _show_employee_detail_dialog(self, employee_id: int) -> None:
        emp = next(
            (e for e in self._employees_stats if int(e.employee_id) == int(employee_id)),
            None,
        )
        if emp is None:
            QMessageBox.warning(self, "Chi tiết nhân viên", "Không tìm thấy nhân viên.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Nhân viên: {emp.full_name}")
        dlg.resize(900, 600)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        root = QVBoxLayout(dlg)
        root.setSpacing(10)

        title = QLabel(f"{emp.full_name} (@{emp.username})")
        title.setStyleSheet("font: 900 14pt 'Segoe UI'; color: #0F172A;")
        root.addWidget(title)

        info = QLabel(
            f"SĐT: {emp.phone or '—'}  |  "
            f"Trạng thái: {'Đang làm' if emp.is_active else 'Đã khoá'}"
        )
        info.setStyleSheet("color:#475569;")
        root.addWidget(info)

        # KPIs
        kpi = QGridLayout()
        kpi.setSpacing(10)

        def _add_kpi(row: int, col: int, label: str, value: str) -> None:
            box = QFrame()
            box.setStyleSheet(
                "QFrame{background: rgba(255,255,255,0.92); border:1px solid #D6E2F7; border-radius:12px;}"
            )
            lay = QVBoxLayout(box)
            lay.setContentsMargins(12, 10, 12, 10)
            t = QLabel(label)
            t.setStyleSheet("color:#5B6A87; font-weight:600; font-size:11px;")
            v = QLabel(value)
            v.setStyleSheet("color:#0F172A; font-weight:800; font-size:16px;")
            lay.addWidget(t)
            lay.addWidget(v)
            kpi.addWidget(box, row, col)

        _add_kpi(0, 0, "LỊCH HẸN", str(emp.appointment_count))
        _add_kpi(0, 1, "HOÀN THÀNH", str(emp.appointment_done))
        _add_kpi(0, 2, "ĐANG XỬ LÝ", str(emp.appointment_in_progress))
        _add_kpi(0, 3, "CHỜ XỬ LÝ", str(emp.appointment_pending))
        _add_kpi(1, 0, "HĐ DỊCH VỤ", report_service.format_vnd(emp.service_revenue))
        _add_kpi(1, 1, "HĐ BÁN LẺ", report_service.format_vnd(emp.retail_revenue))
        _add_kpi(1, 2, "TỔNG DOANH THU", report_service.format_vnd(emp.total_revenue))
        _add_kpi(1, 3, "TỔNG HĐ", str(emp.invoice_count))
        root.addLayout(kpi)

        # Lich hen + hoa don gan day
        lists_row = QHBoxLayout()
        lists_row.setSpacing(12)

        # Cot 1: Lich hen
        appts_box = QFrame()
        appts_box.setStyleSheet(
            "QFrame{background: rgba(255,255,255,0.92); border:1px solid #D6E2F7; border-radius:12px;}"
        )
        appts_lay = QVBoxLayout(appts_box)
        appts_lay.setContentsMargins(12, 12, 12, 12)
        appts_title = QLabel("Lịch hẹn gần đây")
        appts_title.setStyleSheet("font:700 11pt 'Segoe UI';")
        appts_lay.addWidget(appts_title)
        appts_table = QTableWidget(0, 4)
        appts_table.setHorizontalHeaderLabels(["Thời gian", "Khách", "Dịch vụ", "TT"])
        appts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        appts_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        appts_table.verticalHeader().setVisible(False)
        try:
            appts_rows = report_service.employee_recent_appointments(employee_id, 30)
        except Exception:
            appts_rows = []
        status_map = {
            "CHO_XU_LY": "Chờ xử lý",
            "DANG_THUC_HIEN": "Đang thực hiện",
            "HOAN_THANH": "Hoàn thành",
            "HUY": "Huỷ",
        }
        appts_table.setRowCount(len(appts_rows))
        for r, row in enumerate(appts_rows):
            sched = row.get("scheduled_at")
            sched_str = sched.strftime("%d/%m/%Y %H:%M") if sched else ""
            appts_table.setItem(r, 0, QTableWidgetItem(sched_str))
            appts_table.setItem(r, 1, QTableWidgetItem(row.get("customer_name") or ""))
            appts_table.setItem(r, 2, QTableWidgetItem(row.get("service_name") or ""))
            appts_table.setItem(
                r, 3, QTableWidgetItem(status_map.get(row.get("status") or "", row.get("status") or ""))
            )
        appts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        appts_lay.addWidget(appts_table)
        lists_row.addWidget(appts_box, 1)

        # Cot 2: Hoa don
        inv_box = QFrame()
        inv_box.setStyleSheet(
            "QFrame{background: rgba(255,255,255,0.92); border:1px solid #D6E2F7; border-radius:12px;}"
        )
        inv_lay = QVBoxLayout(inv_box)
        inv_lay.setContentsMargins(12, 12, 12, 12)
        inv_title = QLabel("Hoá đơn gần đây")
        inv_title.setStyleSheet("font:700 11pt 'Segoe UI';")
        inv_lay.addWidget(inv_title)
        inv_table = QTableWidget(0, 5)
        inv_table.setHorizontalHeaderLabels(["Số HĐ", "Ngày", "Loại", "Khách", "Tổng"])
        inv_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        inv_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        inv_table.verticalHeader().setVisible(False)
        try:
            inv_rows = report_service.employee_recent_invoices(employee_id, 30)
        except Exception:
            inv_rows = []
        inv_table.setRowCount(len(inv_rows))
        for r, row in enumerate(inv_rows):
            issued = row.get("issued_at")
            issued_str = issued.strftime("%d/%m/%Y") if issued else ""
            inv_type = "Bán lẻ" if (row.get("invoice_type") == "RETAIL") else "Dịch vụ"
            inv_table.setItem(r, 0, QTableWidgetItem(row.get("invoice_no") or ""))
            inv_table.setItem(r, 1, QTableWidgetItem(issued_str))
            inv_table.setItem(r, 2, QTableWidgetItem(inv_type))
            inv_table.setItem(r, 3, QTableWidgetItem(row.get("customer_name") or ""))
            inv_table.setItem(
                r, 4, QTableWidgetItem(report_service.format_vnd(row.get("total_amount")))
            )
        inv_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        inv_lay.addWidget(inv_table)
        lists_row.addWidget(inv_box, 1)

        root.addLayout(lists_row)

        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(dlg.accept)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

        dlg.exec()

    def _reload_products(self, query: str | None = None) -> None:
        if not self._has_active_session():
            return
        products_page = self._pages.get("products")
        q = (query or "").strip() or None
        if q is None and products_page and hasattr(products_page, "searchEdit"):
            q = (products_page.searchEdit.text() or "").strip() or None
        category = ""
        if products_page and hasattr(products_page, "categoryFilterCombo"):
            data = products_page.categoryFilterCombo.currentData()
            if isinstance(data, str):
                category = data
        try:
            self._products_list = list(
                product_service.list_products(
                    active_only=True, query=q, category=category or None
                )
            )
        except Exception:
            self._products_list = []
        self._render_products_table()

    def _sync_products_grid_metrics(self) -> None:
        """O luoi san pham: 6 cot bang nhau (theo viewport), hang co chieu cao da set san."""
        products_page = self._pages.get("products")
        if not products_page or not self._products_list:
            return
        grid = getattr(products_page, "productsGridLayout", None)
        container = getattr(products_page, "productsGridContainer", None)
        sa: QScrollArea | None = getattr(products_page, "productsScrollArea", None)
        if grid is None or container is None:
            return
        cols = 6
        cell_floor = 170
        sp = grid.horizontalSpacing()
        mg = grid.contentsMargins()
        base_min = cols * cell_floor + max(0, cols - 1) * sp + mg.left() + mg.right()
        vw = sa.viewport().width() if sa is not None else 0
        w = max(base_min, vw, container.minimumWidth())
        container.setMinimumWidth(w)
        inner = w - mg.left() - mg.right() - max(0, cols - 1) * sp
        col_w = max(cell_floor, inner // cols)
        for c in range(cols):
            grid.setColumnMinimumWidth(c, col_w)
            grid.setColumnStretch(c, 1)
        grid.invalidate()
        container.updateGeometry()

    def _render_products_table(self) -> None:
        products_page = self._pages.get("products")
        if not products_page or not hasattr(products_page, "productsGridLayout"):
            return

        grid: QGridLayout = products_page.productsGridLayout
        _clear_grid_layout(grid)

        rows = self._products_list
        thumb = 92

        if not rows:
            empty = QLabel("Chưa có sản phẩm nào (hoặc không khớp bộ lọc).")
            empty.setStyleSheet("color:#64748B; font:700 10pt 'Segoe UI'; padding: 28px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(empty, 0, 0, 1, 6)
            if hasattr(products_page, "productsGridContainer"):
                products_page.productsGridContainer.setMinimumWidth(0)
            return

        cols = 6
        cell_min = 170
        for c in range(cols):
            grid.setColumnStretch(c, 1)

        card_refs: list[QFrame] = []

        for idx, p in enumerate(rows):
            card = QFrame()
            card.setObjectName("ProdCard")
            card.setStyleSheet(
                f"QFrame#ProdCard{{background:#FFFFFF; border:1px solid {THEME.border}; border-radius:12px;}}"
                f"QFrame#ProdCard QLabel{{border:none; margin:0; padding:0; background:transparent;}}"
            )
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

            row_lay = QHBoxLayout(card)
            row_lay.setContentsMargins(10, 8, 10, 8)
            row_lay.setSpacing(10)

            img_btn = QPushButton()
            img_btn.setFixedSize(thumb, thumb)
            img_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            img_btn.clicked.connect(lambda _=False, pid=p.id: self._on_product_image_pick(pid))
            img_btn.setStyleSheet(
                "QPushButton{background:#E8EEEB; border:1px dashed #94A3B8; border-radius:10px; font-size:30px;}"
                "QPushButton:hover{background:#D1E8DF; border-color:" + THEME.primary + ";}"
            )
            img_btn.setToolTip("Chọn ảnh (lưu tạm trong phiên)")
            img_btn.setIcon(self._product_thumb_icon(p.id, p.category, thumb - 6))
            img_btn.setIconSize(QSize(thumb - 6, thumb - 6))
            img_btn.setText("")
            row_lay.addWidget(img_btn, 0, Qt.AlignmentFlag.AlignTop)

            right = QWidget()
            right.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
            rv = QVBoxLayout(right)
            rv.setContentsMargins(0, 0, 0, 0)
            rv.setSpacing(3)
            rv.setAlignment(Qt.AlignmentFlag.AlignTop)

            nm = QLabel(p.name)
            nm.setObjectName("prodName")
            nm.setWordWrap(True)
            nm.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            nm.setStyleSheet(
                f"font:800 10pt 'Segoe UI'; color:{THEME.text_strong}; border:none; background:transparent;"
            )
            rv.addWidget(nm, 0, Qt.AlignmentFlag.AlignTop)

            cat_line = QLabel(product_service.CATEGORY_LABELS.get(p.category, p.category))
            cat_line.setStyleSheet(
                f"color:{THEME.muted}; font:9pt 'Segoe UI'; border:none; background:transparent;"
            )
            rv.addWidget(cat_line)

            pr_lbl = QLabel(f"{int(p.price):,} đ".replace(",", "."))
            pr_lbl.setStyleSheet(
                f"color:{THEME.primary}; font:800 11pt 'Segoe UI'; border:none; background:transparent;"
            )
            rv.addWidget(pr_lbl)

            sk = QLabel(f"Tồn: {p.stock}")
            if p.stock <= 0:
                sk.setStyleSheet(
                    "color:#B91C1C; font:600 9pt 'Segoe UI'; border:none; background:transparent;"
                )
            elif p.stock < 5:
                sk.setStyleSheet(
                    "color:#B45309; font:600 9pt 'Segoe UI'; border:none; background:transparent;"
                )
            else:
                sk.setStyleSheet(
                    f"color:{THEME.text_soft}; font:9pt 'Segoe UI'; border:none; background:transparent;"
                )
            rv.addWidget(sk)

            if p.sku:
                sku_lbl = QLabel(f"SKU: {p.sku}")
                sku_lbl.setWordWrap(True)
                sku_lbl.setStyleSheet(
                    f"color:{THEME.muted}; font:8pt 'Segoe UI'; border:none; background:transparent;"
                )
                rv.addWidget(sku_lbl)

            rv.addStretch(1)

            actions = self._make_row_actions(
                on_edit=lambda _, pid=p.id: self._on_edit_product_clicked(pid),
                on_delete=lambda _, pid=p.id: self._on_delete_product_clicked(pid),
                delete_text="Ẩn",
                compact_wrap=True,
            )
            rv.addWidget(actions, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

            row_lay.addWidget(right, 1, Qt.AlignmentFlag.AlignTop)

            gr = idx // cols
            gc = idx % cols
            grid.addWidget(card, gr, gc)
            card_refs.append(card)

        nrows = (len(rows) + cols - 1) // cols
        for r in range(nrows):
            grid.setRowStretch(r, 0)
            heights: list[int] = []
            for j in range(cols):
                i = r * cols + j
                if i < len(card_refs):
                    cr = card_refs[i]
                    cr.adjustSize()
                    heights.append(cr.sizeHint().height())
            if heights:
                row_h = max(heights)
                for j in range(cols):
                    i = r * cols + j
                    if i < len(card_refs):
                        card_refs[i].setFixedHeight(row_h)
                grid.setRowMinimumHeight(r, row_h)

        container = getattr(products_page, "productsGridContainer", None)
        if container is not None:
            container.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum,
            )
            mg = grid.contentsMargins()
            sp = grid.horizontalSpacing()
            fallback_w = cols * cell_min + max(0, cols - 1) * sp + mg.left() + mg.right()
            container.setMinimumWidth(fallback_w)
            grid.activate()
            container.adjustSize()
            ch = container.sizeHint()
            container.setMinimumHeight(max(1, ch.height()))
            self._sync_products_grid_metrics()
            QTimer.singleShot(0, self._sync_products_grid_metrics)

    def _product_placeholder_emoji(self, category: str) -> str:
        if category == "DO_AN":
            return "🍖"
        if category == "PHU_KIEN":
            return "🎀"
        return "🛒"

    def _product_category_bg(self, category: str) -> str:
        if category == "DO_AN":
            return "#FEF3C7"
        if category == "PHU_KIEN":
            return "#DBEAFE"
        return "#F1F5F9"

    def _product_thumb_pixmap(
        self,
        product_id: int | None,
        category: str,
        size: int = 48,
    ) -> QPixmap:
        px = max(24, int(size))
        if product_id is not None:
            path = self._product_images.get(int(product_id))
            if path and os.path.exists(path):
                raw = QPixmap(path)
                if not raw.isNull():
                    return raw.scaled(
                        px,
                        px,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
        pix = QPixmap(px, px)
        pix.fill(QColor(self._product_category_bg(category)))
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(QFont("Segoe UI Emoji", max(14, px // 2)))
        painter.drawText(
            pix.rect(),
            int(Qt.AlignmentFlag.AlignCenter),
            self._product_placeholder_emoji(category),
        )
        painter.end()
        return pix

    def _product_thumb_icon(
        self,
        product_id: int | None,
        category: str,
        size: int = 48,
    ) -> QIcon:
        return QIcon(self._product_thumb_pixmap(product_id, category, size))

    def _on_product_image_pick(self, product_id: int) -> None:
        if next((x for x in self._products_list if x.id == product_id), None) is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh sản phẩm",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if not path:
            return
        self._product_images[product_id] = path
        self._render_products_table()

    def _on_add_product_clicked(self) -> None:
        self._show_product_dialog(None)

    def _on_edit_product_clicked(self, product_id: int) -> None:
        self._show_product_dialog(product_id)

    def _on_delete_product_clicked(self, product_id: int) -> None:
        confirm = QMessageBox.question(
            self,
            "Ẩn sản phẩm",
            f"Bạn muốn ẩn sản phẩm #{product_id}? (giữ lại lịch sử bán hàng)",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            product_service.deactivate_product(product_id)
        except product_service.ProductError as exc:
            QMessageBox.warning(self, "Ẩn sản phẩm", str(exc))
            return
        self._reload_products()

    def _show_product_dialog(self, product_id: int | None) -> None:
        existing = product_service.get_product(product_id) if product_id else None

        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm sản phẩm" if existing is None else f"Sửa sản phẩm #{existing.id}")
        dlg.setMinimumWidth(560)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        name_edit = QLineEdit("" if existing is None else existing.name)
        category_combo = QComboBox()
        category_combo.addItem("Đồ ăn", "DO_AN")
        category_combo.addItem("Phụ kiện", "PHU_KIEN")
        if existing is not None:
            idx = category_combo.findData(existing.category)
            if idx >= 0:
                category_combo.setCurrentIndex(idx)
        sku_edit = QLineEdit("" if existing is None else (existing.sku or ""))
        price_edit = QLineEdit("" if existing is None else f"{int(existing.price)}")
        stock_spin = QSpinBox()
        stock_spin.setRange(0, 1_000_000)
        stock_spin.setValue(0 if existing is None else int(existing.stock))
        desc_edit = QLineEdit("" if existing is None else (existing.description or ""))

        form.addRow("Tên sản phẩm *", name_edit)
        form.addRow("Loại *", category_combo)
        form.addRow("SKU", sku_edit)
        form.addRow("Giá *", price_edit)
        form.addRow("Tồn kho", stock_spin)
        form.addRow("Mô tả", desc_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Thêm" if existing is None else "Lưu")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                if existing is None:
                    product_service.create_product(
                        name=name_edit.text(),
                        category=str(category_combo.currentData()),
                        price=price_edit.text(),
                        stock=int(stock_spin.value()),
                        sku=sku_edit.text(),
                        description=desc_edit.text(),
                        is_active=True,
                    )
                else:
                    product_service.update_product(
                        product_id=existing.id,
                        name=name_edit.text(),
                        category=str(category_combo.currentData()),
                        price=price_edit.text(),
                        stock=int(stock_spin.value()),
                        sku=sku_edit.text(),
                        description=desc_edit.text(),
                        is_active=True,
                    )
            except product_service.ProductError as exc:
                QMessageBox.warning(dlg, "Sản phẩm", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_products()

    def _refresh_appointments_employee_filter(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page or not hasattr(ap_page, "employeeFilterCombo"):
            return
        combo = ap_page.employeeFilterCombo
        prev = combo.currentData() if combo.count() else None
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Tất cả nhân viên", "ALL")
        combo.addItem("Chưa phân công", "NONE")
        for u in self._employees_list:
            combo.addItem(f"{u.full_name} ({u.username})", int(u.id))
        # Quyen: chi Admin moi duoc filter; Employee bat buoc xem cua minh
        is_admin = bool(getattr(self, "_is_admin", False))
        if not is_admin:
            current = Session.current()
            if current is not None:
                idx = combo.findData(int(current.id))
                if idx < 0:
                    combo.addItem(
                        f"{current.full_name} ({current.username})", int(current.id)
                    )
                    idx = combo.findData(int(current.id))
                combo.setCurrentIndex(idx)
            combo.setEnabled(False)
        else:
            combo.setEnabled(True)
            idx = combo.findData(prev) if prev is not None else 0
            combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

        try:
            combo.currentIndexChanged.disconnect()
        except TypeError:
            pass
        combo.currentIndexChanged.connect(lambda _: self._reload_appointments_table())

    # ===================== /PRODUCTS =====================

    def _render_services_table(self) -> None:
        services_page = self._pages.get("services")
        if not services_page:
            return
        table: QTableWidget = services_page.servicesTable
        rows = getattr(self, "_services_visible", None) or self._services_list
        table.setRowCount(len(rows))
        for r, s in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(s.name))
            table.setItem(r, 1, QTableWidgetItem(f"{int(s.price):,}đ".replace(",", ".")))
            table.setItem(r, 2, QTableWidgetItem(s.description or ""))
            table.setCellWidget(
                r,
                3,
                self._make_row_actions(
                    on_edit=lambda _, sid=s.id: self._on_edit_service_clicked(sid),
                    on_delete=lambda _, sid=s.id: self._on_delete_service_clicked(sid),
                    delete_text="Ẩn",
                ),
            )

        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

    def _render_pets_table(self) -> None:
        pets_page = self._pages.get("pets")
        if not pets_page or not hasattr(pets_page, "petsTable"):
            return

        table: QTableWidget = pets_page.petsTable
        owner_name = {c.id: c.full_name for c in self._customers}
        thumb = self._pets_thumb

        if not self._pets:
            table.clearSpans()
            table.setRowCount(1)
            table.setSpan(0, 0, 1, table.columnCount())
            empty = QTableWidgetItem("Chưa có thú cưng nào.")
            empty.setForeground(QColor("#64748B"))
            f = empty.font()
            f.setBold(True)
            empty.setFont(f)
            table.setItem(0, 0, empty)
            table.resizeRowsToContents()
            return

        table.clearSpans()
        table.setRowCount(len(self._pets))
        for r, p in enumerate(self._pets):
            wrap_img = QWidget()
            hi = QHBoxLayout(wrap_img)
            hi.setContentsMargins(4, 4, 4, 4)
            hi.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_btn = QPushButton()
            img_btn.setFixedSize(thumb + 6, thumb + 6)
            img_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            img_btn.clicked.connect(
                lambda _=False, pid=p.id: self._on_pet_image_upload_clicked(pid)
            )
            img_btn.setStyleSheet(
                "QPushButton{background:#E2E8F0; border:1px dashed #94A3B8; border-radius:10px; font-size:18px;}"
                "QPushButton:hover{background:#CBD5E1;}"
            )
            img_btn.setToolTip("Chọn ảnh (hoặc double-click ô ảnh trên bảng)")
            img_path = self._pet_images.get((p.customer_id, p.id))
            if img_path and os.path.exists(img_path):
                pix = QPixmap(img_path)
                if not pix.isNull():
                    img_btn.setIcon(QIcon(pix))
                    img_btn.setIconSize(QSize(thumb, thumb))
                    img_btn.setText("")
            else:
                img_btn.setText("📷")
            hi.addWidget(img_btn)
            table.setCellWidget(r, 0, wrap_img)

            name_item = QTableWidgetItem(p.name)
            name_item.setData(Qt.ItemDataRole.UserRole, p.id)
            table.setItem(r, 1, name_item)
            table.setItem(r, 2, QTableWidgetItem(p.species))
            table.setItem(r, 3, QTableWidgetItem(p.breed or "—"))
            age_txt = "—" if p.age is None else str(p.age)
            table.setItem(r, 4, QTableWidgetItem(age_txt))
            table.setItem(
                r,
                5,
                QTableWidgetItem(owner_name.get(p.customer_id, str(p.customer_id))),
            )
            table.setCellWidget(
                r,
                6,
                self._make_row_actions(
                    on_edit=lambda _, pid=p.id: self._on_edit_pet_clicked(pid),
                    on_delete=lambda _, pid=p.id: self._on_delete_pet_clicked(pid),
                ),
            )

        for r2 in range(table.rowCount()):
            table.resizeRowToContents(r2)
            h_need = self._pets_thumb + 22
            if table.rowHeight(r2) < h_need:
                table.setRowHeight(r2, h_need)

        table.horizontalHeader().setStretchLastSection(False)

    def _on_pet_image_upload_clicked(self, pet_id: int) -> None:
        pet = next((p for p in self._pets if p.id == pet_id), None)
        if pet is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh thú cưng",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if not path:
            return
        self._pet_images[(pet.customer_id, pet.id)] = path
        self._render_pets_table()

    def _refresh_pets_customer_filter(self) -> None:
        pets_page = self._pages.get("pets")
        if not pets_page:
            return
        combo = pets_page.customerFilterCombo
        current = combo.currentData() if combo.count() else "ALL"
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Tất cả khách hàng", "ALL")
        for c in self._customers:
            combo.addItem(c.full_name, c.id)
        idx = combo.findData(current) if current else -1
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    def _refresh_appointments_customer_combo(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        combo = ap_page.customerCombo
        current = combo.currentData() if combo.count() else ""
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Chọn khách hàng", "")
        for c in self._customers:
            combo.addItem(f"{c.full_name} ({c.phone})", c.id)
        idx = combo.findData(current) if current else -1
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)
        self._refresh_appointment_pet_list()

    def _on_pet_image_double_clicked(self, row: int, column: int) -> None:
        if row < 0 or column != 0:
            return
        pets_page = self._pages.get("pets")
        if not pets_page or not hasattr(pets_page, "petsTable"):
            return
        table: QTableWidget = pets_page.petsTable
        name_item = table.item(row, 1)
        pet_id = name_item.data(Qt.ItemDataRole.UserRole) if name_item else None
        if not isinstance(pet_id, int):
            return
        pet = next((p for p in self._pets if p.id == pet_id), None)
        if pet is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh thú cưng",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if not path:
            return
        self._pet_images[(pet.customer_id, pet.id)] = path
        self._render_pets_table()

    def _make_row_actions(
        self,
        *,
        on_edit,
        on_delete,
        delete_text: str = "Xóa",
        compact_wrap: bool = False,
    ) -> QWidget:
        if not getattr(self, "_is_admin", False):
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel("—")
            lbl.setStyleSheet("color:#94A3B8; font:700 9pt 'Segoe UI';")
            lay.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
            return w

        btn_edit = _build_action_icon_button(
            _action_icon("edit", "#3730A3"),
            "Sửa",
            "#EEF2FF",
            "#3730A3",
            hover="#E0E7FF",
        )
        btn_edit.clicked.connect(lambda: on_edit(None))

        del_kind = "hide" if delete_text.strip().lower() == "ẩn" else "trash"
        del_tip = "Ẩn" if del_kind == "hide" else "Xóa"
        btn_del = _build_action_icon_button(
            _action_icon(del_kind, "#B91C1C"),
            del_tip,
            "#FEE2E2",
            "#B91C1C",
            hover="#FCA5A5",
            hover_fg="#7F1D1D",
        )
        btn_del.clicked.connect(lambda: on_delete(None))

        return _wrap_action_buttons(
            [btn_edit, btn_del],
            trailing_stretch=not compact_wrap,
            margins=(0, 2, 0, 0) if compact_wrap else (8, 4, 8, 4),
        )

    def _on_add_customer_clicked(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm khách hàng")
        dlg.setMinimumWidth(520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        title = QLabel("Nhập thông tin khách hàng")
        title.setStyleSheet("font: 800 12pt 'Segoe UI'; color: #0F172A;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        name_edit = QLineEdit()
        phone_edit = QLineEdit()
        address_edit = QLineEdit()
        email_edit = QLineEdit()
        name_edit.setPlaceholderText("VD: Nguyễn Văn A")
        phone_edit.setPlaceholderText("VD: 0901234567")
        address_edit.setPlaceholderText("Địa chỉ (tuỳ chọn)")
        email_edit.setPlaceholderText("Email (tuỳ chọn)")
        form.addRow("Tên khách hàng *", name_edit)
        form.addRow("Số điện thoại *", phone_edit)
        form.addRow("Địa chỉ", address_edit)
        form.addRow("Email", email_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Thêm")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                customer_service.create_customer(
                    name_edit.text(),
                    phone_edit.text(),
                    address_edit.text(),
                    email_edit.text(),
                )
            except customer_service.CustomerError as exc:
                QMessageBox.warning(dlg, "Thêm khách hàng", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_customers(None)

    def _on_edit_customer_clicked(self, customer_id: int) -> None:
        c = next((x for x in self._customers if x.id == customer_id), None)
        if c is None:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Sửa khách hàng #{customer_id}")
        dlg.setMinimumWidth(520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        name_edit = QLineEdit(c.full_name)
        phone_edit = QLineEdit(c.phone)
        address_edit = QLineEdit(c.address or "")
        email_edit = QLineEdit(c.email or "")
        form.addRow("Tên khách hàng *", name_edit)
        form.addRow("Số điện thoại *", phone_edit)
        form.addRow("Địa chỉ", address_edit)
        form.addRow("Email", email_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Lưu")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                customer_service.update_customer(
                    customer_id,
                    name_edit.text(),
                    phone_edit.text(),
                    address_edit.text(),
                    email_edit.text(),
                )
            except customer_service.CustomerError as exc:
                QMessageBox.warning(dlg, "Sửa khách hàng", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_customers(None)

    def _on_delete_customer_clicked(self, customer_id: int) -> None:
        confirm = QMessageBox.question(
            self,
            "Xoá khách hàng",
            f"Bạn chắc chắn muốn xoá khách hàng #{customer_id}?\n"
            "Lưu ý: thú cưng sẽ bị xoá theo. Nếu đã có lịch hẹn thì sẽ không xoá được.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            customer_service.delete_customer(customer_id)
        except customer_service.CustomerError as exc:
            QMessageBox.warning(self, "Xoá khách hàng", str(exc))
            return
        self._reload_customers(None)

    def _on_add_service_clicked(self) -> None:
        self._show_service_dialog(None)

    def _on_edit_service_clicked(self, service_id: int) -> None:
        self._show_service_dialog(service_id)

    def _show_service_dialog(self, service_id: int | None) -> None:
        s = next((x for x in self._services_list if x.id == service_id), None) if service_id else None

        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm dịch vụ" if s is None else f"Sửa dịch vụ #{s.id}")
        dlg.setMinimumWidth(520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        name_edit = QLineEdit("" if s is None else s.name)
        price_edit = QLineEdit("" if s is None else f"{int(s.price)}")
        desc_edit = QLineEdit("" if s is None else (s.description or ""))
        form.addRow("Tên dịch vụ *", name_edit)
        form.addRow("Giá *", price_edit)
        form.addRow("Mô tả", desc_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Thêm" if s is None else "Lưu")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                if s is None:
                    service_service.create_service(name_edit.text(), price_edit.text(), desc_edit.text())
                else:
                    service_service.update_service(s.id, name_edit.text(), price_edit.text(), desc_edit.text())
            except service_service.ServiceError as exc:
                QMessageBox.warning(dlg, "Dịch vụ", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_services()

    def _on_delete_service_clicked(self, service_id: int) -> None:
        confirm = QMessageBox.question(
            self,
            "Ẩn dịch vụ",
            f"Bạn muốn ẩn dịch vụ #{service_id}? (không xoá hẳn dữ liệu)",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            service_service.deactivate_service(service_id)
        except service_service.ServiceError as exc:
            QMessageBox.warning(self, "Ẩn dịch vụ", str(exc))
            return
        self._reload_services()

    def _on_edit_pet_clicked(self, pet_id: int) -> None:
        pet = next((p for p in self._pets if p.id == pet_id), None)
        if pet is None:
            return
        self._show_pet_dialog(pet)

    def _on_delete_pet_clicked(self, pet_id: int) -> None:
        confirm = QMessageBox.question(self, "Xoá thú cưng", f"Bạn chắc chắn muốn xoá thú cưng #{pet_id}?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            pet_service.delete_pet(pet_id)
        except pet_service.PetError as exc:
            QMessageBox.warning(self, "Xoá thú cưng", str(exc))
            return
        self._reload_pets()

    def _on_add_pet_clicked(self) -> None:
        self._show_pet_dialog(None)

    def _show_pet_dialog(self, pet: Pet | None) -> None:
        if not self._customers:
            QMessageBox.warning(self, "Thú cưng", "Chưa có khách hàng. Hãy thêm khách hàng trước.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm thú cưng" if pet is None else f"Sửa thú cưng #{pet.id}")
        dlg.setMinimumWidth(520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        owner_combo = QComboBox()
        for c in self._customers:
            owner_combo.addItem(f"{c.full_name} (#{c.id})", c.id)
        if pet is not None:
            idx = owner_combo.findData(pet.customer_id)
            if idx >= 0:
                owner_combo.setCurrentIndex(idx)

        name_edit = QLineEdit("" if pet is None else pet.name)
        species_edit = QLineEdit("" if pet is None else pet.species)
        breed_edit = QLineEdit("" if pet is None else (pet.breed or ""))
        age_spin = QSpinBox()
        age_spin.setRange(0, 50)
        age_spin.setValue(0 if pet is None or pet.age is None else int(pet.age))

        form.addRow("Khách hàng *", owner_combo)
        form.addRow("Tên thú cưng *", name_edit)
        form.addRow("Loài *", species_edit)
        form.addRow("Giống", breed_edit)
        form.addRow("Tuổi", age_spin)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Thêm" if pet is None else "Lưu")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                if pet is None:
                    pet_service.create_pet(
                        int(owner_combo.currentData()),
                        name_edit.text(),
                        species_edit.text(),
                        breed_edit.text(),
                        int(age_spin.value()),
                    )
                else:
                    pet_service.update_pet(
                        pet.id,
                        int(owner_combo.currentData()),
                        name_edit.text(),
                        species_edit.text(),
                        breed_edit.text(),
                        int(age_spin.value()),
                    )
            except pet_service.PetError as exc:
                QMessageBox.warning(dlg, "Thú cưng", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_pets()

    def _on_view_customer_pets(self) -> None:
        customers_page = self._pages.get("customers")
        if not customers_page:
            return
        table = customers_page.customersTable
        row = table.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Thú cưng",
                "Vui lòng chọn một khách hàng trong danh sách.",
            )
            return
        id_item = table.item(row, 0)
        name_item = table.item(row, 1)
        if not id_item:
            return
        try:
            customer_id = int(id_item.text())
        except ValueError:
            return
        customer_name = name_item.text() if name_item else customer_id
        pets_row = [p for p in pet_service.list_pets(customer_id=customer_id)]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Thú cưng — {customer_name}")
        dlg.resize(440, 340)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))
        layout = QVBoxLayout(dlg)
        if not pets_row:
            layout.addWidget(QLabel("Khách hàng này chưa có thú cưng trong hệ thống."))
        else:
            lw = QListWidget()
            for p in pets_row:
                breed = p.breed or "—"
                age = "—" if p.age is None else str(p.age)
                lw.addItem(f"{p.name} — {p.species}, {breed}, {age} tuổi")
            layout.addWidget(lw)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)
        dlg.exec()

    def _on_demo_confirm_appointment(self) -> None:
        # Backward compat: demo handler removed, use DB handler.
        self._on_confirm_appointment_db()

    def _set_login_busy(self, busy: bool) -> None:
        login_btn = getattr(self._login, "LoginButton", None)
        if login_btn is not None:
            login_btn.setEnabled(not busy)
            login_btn.setText("Đang đăng nhập..." if busy else "Đăng nhập")
        reg_btn = getattr(self._login, "registerButton", None)
        if reg_btn is not None:
            reg_btn.setEnabled(not busy)

    def _on_login(self) -> None:
        if self._login_worker is not None and self._login_worker.isRunning():
            return
        username = (self._login.usernameEdit.text() or "").strip()
        password = self._login.passwordEdit.text() or ""
        self._set_login_busy(True)
        self._login_worker = _LoginWorker(username, password)
        self._login_worker.finished_with_result.connect(self._on_login_worker_finished)
        self._login_worker.finished.connect(self._on_login_worker_thread_done)
        self._login_worker.start()

    def _on_login_worker_thread_done(self) -> None:
        self._login_worker = None

    def _on_login_worker_finished(self, user, err) -> None:
        self._set_login_busy(False)
        if err is not None:
            if isinstance(err, auth_service.AuthError):
                QMessageBox.warning(self, "Đăng nhập thất bại", str(err))
            else:
                QMessageBox.critical(
                    self,
                    "Lỗi hệ thống",
                    f"Không thể kết nối MySQL:\n{err}\n\n"
                    "1. Bật MySQL (XAMPP/WAMP/service)\n"
                    "2. Tạo file .env từ .env.example (mật khẩu root)\n"
                    "3. Chạy: python scripts/init_db.py",
                )
            self._login.passwordEdit.clear()
            self._login.passwordEdit.setFocus()
            return

        self._root_stack.setCurrentWidget(self._main)
        self._refresh_user_indicator(user)
        self._apply_role_visibility(user)
        self._set_active("dashboard")
        QTimer.singleShot(0, self._post_login_load_catalog)

    def _post_login_load_catalog(self) -> None:
        """Tai du lieu sau khi UI chinh da hien - tranh treo man hinh login."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._reload_catalog_data()
            QApplication.processEvents()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Tải dữ liệu",
                f"Đăng nhập thành công nhưng không tải được dữ liệu:\n{exc}",
            )
        finally:
            QApplication.restoreOverrideCursor()

    def _on_logout(self) -> None:
        auth_service.logout()
        self._login.passwordEdit.clear()
        self._login.usernameEdit.setFocus()
        self._root_stack.setCurrentWidget(self._login)
        self._refresh_user_indicator(None)
        self._clear_catalog_ui()
        # an menu admin sau khi logout
        if hasattr(self, "_admin_menu") and self._admin_menu is not None:
            self._admin_menu.menuAction().setVisible(False)

    def _clear_catalog_ui(self) -> None:
        """Clear du lieu danh muc khi logout."""
        self._customers = []
        self._pets = []
        self._services_list = []
        self._services_visible = []
        self._products_list = []
        self._employees_list = []
        self._employees_stats: list = []
        self._pet_images.clear()
        self._product_images.clear()

        emp_page = self._pages.get("employees")
        if emp_page and hasattr(emp_page, "employeesTable"):
            emp_page.employeesTable.setRowCount(0)

        customers_page = self._pages.get("customers")
        if customers_page and hasattr(customers_page, "customersTable"):
            customers_page.customersTable.setRowCount(0)

        products_page = self._pages.get("products")
        if products_page and hasattr(products_page, "productsGridLayout"):
            _clear_grid_layout(products_page.productsGridLayout)

        pets_page = self._pages.get("pets")
        if pets_page:
            if hasattr(pets_page, "petsTable"):
                pets_page.petsTable.setRowCount(0)
            elif hasattr(pets_page, "petsGridLayout"):
                _clear_grid_layout(pets_page.petsGridLayout)
            if hasattr(pets_page, "customerFilterCombo"):
                pets_page.customerFilterCombo.blockSignals(True)
                pets_page.customerFilterCombo.clear()
                pets_page.customerFilterCombo.addItem("Tất cả khách hàng", "ALL")
                pets_page.customerFilterCombo.blockSignals(False)

        services_page = self._pages.get("services")
        if services_page and hasattr(services_page, "servicesTable"):
            services_page.servicesTable.setRowCount(0)

        ap_page = self._pages.get("appointments")
        if ap_page:
            if hasattr(ap_page, "customerCombo"):
                ap_page.customerCombo.blockSignals(True)
                ap_page.customerCombo.clear()
                ap_page.customerCombo.addItem("Chọn khách hàng", "")
                ap_page.customerCombo.blockSignals(False)
            if hasattr(ap_page, "petListWidget"):
                ap_page.petListWidget.clear()
            if hasattr(ap_page, "serviceCombo"):
                ap_page.serviceCombo.clear()
                ap_page.serviceCombo.addItem("Chọn dịch vụ", "")

        inv_page = self._pages.get("invoices")
        if inv_page:
            if hasattr(inv_page, "invoicesTable"):
                inv_page.invoicesTable.setRowCount(0)
            if hasattr(inv_page, "emptyLabel"):
                inv_page.emptyLabel.setText("Chưa có hóa đơn nào")

    def _refresh_user_indicator(self, user) -> None:
        if user is None:
            self.setWindowTitle("Pet Care Management")
            return
        self.setWindowTitle(
            f"Pet Care Management - {user.full_name} ({user.role_name})"
        )

    def _apply_role_visibility(self, user) -> None:
        is_admin = bool(getattr(user, "is_admin", False))
        if hasattr(self, "_admin_menu") and self._admin_menu is not None:
            self._admin_menu.menuAction().setVisible(is_admin)
        if hasattr(self, "_action_manage_users") and self._action_manage_users is not None:
            self._action_manage_users.setVisible(is_admin)

        # Catalog CRUD: chi Admin moi duoc them/sua/xoa
        customers_page = self._pages.get("customers")
        if customers_page and hasattr(customers_page, "addCustomerButton"):
            customers_page.addCustomerButton.setVisible(is_admin)

        pets_page = self._pages.get("pets")
        if pets_page and hasattr(pets_page, "addPetButton"):
            pets_page.addPetButton.setVisible(is_admin)

        services_page = self._pages.get("services")
        if services_page and hasattr(services_page, "addServiceButton"):
            services_page.addServiceButton.setVisible(is_admin)

        products_page = self._pages.get("products")
        if products_page and hasattr(products_page, "addProductButton"):
            products_page.addProductButton.setVisible(is_admin)

        # Trang nhan vien chi danh cho Admin
        if hasattr(self._main, "navEmployees"):
            self._main.navEmployees.setVisible(is_admin)
        emp_page = self._pages.get("employees")
        if emp_page and hasattr(emp_page, "addEmployeeButton"):
            emp_page.addEmployeeButton.setVisible(is_admin)

        # Luu flag de render action column
        self._is_admin = is_admin

        # Cap nhat lai filter NV (Employee chi xem cua minh)
        try:
            self._refresh_appointments_employee_filter()
        except Exception:
            pass

        # Tai du lieu thong ke nhan vien (chi can cho admin)
        if is_admin:
            try:
                self._reload_employees_stats()
            except Exception:
                pass

    def _show_user_admin_dialog(self) -> None:
        if not Session.is_admin():
            QMessageBox.warning(self, "Quản lý người dùng", "Chỉ Admin mới được sử dụng chức năng này.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Quản lý người dùng")
        dlg.resize(860, 520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        root = QVBoxLayout(dlg)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Danh sách người dùng")
        title.setStyleSheet("font: 900 12pt 'Segoe UI'; color: #0F172A;")
        header.addWidget(title)
        header.addStretch(1)

        btn_add = QPushButton("＋  Thêm user")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setObjectName("PrimaryButton")
        btn_add.clicked.connect(lambda: self._admin_add_user(dlg))
        header.addWidget(btn_add)

        root.addLayout(header)

        # Search + role filter
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Tìm theo họ tên / username / SĐT...")
        role_combo = QComboBox()
        role_combo.addItem("Tất cả role", "")
        role_combo.addItem("ADMIN", "ADMIN")
        role_combo.addItem("EMPLOYEE", "EMPLOYEE")
        role_combo.setMinimumWidth(160)
        filter_row.addWidget(search_edit, 1)
        filter_row.addWidget(role_combo, 0)
        root.addLayout(filter_row)

        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(
            ["ID", "Username", "Họ tên", "Role", "SĐT", "Trạng thái", "Thao tác"]
        )
        self._setup_table(table)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root.addWidget(table, 1)

        def refresh() -> None:
            q = (search_edit.text() or "").strip() or None
            role_data = role_combo.currentData()
            role = str(role_data) if role_data else None
            rows = user_service.list_users(active_only=False, query=q, role_name=role)
            table.setRowCount(len(rows))
            for r, u in enumerate(rows):
                table.setItem(r, 0, QTableWidgetItem(str(u["id"])))
                table.setItem(r, 1, QTableWidgetItem(u["username"]))
                table.setItem(r, 2, QTableWidgetItem(u["full_name"]))
                table.setItem(r, 3, QTableWidgetItem(u["role_name"]))
                table.setItem(r, 4, QTableWidgetItem(u.get("phone") or ""))
                table.setItem(r, 5, QTableWidgetItem("Đang hoạt động" if u["is_active"] else "Bị khoá"))

                uid = int(u["id"])
                is_active = bool(u["is_active"])
                table.setCellWidget(
                    r,
                    6,
                    self._make_admin_actions(
                        uid=uid,
                        is_active=is_active,
                        on_refresh=refresh,
                        parent=dlg,
                    ),
                )

            hdr = table.horizontalHeader()
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        refresh()
        search_edit.textChanged.connect(lambda _: refresh())
        role_combo.currentIndexChanged.connect(lambda _: refresh())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        root.addWidget(buttons)
        dlg.exec()

    def _make_admin_actions(self, *, uid: int, is_active: bool, on_refresh, parent: QWidget) -> QWidget:
        btn_edit = _build_action_icon_button(
            _action_icon("edit", "#3730A3"),
            "Sửa",
            "#EEF2FF",
            "#3730A3",
            hover="#E0E7FF",
        )
        btn_role = _build_action_button("Role", "#E0F2FE", "#075985", hover="#BAE6FD")
        btn_pw = _build_action_button("Reset PW", "#FEF9C3", "#854D0E", hover="#FEF08A")
        btn_lock = _build_action_button(
            "Mở" if not is_active else "Khoá",
            "#FEE2E2",
            "#B91C1C",
            hover="#FCA5A5",
            hover_fg="#7F1D1D",
        )

        btn_edit.clicked.connect(lambda: self._admin_edit_user(parent, uid, on_refresh))
        btn_role.clicked.connect(lambda: self._admin_change_role(parent, uid, on_refresh))
        btn_pw.clicked.connect(lambda: self._admin_reset_password(parent, uid, on_refresh))
        btn_lock.clicked.connect(lambda: self._admin_toggle_active(parent, uid, is_active, on_refresh))

        return _wrap_action_buttons([btn_edit, btn_role, btn_pw, btn_lock])

    def _admin_add_user(self, parent: QWidget) -> None:
        dlg = QDialog(parent)
        dlg.setWindowTitle("Thêm user")
        dlg.setMinimumWidth(520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        role_combo = QComboBox()
        role_combo.addItem("ADMIN", "ADMIN")
        role_combo.addItem("EMPLOYEE", "EMPLOYEE")
        username = QLineEdit()
        full_name = QLineEdit()
        phone = QLineEdit()
        pw = QLineEdit()
        pw.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Role *", role_combo)
        form.addRow("Username *", username)
        form.addRow("Họ tên *", full_name)
        form.addRow("SĐT", phone)
        form.addRow("Mật khẩu *", pw)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Thêm")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                user_service.admin_create_user(
                    role_name=str(role_combo.currentData()),
                    username=username.text(),
                    password=pw.text(),
                    full_name=full_name.text(),
                    phone=phone.text(),
                )
            except user_service.UserError as exc:
                QMessageBox.warning(dlg, "Thêm user", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)
        dlg.exec()

    def _admin_edit_user(self, parent: QWidget, uid: int, on_refresh) -> None:
        users = user_service.list_users(active_only=False)
        u = next((x for x in users if int(x["id"]) == uid), None)
        if u is None:
            return

        dlg = QDialog(parent)
        dlg.setWindowTitle(f"Sửa user #{uid}")
        dlg.setMinimumWidth(520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        full_name = QLineEdit(u["full_name"])
        phone = QLineEdit(u.get("phone") or "")
        form.addRow("Họ tên *", full_name)
        form.addRow("SĐT", phone)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Lưu")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                user_service.admin_update_user(uid, full_name.text(), phone.text())
            except user_service.UserError as exc:
                QMessageBox.warning(dlg, "Sửa user", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            on_refresh()

    def _admin_change_role(self, parent: QWidget, uid: int, on_refresh) -> None:
        dlg = QDialog(parent)
        dlg.setWindowTitle(f"Đổi role user #{uid}")
        dlg.setMinimumWidth(420)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        role_combo = QComboBox()
        role_combo.addItem("ADMIN", "ADMIN")
        role_combo.addItem("EMPLOYEE", "EMPLOYEE")
        form.addRow("Role", role_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Lưu")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                user_service.admin_set_role(uid, str(role_combo.currentData()))
            except user_service.UserError as exc:
                QMessageBox.warning(dlg, "Đổi role", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            on_refresh()

    def _admin_reset_password(self, parent: QWidget, uid: int, on_refresh) -> None:
        dlg = QDialog(parent)
        dlg.setWindowTitle(f"Reset mật khẩu user #{uid}")
        dlg.setMinimumWidth(420)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        pw = QLineEdit()
        pw.setEchoMode(QLineEdit.EchoMode.Password)
        confirm = QLineEdit()
        confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Mật khẩu mới *", pw)
        form.addRow("Xác nhận *", confirm)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Reset")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            if pw.text() != confirm.text():
                QMessageBox.warning(dlg, "Reset mật khẩu", "Mật khẩu xác nhận không khớp.")
                return
            try:
                user_service.admin_reset_password(uid, pw.text())
            except user_service.UserError as exc:
                QMessageBox.warning(dlg, "Reset mật khẩu", str(exc))
                return
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            on_refresh()

    def _admin_toggle_active(self, parent: QWidget, uid: int, is_active: bool, on_refresh) -> None:
        action = "Khoá" if is_active else "Mở khoá"
        confirm = QMessageBox.question(parent, action, f"Bạn muốn {action.lower()} user #{uid}?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            user_service.admin_set_active(uid, is_active=not is_active)
        except user_service.UserError as exc:
            QMessageBox.warning(parent, action, str(exc))
            return
        on_refresh()

    def _show_change_password_dialog(self) -> None:
        user = Session.current()
        if user is None:
            QMessageBox.warning(self, "Đổi mật khẩu", "Bạn cần đăng nhập trước.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Đổi mật khẩu")
        dlg.setMinimumWidth(420)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        title = QLabel(f"Tài khoản: {user.username} ({user.full_name})")
        title.setStyleSheet("font: 700 10pt 'Segoe UI'; color: #0F172A;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        old_edit = QLineEdit()
        old_edit.setEchoMode(QLineEdit.EchoMode.Password)
        new_edit = QLineEdit()
        new_edit.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_edit = QLineEdit()
        confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Mật khẩu hiện tại *", old_edit)
        form.addRow("Mật khẩu mới *", new_edit)
        form.addRow("Xác nhận mật khẩu *", confirm_edit)
        layout.addLayout(form)

        hint = QLabel("Mật khẩu mới phải có ít nhất 6 ký tự và khác mật khẩu hiện tại.")
        hint.setStyleSheet("color: #64748B; font: 600 9pt 'Segoe UI';")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("Đổi mật khẩu")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            try:
                auth_service.change_password(
                    user.id,
                    old_edit.text(),
                    new_edit.text(),
                    confirm_edit.text(),
                )
            except auth_service.AuthError as exc:
                QMessageBox.warning(dlg, "Đổi mật khẩu", str(exc))
                return
            except Exception as exc:
                QMessageBox.critical(dlg, "Lỗi hệ thống", str(exc))
                return
            QMessageBox.information(dlg, "Đổi mật khẩu", "Đổi mật khẩu thành công.")
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)
        dlg.exec()

    def _show_register_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Đăng ký tài khoản nhân viên")
        dlg.setMinimumWidth(520)
        self._install_pet_background(dlg, overlay_color=(11, 30, 63, 155))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        title = QLabel("Tạo tài khoản (vai trò: Nhân viên)")
        title.setStyleSheet("font: 800 12pt 'Segoe UI'; color: rgba(255,255,255,0.92);")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        username = QLineEdit()
        full_name = QLineEdit()
        phone = QLineEdit()
        password = QLineEdit()
        confirm = QLineEdit()
        password.setEchoMode(QLineEdit.EchoMode.Password)
        confirm.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Username *", username)
        form.addRow("Họ tên *", full_name)
        form.addRow("SĐT", phone)
        form.addRow("Mật khẩu *", password)
        form.addRow("Xác nhận *", confirm)
        layout.addLayout(form)

        hint = QLabel("Username: chữ/số và . _ - (3–50 ký tự). Mật khẩu ≥ 6 ký tự.")
        hint.setStyleSheet("color: rgba(219,234,254,0.75); font: 600 9pt 'Segoe UI';")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("Tạo tài khoản")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Huỷ")
        buttons.rejected.connect(dlg.reject)

        def _on_ok() -> None:
            if password.text() != confirm.text():
                QMessageBox.warning(dlg, "Đăng ký", "Mật khẩu xác nhận không khớp.")
                return
            try:
                user_id = user_service.register_employee(
                    username=username.text(),
                    password=password.text(),
                    full_name=full_name.text(),
                    phone=phone.text(),
                )
            except user_service.UserError as exc:
                QMessageBox.warning(dlg, "Đăng ký", str(exc))
                return
            QMessageBox.information(
                dlg,
                "Đăng ký",
                f"Tạo tài khoản thành công (ID: {user_id}).\nBạn có thể đăng nhập ngay.",
            )
            # prefill login form
            self._login.usernameEdit.setText(username.text().strip())
            self._login.passwordEdit.clear()
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        layout.addWidget(buttons)
        dlg.exec()

    def _set_active(self, key: str) -> None:
        self._set_sidebar_active(key)
        self._set_stack_page(key)

    def _set_sidebar_active(self, key: str) -> None:
        mapping = {
            "dashboard": self._main.navDashboard,
            "customers": self._main.navCustomers,
            "pets": self._main.navPets,
            "services": self._main.navServices,
            "appointments": self._main.navAppointments,
            "invoices": self._main.navInvoices,
        }
        if hasattr(self._main, "navProducts"):
            mapping["products"] = self._main.navProducts
        if hasattr(self._main, "navEmployees"):
            mapping["employees"] = self._main.navEmployees
        for k, btn in mapping.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _set_stack_page(self, key: str) -> None:
        stack = self._main.stack
        for i in range(stack.count()):
            w = stack.widget(i)
            if w.property("page_key") == key:
                stack.setCurrentIndex(i)
                if key == "dashboard" and isinstance(w, DashboardView):
                    # Chi reload dashboard sau khi user da dang nhap, tranh
                    # query DB trong giai doan __init__ (truoc khi co session).
                    if Session.current() is not None:
                        try:
                            w.reload()
                        except Exception:
                            pass
                return

