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
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
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
            table.setRowCount(len(customers))
            for r, c in enumerate(customers):
                table.setItem(r, 0, QTableWidgetItem(c.id))
                table.setItem(r, 1, QTableWidgetItem(c.name))
                table.setItem(r, 2, QTableWidgetItem(c.phone))
                table.setItem(r, 3, QTableWidgetItem(c.address))
                table.setItem(r, 4, QTableWidgetItem("Sửa | Xóa"))
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
            thumb = 72
            table.setIconSize(QSize(thumb, thumb))
            owner_name = {c.id: c.name for c in customers}

            def fill_pets(owner_id: str | None) -> None:
                data = [p for p in pets if owner_id in (None, "", "ALL") or p.owner_id == owner_id]
                table.setRowCount(len(data))
                for r, p in enumerate(data):
                    table.setRowHeight(r, thumb + 14)

                    # image cell
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

            combo = pets_page.customerFilterCombo
            combo.clear()
            combo.addItem("Tất cả khách hàng", "ALL")
            for c in customers:
                combo.addItem(c.name, c.id)
            combo.currentIndexChanged.connect(lambda _: fill_pets(combo.currentData()))
            fill_pets("ALL")

            def choose_image(row: int, column: int) -> None:
                if row < 0:
                    return
                # column 0 is image
                if column != 0:
                    return
                owner_text = table.item(row, 5).text() if table.item(row, 5) else ""
                # find owner_id by name
                owner_id = next((cid for cid, name in owner_name.items() if name == owner_text), "")
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
                fill_pets(combo.currentData())

            table.cellDoubleClicked.connect(choose_image)

        # ---- Appointments page ----
        ap_page = self._pages.get("appointments")
        if ap_page:
            ap_page.customerCombo.clear()
            ap_page.customerCombo.addItem("Chọn khách hàng", "")
            for c in customers:
                ap_page.customerCombo.addItem(f"{c.name} ({c.phone})", c.id)

            ap_page.serviceCombo.clear()
            ap_page.serviceCombo.addItem("Chọn dịch vụ", "")
            for s in services:
                ap_page.serviceCombo.addItem(f"{s.name} ({s.price:,}đ)".replace(",", "."), s.name)

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
        ap_page.petListWidget.clear()
        cid = ap_page.customerCombo.currentData()
        if not cid:
            return
        for p in self._pets:
            if p.owner_id != cid:
                continue
            item = QListWidgetItem(p.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            ap_page.petListWidget.addItem(item)

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
        service_name = ap_page.serviceCombo.currentData()
        when = ap_page.timeEdit.dateTime().toString("dd/MM/yyyy HH:mm")

        customer_text = ap_page.customerCombo.currentText()
        if customer_id and "(" in customer_text:
            customer_text = customer_text.split("(")[0].strip()

        if not customer_id:
            QMessageBox.warning(self, "Đặt lịch", "Vui lòng chọn khách hàng.")
            return
        if not service_name:
            QMessageBox.warning(self, "Đặt lịch", "Vui lòng chọn dịch vụ.")
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
        self._render_appointments_table()
        for i in range(ap_page.petListWidget.count()):
            it = ap_page.petListWidget.item(i)
            if it:
                it.setCheckState(Qt.CheckState.Unchecked)
        if ap_page.appointmentsTable.rowCount() > 0:
            ap_page.appointmentsTable.selectRow(ap_page.appointmentsTable.rowCount() - 1)

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

