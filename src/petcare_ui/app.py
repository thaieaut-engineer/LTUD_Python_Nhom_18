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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .theme import background_image_path, qss
from .pages.dashboard import DashboardView
from src.petcare_backend.services import auth_service
from src.petcare_backend.services import customer_service, pet_service, service_service
from src.petcare_backend.models import Customer, Pet, Service
from src.petcare_backend.session import Session


APPOINTMENT_STATUSES = ("Chờ xử lý", "Đang thực hiện", "Hoàn thành")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ui_path(name: str) -> str:
    return str(_repo_root() / "ui" / name)


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

        self.setCentralWidget(self._login)
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

    def _install_menubar(self) -> None:
        from PyQt6.QtGui import QAction

        menubar = self.menuBar()
        menubar.clear()
        account_menu = menubar.addMenu("Tài khoản")

        change_pw = QAction("Đổi mật khẩu...", self)
        change_pw.triggered.connect(self._show_change_password_dialog)
        account_menu.addAction(change_pw)

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
        """Khoi tao cac page danh muc (B2/B3/B4). Du lieu se load sau login."""
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

    def _reload_catalog_data(self) -> None:
        """Load khach hang/thu cung/dich vu tu MySQL va render UI."""
        self._reload_customers(None)
        self._reload_services()
        self._reload_pets()
        self._refresh_pets_customer_filter()
        self._refresh_appointments_customer_combo()

        dash = self._pages.get("dashboard")
        if isinstance(dash, DashboardView):
            try:
                dash.reload()
            except Exception:
                pass

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
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)

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
        table.verticalHeader().setVisible(False)
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
        if cid:
            for p in self._pets:
                if p.customer_id != cid:
                    continue
                item = QListWidgetItem(p.name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
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
            combo.addItem("Chọn dịch vụ", "")
            for s in self._services_list:
                combo.addItem(
                    f"{s.name} ({s.price:,}đ)".replace(",", "."), s.name
                )
            prev = previous_selection.get(name)
            if prev:
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
        table: QTableWidget = ap_page.appointmentsTable
        self._setup_appointments_table(table)
        table.blockSignals(True)
        table.setRowCount(len(self._demo_appointments))
        for r, a in enumerate(self._demo_appointments):
            table.setItem(r, 0, QTableWidgetItem(str(a["when"])))
            table.setItem(r, 1, QTableWidgetItem(str(a["customer"])))
            pets_list = a.get("pets")
            if isinstance(pets_list, list) and pets_list:
                pet_txt = ", ".join(str(x) for x in pets_list)
            else:
                pet_txt = str(a.get("pet", ""))
            table.setItem(r, 2, QTableWidgetItem(pet_txt))
            table.setItem(r, 3, QTableWidgetItem(str(a["service"])))

            combo = QComboBox()
            combo.addItems(APPOINTMENT_STATUSES)
            st = str(a.get("status", "Chờ xử lý"))
            idx = combo.findText(st)
            combo.blockSignals(True)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)
            combo.currentTextChanged.connect(lambda text, row=r: self._on_appt_status_changed(row, text))
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            table.setCellWidget(r, 4, combo)

            res_item = QTableWidgetItem(str(a.get("result", "")))
            res_item.setFlags(
                res_item.flags()
                | Qt.ItemFlag.ItemIsEditable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            table.setItem(r, 5, res_item)

        table.blockSignals(False)

        hdr = table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        status_w = self._appointment_status_column_width_px(table)
        table.setColumnWidth(4, status_w)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        for r in range(table.rowCount()):
            cw = table.cellWidget(r, 4)
            if isinstance(cw, QComboBox):
                view = cw.view()
                if view is not None:
                    view.setMinimumWidth(max(status_w, 260))

        self._sync_appointment_detail_panel()

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
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

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
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        btn_edit = QPushButton("Sửa")
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setStyleSheet(
            "QPushButton{background:#EEF2FF;color:#3730A3;border:none;padding:4px 10px;border-radius:6px;font:700 8pt 'Segoe UI';}"
            "QPushButton:hover{background:#E0E7FF;}"
        )
        btn_edit.clicked.connect(lambda: on_edit(None))

        btn_del = QPushButton(delete_text)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(
            "QPushButton{background:#FEE2E2;color:#B91C1C;border:none;padding:4px 10px;border-radius:6px;font:700 8pt 'Segoe UI';}"
            "QPushButton:hover{background:#FCA5A5;color:#7F1D1D;}"
        )
        btn_del.clicked.connect(lambda: on_delete(None))

        lay.addWidget(btn_edit)
        lay.addWidget(btn_del)
        lay.addStretch(1)
        return w

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
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return

        customer_id = ap_page.customerCombo.currentData()
        when = ap_page.timeEdit.dateTime().toString("dd/MM/yyyy HH:mm")

        customer_text = ap_page.customerCombo.currentText()
        if customer_id and "(" in customer_text:
            customer_text = customer_text.split("(")[0].strip()

        if not customer_id:
            QMessageBox.warning(self, "Đặt lịch", "Vui lòng chọn khách hàng.")
            return

        pets_selected: list[str] = []
        for i in range(ap_page.petListWidget.count()):
            it = ap_page.petListWidget.item(i)
            if it and it.checkState() == Qt.CheckState.Checked:
                pets_selected.append(it.text())

        if not pets_selected:
            QMessageBox.warning(
                self,
                "Đặt lịch",
                "Vui lòng chọn ít nhất một thú cưng (tích vào danh sách sau khi chọn khách hàng).",
            )
            return

        per_pet_mode = len(pets_selected) >= 2

        if per_pet_mode:
            plan: list[tuple[str, str]] = []
            missing: list[str] = []
            for name in pets_selected:
                combo = self._per_pet_service_combos.get(name)
                svc = combo.currentData() if combo else ""
                if not svc:
                    missing.append(name)
                else:
                    plan.append((name, svc))
            if missing:
                QMessageBox.warning(
                    self,
                    "Đặt lịch",
                    "Vui lòng chọn dịch vụ cho: " + ", ".join(missing) + ".",
                )
                return
            for name, svc in plan:
                self._demo_appointments.append(
                    {
                        "customer_id": customer_id or "",
                        "customer": customer_text,
                        "pet": name,
                        "pets": [name],
                        "service": svc,
                        "when": when,
                        "status": "Chờ xử lý",
                        "result": "",
                    }
                )
            added = len(plan)
        else:
            service_name = ap_page.serviceCombo.currentData()
            if not service_name:
                QMessageBox.warning(self, "Đặt lịch", "Vui lòng chọn dịch vụ.")
                return
            pet_display = ", ".join(pets_selected)
            self._demo_appointments.append(
                {
                    "customer_id": customer_id or "",
                    "customer": customer_text,
                    "pet": pet_display,
                    "pets": pets_selected,
                    "service": service_name,
                    "when": when,
                    "status": "Chờ xử lý",
                    "result": "",
                }
            )
            added = 1

        self._render_appointments_table()
        ap_page.petListWidget.blockSignals(True)
        for i in range(ap_page.petListWidget.count()):
            it = ap_page.petListWidget.item(i)
            if it:
                it.setCheckState(Qt.CheckState.Unchecked)
        ap_page.petListWidget.blockSignals(False)
        self._update_per_pet_service_ui()
        if ap_page.appointmentsTable.rowCount() > 0:
            last_row = ap_page.appointmentsTable.rowCount() - 1
            ap_page.appointmentsTable.selectRow(max(0, last_row - added + 1))

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

        self.setCentralWidget(self._main)
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
        self.setCentralWidget(self._login)
        self._refresh_user_indicator(None)

    def _refresh_user_indicator(self, user) -> None:
        if user is None:
            self.setWindowTitle("Pet Care Management")
            return
        self.setWindowTitle(
            f"Pet Care Management - {user.full_name} ({user.role_name})"
        )

    def _apply_role_visibility(self, user) -> None:
        # Tam thoi chua co nut nao chi rieng ADMIN. Khi them quan ly user (B1)
        # se an/hien o day. Vi du:
        # is_admin = user.is_admin
        # if hasattr(self._main, "navUsers"):
        #     self._main.navUsers.setVisible(is_admin)
        return

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

