from __future__ import annotations

import os
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt, QDateTime, QEvent, QSize
from PyQt6.QtGui import QFontMetrics, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
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
    QPlainTextEdit,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .theme import background_image_path, qss
from .pages.dashboard import DashboardView
from src.petcare_backend.services import auth_service
from src.petcare_backend.services import customer_service, pet_service, service_service
from src.petcare_backend.services import user_service
from src.petcare_backend.services import appointment_service
from src.petcare_backend.services import invoice_service, payment_service
from src.petcare_backend.models import Customer, Pet, Service
from src.petcare_backend.session import Session


APPOINTMENT_STATUSES = ("Chờ xử lý", "Đang thực hiện", "Hoàn thành", "Hủy")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ui_path(name: str) -> str:
    return str(_repo_root() / "ui" / name)


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


def _wrap_action_buttons(buttons: list[QPushButton]) -> QWidget:
    """Goi list nut action vao 1 QWidget can chinh san sang gan vao QTableWidget.

    Tinh san minimumSize de QHeaderView::ResizeToContents lam viec dung.
    """
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(8, 4, 8, 4)
    lay.setSpacing(8)
    total_w = 16
    max_h = 0
    for b in buttons:
        lay.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        total_w += b.minimumWidth() + 8
        max_h = max(max_h, b.minimumHeight())
    lay.addStretch(1)
    w.setMinimumSize(total_w, max_h + 8)
    return w


