from __future__ import annotations

import os
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget

from .theme import qss


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

        self.setCentralWidget(self._login)
        self._wire_login()
        self._wire_main()

        self._load_pages()
        self._set_active("dashboard")

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

        add("dashboard", "dashboard.ui")
        add("customers", "customers.ui")
        add("pets", "pets.ui")
        add("services", "services.ui")
        add("appointments", "appointments.ui")
        add("invoices", "invoices.ui")

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

