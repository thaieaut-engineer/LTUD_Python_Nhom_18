from __future__ import annotations

import os
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt, QDateTime, QSize
from PyQt6.QtGui import QFontMetrics, QIcon, QPixmap
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

from .theme import qss
from .demo_data import Customer, Pet, seed_demo


APPOINTMENT_STATUSES = ("Chờ xử lý", "Đang thực hiện", "Hoàn thành")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ui_path(name: str) -> str:
    return str(_repo_root() / "ui" / name)


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
        self._pet_images: dict[tuple[str, str], str] = {}
        self._customers: list[Customer] = []
        self._pets: list[Pet] = []
        self._pets_thumb: int = 72
        self._services_list: list = []
        self._per_pet_service_container: QWidget | None = None
        self._per_pet_service_rows_layout: QVBoxLayout | None = None
        self._per_pet_service_combos: dict[str, QComboBox] = {}

        self.setCentralWidget(self._login)
        self._wire_login()
        self._wire_main()

        self._load_pages()
        self._set_active("dashboard")
        self._seed_demo_data()

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss())

    def _wire_login(self) -> None:
        self._login.LoginButton.clicked.connect(self._on_login)
        self._login.usernameEdit.returnPressed.connect(self._on_login)
        self._login.passwordEdit.returnPressed.connect(self._on_login)

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

        add("dashboard", "dashboard.ui")
        add("customers", "customers.ui")
        add("pets", "pets.ui")
        add("services", "services.ui")
        add("appointments", "appointments.ui")
        ap_lay = self._pages["appointments"].layout()
        if isinstance(ap_lay, QVBoxLayout) and ap_lay.count() >= 2:
            ap_lay.setStretch(1, 1)

        add("invoices", "invoices.ui")

    def _seed_demo_data(self) -> None:
        customers, pets, services, appointments, invoices = seed_demo()
        self._customers = list(customers)
        self._pets = list(pets)

        # ---- Dashboard ----
        dash = self._pages.get("dashboard")
        if dash:
            customers_count = len(customers)
            pets_count = len(pets)
            today = QDateTime.currentDateTime().date().toPyDate()
            revenue_today = sum(
                inv.total for inv in invoices if inv.paid and inv.created_at.date() == today
            )
            appt_today = sum(1 for ap in appointments if ap.when.date() == today)

            dash.blueValue.setText(f"{revenue_today:,}đ".replace(",", "."))
            dash.orangeValue.setText(str(pets_count))
            dash.greenValue.setText(str(customers_count))
            dash.pinkValue.setText(str(appt_today))

        # ---- Customers table ----
        customers_page = self._pages.get("customers")
        if customers_page:
            table: QTableWidget = customers_page.customersTable
            self._setup_table(table)
            self._render_customers_table()
            customers_page.searchEdit.textChanged.connect(
                lambda text: self._filter_table(table, text, cols=(0, 1, 2, 3))
            )
            customers_page.viewPetsButton.clicked.connect(self._on_view_customer_pets)

        # ---- Services table ----
        services_page = self._pages.get("services")
        if services_page:
            table: QTableWidget = services_page.servicesTable
            self._setup_table(table)
            table.setRowCount(len(services))
            for r, s in enumerate(services):
                table.setItem(r, 0, QTableWidgetItem(s.name))
                table.setItem(r, 1, QTableWidgetItem(f"{s.price:,}đ".replace(",", ".")))
                table.setItem(r, 2, QTableWidgetItem(s.description))
                table.setItem(r, 3, QTableWidgetItem("Sửa | Xóa"))

        # ---- Pets table + filter ----
        pets_page = self._pages.get("pets")
        if pets_page:
            table: QTableWidget = pets_page.petsTable
            self._setup_table(table)
            table.setIconSize(QSize(self._pets_thumb, self._pets_thumb))

            self._refresh_pets_customer_filter()
            pets_page.customerFilterCombo.currentIndexChanged.connect(
                lambda _: self._render_pets_table(pets_page.customerFilterCombo.currentData())
            )
            self._render_pets_table("ALL")
            table.cellDoubleClicked.connect(self._on_pet_image_double_clicked)
            pets_page.addPetButton.clicked.connect(self._on_add_pet_clicked)

        # ---- Appointments page ----
        ap_page = self._pages.get("appointments")
        if ap_page:
            self._services_list = list(services)
            self._refresh_appointments_customer_combo()
            ap_page.addNewCustomerButton.clicked.connect(self._on_add_new_customer_clicked)

            ap_page.serviceCombo.clear()
            ap_page.serviceCombo.addItem("Chọn dịch vụ", "")
            for s in services:
                ap_page.serviceCombo.addItem(f"{s.name} ({s.price:,}đ)".replace(",", "."), s.name)

            self._build_per_pet_service_container(ap_page)

            ap_page.timeEdit.setDateTime(QDateTime.currentDateTime().addSecs(3600))

            self._demo_appointments = [
                {
                    "customer_id": a.customer_id,
                    "customer": next((c.name for c in customers if c.id == a.customer_id), a.customer_id),
                    "pet": a.pet_name,
                    "pets": [a.pet_name],
                    "service": a.service_name,
                    "when": a.when.strftime("%d/%m/%Y %H:%M"),
                    "status": a.status,
                    "result": "",
                }
                for a in appointments
            ]
            ap_page.customerCombo.currentIndexChanged.connect(lambda _: self._refresh_appointment_pet_list())
            ap_page.petListWidget.itemChanged.connect(self._on_appointment_pet_check_changed)
            self._refresh_appointment_pet_list()
            ap_page.appointmentsTable.itemChanged.connect(self._on_appointment_result_changed)
            ap_page.appointmentsTable.itemSelectionChanged.connect(self._on_appointment_selection_changed)
            ap_page.confirmButton.clicked.connect(self._on_demo_confirm_appointment)
            self._render_appointments_table()
            if ap_page.appointmentsTable.rowCount() > 0:
                ap_page.appointmentsTable.selectRow(0)

        # ---- Invoices page ----
        inv_page = self._pages.get("invoices")
        if inv_page:
            paid = [inv for inv in invoices if inv.paid]
            unpaid = [inv for inv in invoices if not inv.paid]
            inv_page.emptyLabel.setText(
                f"Demo: {len(invoices)} hóa đơn (Đã thanh toán: {len(paid)} | Chưa thanh toán: {len(unpaid)})"
            )

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
                if p.owner_id != cid:
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

    def _render_customers_table(self) -> None:
        customers_page = self._pages.get("customers")
        if not customers_page:
            return
        table: QTableWidget = customers_page.customersTable
        table.setRowCount(len(self._customers))
        for r, c in enumerate(self._customers):
            table.setItem(r, 0, QTableWidgetItem(c.id))
            table.setItem(r, 1, QTableWidgetItem(c.name))
            table.setItem(r, 2, QTableWidgetItem(c.phone))
            table.setItem(r, 3, QTableWidgetItem(c.address))
            table.setItem(r, 4, QTableWidgetItem("Sửa | Xóa"))

    def _render_pets_table(self, owner_id: str | None = "ALL") -> None:
        pets_page = self._pages.get("pets")
        if not pets_page:
            return
        table: QTableWidget = pets_page.petsTable
        thumb = self._pets_thumb
        owner_name = {c.id: c.name for c in self._customers}
        data = [p for p in self._pets if owner_id in (None, "", "ALL") or p.owner_id == owner_id]
        table.setRowCount(len(data))
        for r, p in enumerate(data):
            table.setRowHeight(r, thumb + 14)

            img_item = QTableWidgetItem("📷")
            img_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            img_path = self._pet_images.get((p.owner_id, p.name))
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

            table.setItem(r, 1, QTableWidgetItem(p.name))
            table.setItem(r, 2, QTableWidgetItem(p.species))
            table.setItem(r, 3, QTableWidgetItem(p.breed))
            table.setItem(r, 4, QTableWidgetItem(str(p.age)))
            table.setItem(r, 5, QTableWidgetItem(owner_name.get(p.owner_id, p.owner_id)))
            table.setItem(r, 6, QTableWidgetItem("Sửa | Xóa"))

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
            combo.addItem(c.name, c.id)
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
            combo.addItem(f"{c.name} ({c.phone})", c.id)
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
        owner_text = table.item(row, 5).text() if table.item(row, 5) else ""
        owner_id = next((c.id for c in self._customers if c.name == owner_text), "")
        pet_name = table.item(row, 1).text() if table.item(row, 1) else ""
        if not owner_id or not pet_name:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh thú cưng",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if not path:
            return
        self._pet_images[(owner_id, pet_name)] = path
        self._render_pets_table(pets_page.customerFilterCombo.currentData())

    def _generate_customer_id(self) -> str:
        max_num = 0
        for c in self._customers:
            if c.id.startswith("KH"):
                try:
                    n = int(c.id[2:])
                    if n > max_num:
                        max_num = n
                except ValueError:
                    continue
        return f"KH{max_num + 1:03d}"

    def _on_add_new_customer_clicked(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm khách hàng mới")
        dlg.setMinimumWidth(560)
        dlg.resize(600, 620)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        title = QLabel("Nhập thông tin khách hàng và thú cưng")
        title.setStyleSheet("font: 800 12pt 'Segoe UI'; color: #0F172A;")
        layout.addWidget(title)

        customer_section_title = QLabel("Thông tin khách hàng")
        customer_section_title.setStyleSheet(
            "font: 700 10pt 'Segoe UI'; color: #0F172A; padding-top: 4px;"
        )
        layout.addWidget(customer_section_title)

        form = QFormLayout()
        form.setSpacing(10)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("VD: Nguyễn Văn A")
        phone_edit = QLineEdit()
        phone_edit.setPlaceholderText("VD: 0901234567 (tùy chọn)")
        address_edit = QLineEdit()
        address_edit.setPlaceholderText("Địa chỉ (tùy chọn)")

        form.addRow("Tên khách hàng *", name_edit)
        form.addRow("Số điện thoại", phone_edit)
        form.addRow("Địa chỉ", address_edit)
        layout.addLayout(form)

        pets_header = QHBoxLayout()
        pets_section_title = QLabel("Danh sách thú cưng")
        pets_section_title.setStyleSheet(
            "font: 700 10pt 'Segoe UI'; color: #0F172A;"
        )
        pets_header.addWidget(pets_section_title)
        pets_header.addStretch(1)
        add_pet_btn = QPushButton("+ Thêm thú cưng")
        add_pet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_pet_btn.setStyleSheet(
            "QPushButton { background: #2563EB; color: white; border: none;"
            " padding: 6px 14px; border-radius: 6px; font: 600 9pt 'Segoe UI'; }"
            "QPushButton:hover { background: #1D4ED8; }"
        )
        pets_header.addWidget(add_pet_btn)
        layout.addLayout(pets_header)

        pets_scroll = QScrollArea()
        pets_scroll.setWidgetResizable(True)
        pets_scroll.setFrameShape(QFrame.Shape.NoFrame)
        pets_scroll.setMinimumHeight(260)

        pets_container = QWidget()
        pets_rows_layout = QVBoxLayout(pets_container)
        pets_rows_layout.setContentsMargins(0, 0, 0, 0)
        pets_rows_layout.setSpacing(8)
        pets_rows_layout.addStretch(1)
        pets_scroll.setWidget(pets_container)
        layout.addWidget(pets_scroll, 1)

        pet_rows: list[dict] = []

        def _update_remove_buttons() -> None:
            only_one = len(pet_rows) <= 1
            for row in pet_rows:
                row["remove_btn"].setDisabled(only_one)

        def _add_pet_row() -> None:
            frame = QFrame()
            frame.setStyleSheet(
                "QFrame { background: #F8FAFC; border: 1px solid #E2E8F0;"
                " border-radius: 8px; }"
            )
            v = QVBoxLayout(frame)
            v.setContentsMargins(12, 10, 12, 12)
            v.setSpacing(8)

            head = QHBoxLayout()
            head_label = QLabel()
            head_label.setStyleSheet(
                "font: 700 9pt 'Segoe UI'; color: #334155; border: none;"
                " background: transparent;"
            )
            head.addWidget(head_label)
            head.addStretch(1)
            remove_btn = QPushButton("Xóa")
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.setStyleSheet(
                "QPushButton { background: #FEE2E2; color: #B91C1C; border: none;"
                " padding: 4px 10px; border-radius: 6px; font: 600 8pt 'Segoe UI'; }"
                "QPushButton:hover { background: #FCA5A5; color: #7F1D1D; }"
                "QPushButton:disabled { background: #F1F5F9; color: #94A3B8; }"
            )
            head.addWidget(remove_btn)
            v.addLayout(head)

            pf = QFormLayout()
            pf.setSpacing(8)
            pet_name_edit = QLineEdit()
            pet_name_edit.setPlaceholderText("VD: Milu")
            species_edit = QLineEdit()
            species_edit.setPlaceholderText("VD: Chó / Mèo")
            breed_edit = QLineEdit()
            breed_edit.setPlaceholderText("VD: Poodle")
            age_spin = QSpinBox()
            age_spin.setRange(0, 50)
            age_spin.setValue(0)
            age_spin.setSuffix(" tuổi")

            pf.addRow("Tên thú cưng *", pet_name_edit)
            pf.addRow("Loài *", species_edit)
            pf.addRow("Giống *", breed_edit)
            pf.addRow("Tuổi", age_spin)
            v.addLayout(pf)

            insert_at = pets_rows_layout.count() - 1
            pets_rows_layout.insertWidget(insert_at, frame)

            row_data = {
                "frame": frame,
                "head_label": head_label,
                "remove_btn": remove_btn,
                "name": pet_name_edit,
                "species": species_edit,
                "breed": breed_edit,
                "age": age_spin,
            }
            pet_rows.append(row_data)

            def _renumber() -> None:
                for i, r in enumerate(pet_rows, start=1):
                    r["head_label"].setText(f"Thú cưng #{i}")

            def _remove() -> None:
                if len(pet_rows) <= 1:
                    return
                pet_rows.remove(row_data)
                pets_rows_layout.removeWidget(frame)
                frame.setParent(None)
                frame.deleteLater()
                _renumber()
                _update_remove_buttons()

            remove_btn.clicked.connect(_remove)
            _renumber()
            _update_remove_buttons()

        add_pet_btn.clicked.connect(_add_pet_row)
        _add_pet_row()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("Xác nhận thêm khách hàng mới")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Hủy")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        name = name_edit.text().strip()
        phone = phone_edit.text().strip()
        address = address_edit.text().strip()

        collected_pets: list[tuple[str, str, str, int]] = []
        missing_customer: list[str] = []
        if not name:
            missing_customer.append("tên khách hàng")

        pet_errors: list[str] = []
        seen_names: set[str] = set()
        for idx, row in enumerate(pet_rows, start=1):
            pet_name = row["name"].text().strip()
            species = row["species"].text().strip()
            breed = row["breed"].text().strip()
            age = int(row["age"].value())
            row_missing: list[str] = []
            if not pet_name:
                row_missing.append("tên")
            if not species:
                row_missing.append("loài")
            if not breed:
                row_missing.append("giống")
            if row_missing:
                pet_errors.append(
                    f"Thú cưng #{idx}: thiếu {', '.join(row_missing)}"
                )
                continue
            key = pet_name.lower()
            if key in seen_names:
                pet_errors.append(
                    f"Thú cưng #{idx}: tên '{pet_name}' bị trùng trong danh sách"
                )
                continue
            seen_names.add(key)
            collected_pets.append((pet_name, species, breed, age))

        if missing_customer or pet_errors or not collected_pets:
            msgs: list[str] = []
            if missing_customer:
                msgs.append("Vui lòng nhập: " + ", ".join(missing_customer) + ".")
            if not collected_pets and not pet_errors:
                msgs.append("Vui lòng nhập thông tin ít nhất một thú cưng.")
            if pet_errors:
                msgs.append("\n".join(pet_errors))
            QMessageBox.warning(self, "Thiếu thông tin", "\n".join(msgs))
            return

        new_id = self._generate_customer_id()
        self._customers.append(Customer(new_id, name, phone, address))
        for pet_name, species, breed, age in collected_pets:
            self._pets.append(Pet(pet_name, species, breed, age, new_id))

        self._render_customers_table()

        pets_page = self._pages.get("pets")
        current_filter = (
            pets_page.customerFilterCombo.currentData() if pets_page else "ALL"
        ) or "ALL"
        self._refresh_pets_customer_filter()
        self._render_pets_table(current_filter)
        self._refresh_appointments_customer_combo()

        ap_page = self._pages.get("appointments")
        if ap_page:
            idx = ap_page.customerCombo.findData(new_id)
            if idx >= 0:
                ap_page.customerCombo.setCurrentIndex(idx)

        pet_names_display = ", ".join(p[0] for p in collected_pets)
        QMessageBox.information(
            self,
            "Thành công",
            f"Đã thêm khách hàng {name} (mã {new_id}) cùng {len(collected_pets)} "
            f"thú cưng: {pet_names_display}.",
        )

    def _on_add_pet_clicked(self) -> None:
        if not self._customers:
            QMessageBox.warning(
                self,
                "Thêm thú cưng",
                "Chưa có khách hàng nào. Hãy thêm khách hàng trước tại trang Đặt lịch.",
            )
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm thú cưng")
        dlg.setMinimumWidth(440)

        layout = QVBoxLayout(dlg)

        title = QLabel("Nhập thông tin thú cưng")
        title.setStyleSheet("font: 800 12pt 'Segoe UI'; color: #0F172A;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        owner_combo = QComboBox()
        for c in self._customers:
            owner_combo.addItem(f"{c.name} ({c.id})", c.id)

        pets_page = self._pages.get("pets")
        if pets_page:
            preselect = pets_page.customerFilterCombo.currentData()
            if preselect and preselect != "ALL":
                idx = owner_combo.findData(preselect)
                if idx >= 0:
                    owner_combo.setCurrentIndex(idx)

        pet_name_edit = QLineEdit()
        pet_name_edit.setPlaceholderText("VD: Milu")
        species_edit = QLineEdit()
        species_edit.setPlaceholderText("VD: Chó / Mèo")
        breed_edit = QLineEdit()
        breed_edit.setPlaceholderText("VD: Poodle")
        age_spin = QSpinBox()
        age_spin.setRange(0, 50)
        age_spin.setValue(0)
        age_spin.setSuffix(" tuổi")

        form.addRow("Khách hàng *", owner_combo)
        form.addRow("Tên thú cưng *", pet_name_edit)
        form.addRow("Loài *", species_edit)
        form.addRow("Giống *", breed_edit)
        form.addRow("Tuổi", age_spin)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("Xác nhận thêm thú cưng")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Hủy")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        owner_id = owner_combo.currentData()
        pet_name = pet_name_edit.text().strip()
        species = species_edit.text().strip()
        breed = breed_edit.text().strip()
        age = int(age_spin.value())

        missing: list[str] = []
        if not owner_id:
            missing.append("khách hàng")
        if not pet_name:
            missing.append("tên thú cưng")
        if not species:
            missing.append("loài")
        if not breed:
            missing.append("giống")
        if missing:
            QMessageBox.warning(
                self,
                "Thiếu thông tin",
                "Vui lòng nhập: " + ", ".join(missing) + ".",
            )
            return

        self._pets.append(Pet(pet_name, species, breed, age, owner_id))

        if pets_page:
            filter_combo = pets_page.customerFilterCombo
            idx = filter_combo.findData(owner_id)
            if idx >= 0:
                filter_combo.blockSignals(True)
                filter_combo.setCurrentIndex(idx)
                filter_combo.blockSignals(False)
            self._render_pets_table(filter_combo.currentData())

        self._refresh_appointment_pet_list()

        owner_name = next((c.name for c in self._customers if c.id == owner_id), owner_id)
        QMessageBox.information(
            self,
            "Thành công",
            f"Đã thêm thú cưng {pet_name} cho khách hàng {owner_name}.",
        )

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
        customer_id = id_item.text()
        customer_name = name_item.text() if name_item else customer_id
        pets_row = [p for p in self._pets if p.owner_id == customer_id]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Thú cưng — {customer_name}")
        dlg.resize(440, 340)
        layout = QVBoxLayout(dlg)
        if not pets_row:
            layout.addWidget(QLabel("Khách hàng này chưa có thú cưng trong hệ thống."))
        else:
            lw = QListWidget()
            for p in pets_row:
                lw.addItem(f"{p.name} — {p.species}, {p.breed}, {p.age} tuổi")
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
        self.setCentralWidget(self._main)
        self._set_active("dashboard")

    def _on_logout(self) -> None:
        self.setCentralWidget(self._login)

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
                return