class PetBackground(QLabel):
    """Ảnh nền thú cưng tự động scale theo kích thước parent (cover + overlay)."""

    def __init__(
        self,
        parent: QWidget,
        image_path: str,
        overlay_color: tuple[int, int, int, int] = (239, 246, 255, 170),
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
        self._customers: list[Customer] = []
        self._pets: list[Pet] = []
        self._pets_thumb: int = 72
        self._services_list: list[Service] = []
        self._per_pet_service_container: QWidget | None = None
        self._per_pet_service_rows_layout: QVBoxLayout | None = None
        self._per_pet_service_combos: dict[str, QComboBox] = {}

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
        self._set_active("dashboard")
        # Chi khoi tao UI pages; du lieu se load tu MySQL sau khi dang nhap thanh cong.
        self._init_catalog_pages()

    def _install_pet_background(
        self,
        widget: QWidget,
        overlay_color: tuple[int, int, int, int] = (239, 246, 255, 140),
    ) -> PetBackground | None:
        if not self._bg_path or not Path(self._bg_path).exists():
            return None
        return PetBackground(widget, self._bg_path, overlay_color=overlay_color)

    def _install_backgrounds(self) -> None:
        login_root = self._login.findChild(QWidget, "LoginPage") or self._login
        self._install_pet_background(login_root, overlay_color=(11, 30, 63, 155))

        app_root = self._main.centralWidget()
        if app_root is not None:
            app_root.setObjectName("AppRoot")
            app_root.style().unpolish(app_root)
            app_root.style().polish(app_root)
            self._install_pet_background(app_root, overlay_color=(239, 246, 255, 60))

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
            "QPushButton:hover{background:rgba(255,255,255,0.16);border:1px solid rgba(191,219,254,0.65);}"
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
        self._main.navAppointments.clicked.connect(lambda: self._set_active("appointments"))
        self._main.navInvoices.clicked.connect(lambda: self._set_active("invoices"))
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
        add("appointments", "appointments.ui")
        ap_lay = self._pages["appointments"].layout()
        if isinstance(ap_lay, QVBoxLayout) and ap_lay.count() >= 2:
            ap_lay.setStretch(1, 1)

        add("invoices", "invoices.ui")

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

        pets_page = self._pages.get("pets")
        if pets_page:
            table: QTableWidget = pets_page.petsTable
            self._setup_table(table)
            table.setIconSize(QSize(self._pets_thumb, self._pets_thumb))
            pets_page.customerFilterCombo.currentIndexChanged.connect(lambda _: self._reload_pets())
            pets_page.addPetButton.clicked.connect(self._on_add_pet_clicked)
            table.cellDoubleClicked.connect(self._on_pet_image_double_clicked)

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
            # Bang chi hien thong tin, khong edit truc tiep (doi trang thai trong dialog chi tiet)
            # Bo panel chi tiet ben duoi -> khong can itemSelectionChanged nua
            # Mo chi tiet bang click 1 lan (an toan hon double click)
            table.cellClicked.connect(lambda r, c: self._on_appointment_row_clicked(r, c))

            # an luon panel chi tiet ben duoi danh sach
            if hasattr(ap_page, "detailTitle"):
                ap_page.detailTitle.setVisible(False)
            if hasattr(ap_page, "appointmentDetailEdit"):
                ap_page.appointmentDetailEdit.setVisible(False)

        inv_page = self._pages.get("invoices")
        if inv_page:
            if hasattr(inv_page, "createInvoiceButton"):
                inv_page.createInvoiceButton.clicked.connect(self._show_invoice_center)
            self._install_invoices_table(inv_page)

    def _reload_catalog_data(self) -> None:
        """Load khach hang/thu cung/dich vu tu MySQL va render UI."""
        self._reload_customers(None)
        self._reload_services()
        self._reload_pets()
        self._refresh_pets_customer_filter()
        self._refresh_appointments_customer_combo()
        self._reload_appointments_table()
        self._reload_invoices_table()

        dash = self._pages.get("dashboard")
        if isinstance(dash, DashboardView):
            try:
                dash.reload()
            except Exception:
                pass

    def _install_invoices_table(self, inv_page: QWidget) -> None:
        """Invoices UI chi co emptyLabel -> chen runtime table."""
        if hasattr(inv_page, "invoicesTable"):
            return
        layout = inv_page.layout()
        if layout is None:
            return
        table = QTableWidget()
        table.setObjectName("invoicesTable")
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(
            ["Mã HĐ", "Ngày", "Khách hàng", "Thú cưng", "Tổng tiền", "Trạng thái", "Thao tác"]
        )
        self._setup_table(table)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table, 1)
        inv_page.invoicesTable = table  # type: ignore[attr-defined]

        if hasattr(inv_page, "emptyLabel"):
            inv_page.emptyLabel.setVisible(False)

    def _reload_invoices_table(self) -> None:
        inv_page = self._pages.get("invoices")
        if not inv_page or not hasattr(inv_page, "invoicesTable"):
            return
        rows = invoice_service.list_recent(limit=150)
        self._invoice_rows = rows  # type: ignore[attr-defined]

        table: QTableWidget = inv_page.invoicesTable
        table.setRowCount(len(rows))
        for r, i in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(str(i.get("invoice_no", ""))))
            issued = i.get("issued_at")
            issued_txt = issued.strftime("%d/%m/%Y %H:%M") if issued else ""
            table.setItem(r, 1, QTableWidgetItem(issued_txt))
            table.setItem(r, 2, QTableWidgetItem(str(i.get("customer_name", ""))))
            table.setItem(r, 3, QTableWidgetItem(str(i.get("pet_name", ""))))
            total = float(i.get("total_amount") or 0)
            table.setItem(r, 4, QTableWidgetItem(f"{int(total):,}đ".replace(",", ".")))
            status = str(i.get("payment_status", "CHUA_TT"))
            status_label = "Đã TT" if status == "DA_TT" else ("Chưa TT" if status == "CHUA_TT" else status)
            table.setItem(r, 5, QTableWidgetItem(status_label))

            invoice_id = int(i["invoice_id"])
            table.setCellWidget(
                r,
                6,
                self._make_invoice_actions(invoice_id=invoice_id),
            )

        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(6, 260)

    def _make_invoice_actions(self, *, invoice_id: int) -> QWidget:
        btn_view = _build_action_button("Xem", "#EEF2FF", "#3730A3", hover="#E0E7FF")
        btn_view.clicked.connect(lambda: self._show_invoice_detail(invoice_id))

        btn_pay = _build_action_button("Thanh toán", "#DCFCE7", "#166534", hover="#BBF7D0")
        btn_pay.clicked.connect(lambda: self._show_payment_dialog(invoice_id))

        return _wrap_action_buttons([btn_view, btn_pay])

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

        info = QLabel("Chọn lịch hẹn đã Hoàn thành để tạo hoá đơn.")
        info.setStyleSheet("color:#334155; font:700 9pt 'Segoe UI';")
        root.addWidget(info)

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["ID", "Thời gian", "Khách hàng", "Thú cưng", "Dịch vụ", "Trạng thái"])
        self._setup_table(table)
        root.addWidget(table, 1)

        # load candidates
        rows = appointment_service.list_recent(limit=200)
        candidates = []
        for a in rows:
            if a.get("status") == "HOAN_THANH":
                candidates.append(a)
        table.setRowCount(len(candidates))
        for r, a in enumerate(candidates):
            appt_id = int(a["appointment_id"])
            table.setItem(r, 0, QTableWidgetItem(str(appt_id)))
            when_txt = a["scheduled_at"].strftime("%d/%m/%Y %H:%M") if a.get("scheduled_at") else ""
            table.setItem(r, 1, QTableWidgetItem(when_txt))
            table.setItem(r, 2, QTableWidgetItem(str(a.get("customer_name", ""))))
            table.setItem(r, 3, QTableWidgetItem(str(a.get("pet_name", ""))))
            table.setItem(r, 4, QTableWidgetItem(str(a.get("service_name", ""))))
            table.setItem(r, 5, QTableWidgetItem(str(a.get("status_label", ""))))
            # store id
            table.item(r, 0).setData(Qt.ItemDataRole.UserRole, appt_id)

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
            QMessageBox.information(dlg, "Tạo hoá đơn", f"Đã tạo hoá đơn (ID: {inv_id}).")
            dlg.accept()

        buttons.accepted.connect(_on_ok)
        root.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_invoices_table()

    def _show_invoice_detail(self, invoice_id: int) -> None:
        from src.petcare_backend.dao import invoice_item_dao
        from src.petcare_backend.invoice_export import export_invoice_pdf, ExportError

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Chi tiết hoá đơn #{invoice_id}")
        dlg.resize(760, 520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        root = QVBoxLayout(dlg)
        root.setSpacing(10)

        items = invoice_item_dao.list_by_invoice(invoice_id)
        top_bar = QHBoxLayout()
        top_bar.addStretch(1)
        btn_export = QPushButton("Xuất PDF")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet(
            "QPushButton{background:#2563EB;color:white;border:none;padding:6px 14px;border-radius:8px;font:800 9pt 'Segoe UI';}"
            "QPushButton:hover{background:#1D4ED8;}"
        )
        top_bar.addWidget(btn_export)
        root.addLayout(top_bar)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Thú cưng", "Dịch vụ", "SL", "Đơn giá", "Thành tiền"])
        self._setup_table(table)
        table.setRowCount(len(items))
        for r, it in enumerate(items):
            table.setItem(r, 0, QTableWidgetItem(str(it.get("pet_name") or "—")))
            table.setItem(r, 1, QTableWidgetItem(str(it.get("service_name", ""))))
            table.setItem(r, 2, QTableWidgetItem(str(it.get("quantity", ""))))
            table.setItem(r, 3, QTableWidgetItem(f"{int(float(it.get('unit_price') or 0)):,}đ".replace(",", ".")))
            table.setItem(r, 4, QTableWidgetItem(f"{int(float(it.get('line_total') or 0)):,}đ".replace(",", ".")))
        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(table, 1)

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

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        root.addWidget(buttons)
        dlg.exec()

    def _show_payment_dialog(self, invoice_id: int) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Thanh toán hoá đơn #{invoice_id}")
        dlg.setMinimumWidth(520)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        root = QVBoxLayout(dlg)
        form = QFormLayout()
        amount = QLineEdit()
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
        self._appointments_rows = appointment_service.list_recent(limit=150)  # type: ignore[attr-defined]
        self._render_appointments_table_db()

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
            status_item = QTableWidgetItem(str(a.get("status_label") or ""))
            status_item.setData(Qt.ItemDataRole.UserRole, appt_id)
            table.setItem(r, 4, status_item)

            res_item = QTableWidgetItem(str(a.get("note") or ""))
            res_item.setData(Qt.ItemDataRole.UserRole, appt_id)
            table.setItem(r, 5, res_item)

        table.blockSignals(False)

        hdr = table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        # ensure table is read-only
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

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
        lines = [
            f"Thời gian: {a['scheduled_at'].strftime('%d/%m/%Y %H:%M') if a.get('scheduled_at') else ''}",
            f"Khách hàng: {a.get('customer_name','')}",
            f"SĐT: {a.get('customer_phone','—')}",
            f"Địa chỉ: {a.get('customer_address','—')}",
            f"Thú cưng: {a.get('pet_name','')}",
            f"Dịch vụ: {a.get('service_name','')}",
            f"Trạng thái: {a.get('status_label','')}",
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

    def _show_appointment_detail_dialog(self, row: int) -> None:
        from src.petcare_backend.dao import appointment_service_dao

        rows = getattr(self, "_appointments_rows", [])
        if row < 0 or row >= len(rows):
            return
        a = rows[row]
        appt_id = int(a.get("appointment_id") or 0)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Chi tiết lịch hẹn #{a.get('appointment_id', '')}")
        dlg.resize(680, 600)
        self._install_pet_background(dlg, overlay_color=(239, 246, 255, 170))

        root = QVBoxLayout(dlg)
        root.setSpacing(10)

        header = QLabel("Thông tin lịch hẹn")
        header.setStyleSheet("font: 900 11pt 'Segoe UI'; color:#0F172A;")
        root.addWidget(header)

        status_row = QHBoxLayout()
        status_lbl = QLabel("Trạng thái")
        status_lbl.setStyleSheet("color: rgba(15,23,42,0.65); font: 700 9pt 'Segoe UI';")
        status_row.addWidget(status_lbl)
        status_combo = QComboBox()
        status_combo.addItems(APPOINTMENT_STATUSES)
        current_status = str(a.get("status_label") or "Chờ xử lý")
        idx = status_combo.findText(current_status)
        if idx >= 0:
            status_combo.setCurrentIndex(idx)
        status_row.addWidget(status_combo, 1)
        root.addLayout(status_row)

        info_lines = [
            f"Mã lịch hẹn: {a.get('appointment_id','')}",
            f"Thời gian: {self._fmt_dt_safe(a.get('scheduled_at'))}",
            f"Khách hàng: {a.get('customer_name','')}",
            f"SĐT: {a.get('customer_phone','—')}",
            f"Địa chỉ: {a.get('customer_address','—')}",
        ]
        info_text = QPlainTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText("\n".join(info_lines))
        info_text.setMaximumHeight(120)
        root.addWidget(info_text)

        svc_lbl = QLabel("Thú cưng & dịch vụ")
        svc_lbl.setStyleSheet("font: 800 10pt 'Segoe UI'; color:#0F172A;")
        root.addWidget(svc_lbl)

        svc_table = QTableWidget()
        svc_table.setColumnCount(4)
        svc_table.setHorizontalHeaderLabels(["Thú cưng", "Dịch vụ", "SL", "Đơn giá"])
        self._setup_table(svc_table)
        try:
            svc_items = appointment_service_dao.list_by_appointment(appt_id)
        except Exception:
            svc_items = []
        svc_table.setRowCount(len(svc_items))
        for r, it in enumerate(svc_items):
            svc_table.setItem(r, 0, QTableWidgetItem(str(it.get("pet_name") or "—")))
            svc_table.setItem(r, 1, QTableWidgetItem(str(it.get("service_name") or "")))
            svc_table.setItem(r, 2, QTableWidgetItem(str(it.get("quantity") or 1)))
            try:
                price_txt = f"{int(float(it.get('unit_price') or 0)):,}đ".replace(",", ".")
            except Exception:
                price_txt = str(it.get("unit_price") or "")
            svc_table.setItem(r, 3, QTableWidgetItem(price_txt))
        hdr = svc_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        svc_table.setMinimumHeight(160)
        root.addWidget(svc_table, 1)

        result_lbl = QLabel("Kết quả dịch vụ")
        result_lbl.setStyleSheet("font: 800 10pt 'Segoe UI'; color:#0F172A;")
        root.addWidget(result_lbl)

        result_edit = QPlainTextEdit()
        result_edit.setPlaceholderText("Nhập kết quả dịch vụ...")
        result_edit.setPlainText(str(a.get("note") or ""))
        result_edit.setMaximumHeight(120)
        root.addWidget(result_edit)

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
            try:
                appointment_service.update_status(appt_id, status_combo.currentText())
                appointment_service.update_result_note(appt_id, result_edit.toPlainText())
            except Exception as exc:
                QMessageBox.warning(dlg, "Lưu", str(exc))
                return
            self._reload_appointments_table()
            dlg.accept()

        buttons.accepted.connect(_on_save)
        buttons.rejected.connect(dlg.reject)
        root.addWidget(buttons)
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
                btn_del = QPushButton("Xoá")
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setStyleSheet(
                    "QPushButton{background:#FEE2E2;color:#B91C1C;border:none;padding:3px 10px;border-radius:6px;font:700 8pt 'Segoe UI';}"
                    "QPushButton:hover{background:#FCA5A5;color:#7F1D1D;}"
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
        q = (query or "").strip()
        self._customers = list(customer_service.list_customers(q or None))
        self._render_customers_table()
        self._refresh_pets_customer_filter()
        self._refresh_appointments_customer_combo()

    def _reload_services(self) -> None:
        self._services_list = list(service_service.list_services(active_only=True))
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

    def _render_services_table(self) -> None:
        services_page = self._pages.get("services")
        if not services_page:
            return
        table: QTableWidget = services_page.servicesTable
        table.setRowCount(len(self._services_list))
        for r, s in enumerate(self._services_list):
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
        if not pets_page:
            return
        table: QTableWidget = pets_page.petsTable
        thumb = self._pets_thumb
        owner_name = {c.id: c.full_name for c in self._customers}
        table.setRowCount(len(self._pets))
        for r, p in enumerate(self._pets):
            table.setRowHeight(r, thumb + 14)

            img_item = QTableWidgetItem("📷")
            img_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            img_path = self._pet_images.get((p.customer_id, p.id))
            if img_path and os.path.exists(img_path):
                pix = QPixmap(img_path)
                if not pix.isNull():
                    icon = QIcon(
                        pix.scaled(
                            thumb,
                            thumb,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                    img_item.setIcon(icon)
                    img_item.setText("")
            table.setItem(r, 0, img_item)

            name_item = QTableWidgetItem(p.name)
            name_item.setData(Qt.ItemDataRole.UserRole, p.id)
            table.setItem(r, 1, name_item)
            table.setItem(r, 2, QTableWidgetItem(p.species))
            table.setItem(r, 3, QTableWidgetItem(p.breed or ""))
            table.setItem(r, 4, QTableWidgetItem("" if p.age is None else str(p.age)))
            table.setItem(r, 5, QTableWidgetItem(owner_name.get(p.customer_id, str(p.customer_id))))
            table.setCellWidget(
                r,
                6,
                self._make_row_actions(
                    on_edit=lambda _, pid=p.id: self._on_edit_pet_clicked(pid),
                    on_delete=lambda _, pid=p.id: self._on_delete_pet_clicked(pid),
                ),
            )

        table.setColumnWidth(0, thumb + 18)

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
        if not pets_page:
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
    ) -> QWidget:
        if not getattr(self, "_is_admin", False):
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel("—")
            lbl.setStyleSheet("color:#94A3B8; font:700 9pt 'Segoe UI';")
            lay.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
            return w

        btn_edit = _build_action_button("Sửa", "#EEF2FF", "#3730A3", hover="#E0E7FF")
        btn_edit.clicked.connect(lambda: on_edit(None))

        btn_del = _build_action_button(
            delete_text, "#FEE2E2", "#B91C1C", hover="#FCA5A5", hover_fg="#7F1D1D"
        )
        btn_del.clicked.connect(lambda: on_delete(None))

        return _wrap_action_buttons([btn_edit, btn_del])

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

    def _on_login(self) -> None:
        username = (self._login.usernameEdit.text() or "").strip()
        password = self._login.passwordEdit.text() or ""
        try:
            user = auth_service.login(username, password)
        except auth_service.AuthError as exc:
            QMessageBox.warning(self, "Đăng nhập thất bại", str(exc))
            self._login.passwordEdit.clear()
            self._login.passwordEdit.setFocus()
            return
        except Exception as exc:  # ket noi DB / loi he thong
            QMessageBox.critical(
                self,
                "Lỗi hệ thống",
                f"Không thể kết nối hệ thống:\n{exc}\n\n"
                "Hãy kiểm tra MySQL đang chạy và file .env đã đúng.",
            )
            return

        self._root_stack.setCurrentWidget(self._main)
        self._refresh_user_indicator(user)
        self._apply_role_visibility(user)
        try:
            self._reload_catalog_data()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Tải dữ liệu",
                f"Đăng nhập thành công nhưng không tải được dữ liệu danh mục:\n{exc}",
            )
        self._set_active("dashboard")

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

        customers_page = self._pages.get("customers")
        if customers_page and hasattr(customers_page, "customersTable"):
            customers_page.customersTable.setRowCount(0)

        pets_page = self._pages.get("pets")
        if pets_page:
            if hasattr(pets_page, "petsTable"):
                pets_page.petsTable.setRowCount(0)
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

        # Luu flag de render action column
        self._is_admin = is_admin

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

        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(
            ["ID", "Username", "Họ tên", "Role", "SĐT", "Trạng thái", "Thao tác"]
        )
        self._setup_table(table)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root.addWidget(table, 1)

        def refresh() -> None:
            rows = user_service.list_users(active_only=False)
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

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        root.addWidget(buttons)
        dlg.exec()

    def _make_admin_actions(self, *, uid: int, is_active: bool, on_refresh, parent: QWidget) -> QWidget:
        btn_edit = _build_action_button("Sửa", "#EEF2FF", "#3730A3", hover="#E0E7FF")
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
                    try:
                        w.reload()
                    except Exception:
                        pass
                return

