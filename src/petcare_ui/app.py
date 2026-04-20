from __future__ import annotations

import os
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt, QDateTime, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from .theme import qss
from .demo_data import seed_demo


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
        self._demo_appointments: list[dict[str, str]] = []
        self._demo_exams: list[dict[str, str]] = []
        self._pet_images: dict[tuple[str, str], str] = {}

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
        self._main.navExam.clicked.connect(lambda: self._set_active("exam"))
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
        add("exam", "exam.ui")
        add("invoices", "invoices.ui")

    def _seed_demo_data(self) -> None:
        customers, pets, services, appointments, invoices = seed_demo()

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

            # preload recent
            self._demo_appointments = [
                {
                    "customer": next((c.name for c in customers if c.id == a.customer_id), a.customer_id),
                    "pet": a.pet_name,
                    "service": a.service_name,
                    "when": a.when.strftime("%d/%m/%Y %H:%M"),
                    "status": a.status,
                }
                for a in appointments
            ]
            self._render_recent_appointments()
            ap_page.confirmButton.clicked.connect(self._on_demo_confirm_appointment)

        # ---- Exam page ----
        exam_page = self._pages.get("exam")
        if exam_page:
            exam_page.examCustomerCombo.clear()
            exam_page.examCustomerCombo.addItem("Chọn khách hàng", "")
            for c in customers:
                exam_page.examCustomerCombo.addItem(f"{c.name} ({c.phone})", c.id)

            exam_page.examTimeEdit.setDateTime(QDateTime.currentDateTime())

            # preload demo exams
            self._demo_exams = [
                {
                    "when": (QDateTime.currentDateTime().addDays(-1)).toString("dd/MM/yyyy HH:mm"),
                    "customer": "Nguyễn Thị Lan",
                    "pet": "Bông",
                    "temp": "38.7°C",
                    "weight": "3.1kg",
                    "diagnosis": "Viêm đường hô hấp nhẹ",
                    "fee": "0đ",
                },
                {
                    "when": (QDateTime.currentDateTime().addSecs(-7200)).toString("dd/MM/yyyy HH:mm"),
                    "customer": "Trần Minh Khoa",
                    "pet": "Lucky",
                    "temp": "39.2°C",
                    "weight": "10.5kg",
                    "diagnosis": "Rối loạn tiêu hoá (theo dõi)",
                    "fee": "20.000đ",
                },
            ]
            self._render_recent_exams()
            exam_page.saveExamButton.clicked.connect(self._on_demo_save_exam)

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

    def _render_recent_appointments(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return
        if not self._demo_appointments:
            ap_page.recentEmpty.setText("Chưa có lịch hẹn")
            return
        last = list(reversed(self._demo_appointments))[:5]
        lines = [
            f"- {a['when']} | {a['customer']} | {a['pet']} | {a['service']} | {a['status']}" for a in last
        ]
        ap_page.recentEmpty.setText("\n".join(lines))

    def _render_recent_exams(self) -> None:
        exam_page = self._pages.get("exam")
        if not exam_page:
            return
        if not self._demo_exams:
            exam_page.recentExamsLabel.setText("Chưa có phiên khám")
            return
        last = list(reversed(self._demo_exams))[:5]
        lines = [
            (
                f"- {e['when']} | {e['customer']} | {e['pet']} | "
                f"{e['temp']} | {e['weight']} | {e['diagnosis']} | Phí: {e['fee']}"
            )
            for e in last
        ]
        exam_page.recentExamsLabel.setText("\n".join(lines))

    def _on_demo_save_exam(self) -> None:
        exam_page = self._pages.get("exam")
        if not exam_page:
            return

        customer_id = exam_page.examCustomerCombo.currentData()
        customer_text = exam_page.examCustomerCombo.currentText()
        if customer_id and "(" in customer_text:
            customer_text = customer_text.split("(")[0].strip()
        if not customer_id:
            customer_text = "Chưa chọn khách hàng"

        pet = (exam_page.examPetEdit.text() or "").strip() or "Chưa nhập thú cưng"
        when = exam_page.examTimeEdit.dateTime().toString("dd/MM/yyyy HH:mm")
        temp = f"{exam_page.tempSpin.value():.1f}°C"
        weight = f"{exam_page.weightSpin.value():.1f}kg"
        diagnosis = (exam_page.diagnosisEdit.toPlainText() or "").strip() or "Chưa nhập chẩn đoán"
        fee_val = int(exam_page.extraFeeSpin.value())
        fee = f"{fee_val:,}đ".replace(",", ".")

        self._demo_exams.append(
            {
                "when": when,
                "customer": customer_text,
                "pet": pet,
                "temp": temp,
                "weight": weight,
                "diagnosis": diagnosis,
                "fee": fee,
            }
        )
        self._render_recent_exams()
        exam_page.examPetEdit.clear()
        exam_page.symptomsEdit.clear()
        exam_page.diagnosisEdit.clear()
        exam_page.extraFeeSpin.setValue(0)

    def _on_demo_confirm_appointment(self) -> None:
        ap_page = self._pages.get("appointments")
        if not ap_page:
            return

        customer_id = ap_page.customerCombo.currentData()
        service_name = ap_page.serviceCombo.currentData()
        pet_name = (ap_page.petEdit.text() or "").strip()
        when = ap_page.timeEdit.dateTime().toString("dd/MM/yyyy HH:mm")

        customer_text = ap_page.customerCombo.currentText()
        if customer_id and "(" in customer_text:
            customer_text = customer_text.split("(")[0].strip()

        if not customer_id:
            customer_text = "Chưa chọn khách hàng"
        if not service_name:
            service_name = "Chưa chọn dịch vụ"
        if not pet_name:
            pet_name = "Chưa nhập thú cưng"

        self._demo_appointments.append(
            {
                "customer": customer_text,
                "pet": pet_name,
                "service": service_name,
                "when": when,
                "status": "Chờ xử lý",
            }
        )
        self._render_recent_appointments()
        ap_page.petEdit.clear()

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
            "exam": self._main.navExam,
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

