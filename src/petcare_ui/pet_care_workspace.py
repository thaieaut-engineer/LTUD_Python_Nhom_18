"""Giao diện chi tiết chăm sóc thú cưng (luu tru theo ngay) — tham khảo layout bàn bida."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QHeaderView,
)

from src.petcare_backend.dao import pet_dao
from src.petcare_backend.models import Pet
from src.petcare_backend.services.pet_service import PetError
from src.petcare_backend.services import (
    pet_boarding_service,
    pet_service,
    service_service,
    product_service,
    invoice_service,
    payment_service,
)
from src.petcare_backend.services.pet_boarding_service import (
    BoardingError,
    STAY_STATUS_LABEL,
    LOG_TYPE_LABEL,
    PAYMENT_STATUS_LABEL,
)
from src.petcare_backend.dao import invoice_item_dao, invoice_dao


def _fmt_money(v) -> str:
    try:
        return f"{int(float(v)):,}đ".replace(",", ".")
    except (TypeError, ValueError):
        return "0đ"


def _fmt_dt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y %H:%M")
    return str(v)


class _ActionTile(QPushButton):
    """Nút chức năng lớn kiểu bàn bida."""

    def __init__(self, icon: str, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(140, 88)
        self.setStyleSheet(
            """
            QPushButton {
                background: #1E3A5F;
                color: white;
                border-radius: 12px;
                border: 1px solid #334155;
                text-align: center;
                padding: 10px;
                font: 600 10pt 'Segoe UI';
            }
            QPushButton:hover { background: #2563EB; }
            QPushButton:pressed { background: #1D4ED8; }
            QPushButton:disabled { background: #94A3B8; color: #E2E8F0; }
            """
        )
        self.setText(f"{icon}\n{title}" + (f"\n{subtitle}" if subtitle else ""))


class PetCareWorkspaceDialog(QDialog):
    """Workspace khi chọn thú cưng trong danh sách."""

    def __init__(
        self,
        parent,
        pet: Pet,
        *,
        employees: list,
        customers_lookup: dict[int, str],
        install_bg=None,
    ):
        super().__init__(parent)
        self._pet = pet
        self._employees = employees
        self._customers_lookup = customers_lookup
        self._install_bg = install_bg
        self._stay: dict | None = None
        self._stay_id: int | None = None

        self.setWindowTitle(f"Chăm sóc — {pet.name}")
        self.setMinimumSize(960, 680)
        if install_bg:
            install_bg(self, overlay_color=(15, 23, 42, 200))

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        self._header = QLabel()
        self._header.setStyleSheet(
            "background:#0F172A; color:white; padding:14px 18px; border-radius:12px; "
            "font: 800 13pt 'Segoe UI';"
        )
        root.addWidget(self._header)

        self._tabs = QTabWidget()
        root.addWidget(self._tabs, 1)

        self._build_overview_tab()
        self._build_history_tab()
        self._build_invoice_tab()

        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.reject)
        close_row.addWidget(btn_close)
        root.addLayout(close_row)

        self._reload_stay()

    def _build_overview_tab(self) -> None:
        tab = QWidget()
        lay = QHBoxLayout(tab)
        lay.setSpacing(14)

        # --- Thông tin thú ---
        info_box = QGroupBox("Thông tin thú cưng")
        info_box.setStyleSheet("QGroupBox { font-weight: 700; }")
        info_form = QFormLayout(info_box)
        self._name_edit = QLineEdit(self._pet.name)
        self._species_edit = QLineEdit(self._pet.species)
        self._breed_edit = QLineEdit(self._pet.breed or "")
        self._age_spin = QSpinBox()
        self._age_spin.setRange(0, 50)
        self._age_spin.setValue(0 if self._pet.age is None else int(self._pet.age))
        self._health_edit = QTextEdit(self._pet.health_note or "")
        self._health_edit.setMaximumHeight(72)
        owner = self._customers_lookup.get(self._pet.customer_id, f"#{self._pet.customer_id}")
        info_form.addRow("Chủ", QLabel(owner))
        info_form.addRow("Tên *", self._name_edit)
        info_form.addRow("Loài *", self._species_edit)
        info_form.addRow("Giống", self._breed_edit)
        info_form.addRow("Tuổi", self._age_spin)
        info_form.addRow("Ghi chú sức khoẻ", self._health_edit)
        btn_save_pet = QPushButton("💾  Lưu thông tin thú")
        btn_save_pet.clicked.connect(self._on_save_pet_info)
        info_form.addRow("", btn_save_pet)
        lay.addWidget(info_box, 1)

        # --- Chức năng + trạng thái ---
        right = QVBoxLayout()
        self._status_badge = QLabel()
        self._status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_badge.setStyleSheet(
            "padding:8px; border-radius:8px; font-weight:700; font-size:11pt;"
        )
        right.addWidget(self._status_badge)

        self._stay_info = QLabel()
        self._stay_info.setWordWrap(True)
        self._stay_info.setStyleSheet("color:#475569; font-size:10pt;")
        right.addWidget(self._stay_info)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._btn_checkin = _ActionTile("🏠", "Nhận thú", "Bắt đầu chăm sóc")
        self._btn_employee = _ActionTile("👤", "NV chăm sóc", "Gán nhân viên")
        self._btn_feed = _ActionTile("🍖", "Cho ăn", "Chọn đồ ăn + ảnh")
        self._btn_care_svc = _ActionTile("✨", "Dịch vụ", "Chăm sóc + ảnh")
        self._btn_video = _ActionTile("🎬", "Video", "Tình trạng")
        self._btn_pickup = _ActionTile("✅", "Khách nhận", "Trả thú")
        self._btn_invoice = _ActionTile("🧾", "Hóa đơn", "Tab thanh toán")

        tiles = [
            self._btn_checkin,
            self._btn_employee,
            self._btn_feed,
            self._btn_care_svc,
            self._btn_video,
            self._btn_pickup,
            self._btn_invoice,
        ]
        for i, btn in enumerate(tiles):
            grid.addWidget(btn, i // 3, i % 3)

        self._btn_checkin.clicked.connect(self._on_check_in)
        self._btn_employee.clicked.connect(self._on_assign_employee)
        self._btn_feed.clicked.connect(self._on_feeding_with_product)
        self._btn_care_svc.clicked.connect(self._on_care_service_with_photos)
        self._btn_video.clicked.connect(lambda: self._on_upload_media("VIDEO"))
        self._btn_pickup.clicked.connect(self._on_pickup)
        self._btn_invoice.clicked.connect(lambda: self._tabs.setCurrentIndex(2))

        right.addLayout(grid)

        self._billing_summary = QFrame()
        self._billing_summary.setStyleSheet(
            "QFrame { background:#F8FAFC; border:1px solid #CBD5E1; border-radius:10px; padding:8px; }"
        )
        bill_lay = QVBoxLayout(self._billing_summary)
        bill_title = QLabel("Tóm tắt nhanh")
        bill_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._bill_lines = QLabel("—")
        self._bill_lines.setWordWrap(True)
        self._bill_lines.setStyleSheet("font-family: Consolas; font-size:10pt;")
        bill_lay.addWidget(bill_title)
        bill_lay.addWidget(self._bill_lines)
        right.addWidget(self._billing_summary)

        lay.addLayout(right, 2)
        self._tabs.addTab(tab, "Tổng quan")

    def _build_history_tab(self) -> None:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        self._history_table = QTableWidget(0, 4)
        self._history_table.setHorizontalHeaderLabels(["Thời gian", "Loại", "Nội dung", "Nhân viên"])
        self._history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self._history_table)

        media_row = QHBoxLayout()
        self._media_list = QTableWidget(0, 3)
        self._media_list.setHorizontalHeaderLabels(["Loại", "Mô tả", "File"])
        self._media_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        btn_open_media = QPushButton("Mở file đã chọn")
        btn_open_media.clicked.connect(self._on_open_selected_media)
        lay.addWidget(QLabel("Ảnh / video đã tải:"))
        lay.addWidget(self._media_list)
        lay.addWidget(btn_open_media)
        self._tabs.addTab(tab, "Lịch sử")

    def _build_invoice_tab(self) -> None:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        self._inv_summary = QLabel("Chưa có hóa đơn cho đợt chăm sóc này.")
        self._inv_summary.setWordWrap(True)
        lay.addWidget(self._inv_summary)

        self._inv_hint = QLabel()
        self._inv_hint.setWordWrap(True)
        self._inv_hint.setStyleSheet(
            "color:#475569; font-size:10pt; padding:6px 8px; "
            "background:#F1F5F9; border-radius:8px;"
        )
        lay.addWidget(self._inv_hint)

        self._inv_items = QTableWidget(0, 4)
        self._inv_items.setHorizontalHeaderLabels(["Hạng mục", "SL", "Đơn giá", "Thành tiền"])
        self._inv_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._inv_items.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._inv_items.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._inv_items.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self._inv_items)

        row = QHBoxLayout()
        self._btn_create_inv = QPushButton("Tạo hóa đơn lưu trú")
        self._btn_add_svc = QPushButton("+ Thêm dịch vụ")
        self._btn_add_prod = QPushButton("+ Thêm sản phẩm")
        self._btn_del_line = QPushButton("Xóa dòng đã chọn")
        self._btn_pay = QPushButton("Xác nhận thanh toán")
        self._btn_reopen = QPushButton("Mở lại chỉnh sửa HĐ")
        self._btn_create_inv.clicked.connect(self._on_create_invoice)
        self._btn_add_svc.clicked.connect(self._on_add_service_to_invoice)
        self._btn_add_prod.clicked.connect(self._on_add_product_to_invoice)
        self._btn_del_line.clicked.connect(self._on_remove_invoice_line)
        self._btn_pay.clicked.connect(self._on_mark_paid)
        self._btn_reopen.clicked.connect(self._on_reopen_invoice)
        for b in (
            self._btn_create_inv,
            self._btn_add_svc,
            self._btn_add_prod,
            self._btn_del_line,
            self._btn_pay,
            self._btn_reopen,
        ):
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)
        self._tabs.addTab(tab, "Hóa đơn")

    def _reload_stay(self) -> None:
        try:
            self._stay = pet_boarding_service.get_workspace_stay(self._pet.id)
        except BoardingError as exc:
            QMessageBox.warning(self, "Chăm sóc", str(exc))
            self._stay = None
        self._stay_id = int(self._stay["id"]) if self._stay else None
        self._refresh_header()
        self._refresh_actions_enabled()
        self._refresh_history()
        self._refresh_invoice_tab()
        self._refresh_billing_summary()

    def _refresh_header(self) -> None:
        owner = self._customers_lookup.get(self._pet.customer_id, "")
        if self._stay:
            st = self._stay.get("status", "")
            label = STAY_STATUS_LABEL.get(st, st)
            self._header.setText(
                f"🐾 {self._pet.name}  ·  {self._pet.species}  ·  Chủ: {owner}\n"
                f"Đợt #{self._stay_id} — {label}"
            )
            ci = _fmt_dt(self._stay.get("check_in_at"))
            co = _fmt_dt(self._stay.get("expected_check_out_at"))
            emp = self._stay.get("employee_name") or "Chưa gán"
            rate = self._stay.get("daily_rate") or 0
            self._stay_info.setText(
                f"Nhận: {ci}\nDự kiến trả: {co}\nNV: {emp}\nGiá/ngày: {_fmt_money(rate)}"
            )
            colors = {
                "DANG_CHAM_SOC": ("#FEF3C7", "#B45309"),
                "KHACH_DA_NHAN": ("#DCFCE7", "#15803D"),
                "HUY": ("#FEE2E2", "#B91C1C"),
            }
            bg, fg = colors.get(st, ("#E2E8F0", "#334155"))
            self._status_badge.setText(label)
            self._status_badge.setStyleSheet(
                f"padding:8px; border-radius:8px; font-weight:700; "
                f"background:{bg}; color:{fg};"
            )
        else:
            self._header.setText(
                f"🐾 {self._pet.name}  ·  {self._pet.species}  ·  Chủ: {owner}\n"
                "Chưa có đợt chăm sóc đang diễn ra"
            )
            self._stay_info.setText("Nhấn «Nhận thú» để bắt đầu giao thú cho shop chăm sóc.")
            self._status_badge.setText("Chưa nhận")
            self._status_badge.setStyleSheet(
                "padding:8px; border-radius:8px; font-weight:700; "
                "background:#F1F5F9; color:#64748B;"
            )

    def _refresh_actions_enabled(self) -> None:
        active = self._stay is not None and self._stay.get("status") == "DANG_CHAM_SOC"
        self._btn_checkin.setEnabled(not active)
        for btn in (
            self._btn_employee,
            self._btn_feed,
            self._btn_care_svc,
            self._btn_video,
            self._btn_pickup,
        ):
            btn.setEnabled(active)

    def _refresh_history(self) -> None:
        logs = pet_boarding_service.get_care_history(self._pet.id)
        self._history_table.setRowCount(len(logs))
        for r, lg in enumerate(logs):
            self._history_table.setItem(r, 0, QTableWidgetItem(_fmt_dt(lg.get("created_at"))))
            lt = LOG_TYPE_LABEL.get(lg.get("log_type", ""), lg.get("log_type", ""))
            self._history_table.setItem(r, 1, QTableWidgetItem(str(lt)))
            self._history_table.setItem(
                r, 2, QTableWidgetItem(self._format_log_content(lg))
            )
            self._history_table.setItem(
                r, 3, QTableWidgetItem(str(lg.get("employee_name") or "—"))
            )

        media = []
        if self._stay_id:
            from src.petcare_backend.dao import pet_care_media_dao

            media = pet_care_media_dao.list_by_stay(self._stay_id)
        self._media_list.setRowCount(len(media))
        for r, m in enumerate(media):
            self._media_list.setItem(r, 0, QTableWidgetItem(str(m.get("media_type", ""))))
            self._media_list.setItem(r, 1, QTableWidgetItem(str(m.get("caption") or "")))
            path_item = QTableWidgetItem(str(m.get("file_path", "")))
            path_item.setData(Qt.ItemDataRole.UserRole, m.get("file_path"))
            self._media_list.setItem(r, 2, path_item)

    def _refresh_invoice_tab(self) -> None:
        inv = None
        if self._stay_id:
            inv = invoice_dao.get_by_pet_stay(self._stay_id)
            if inv is not None:
                try:
                    invoice_service.sync_invoice_totals(int(inv["id"]))
                    inv = invoice_dao.get_by_pet_stay(self._stay_id)
                except Exception:
                    pass
        if inv is None:
            self._inv_summary.setText("Chưa có hóa đơn cho đợt chăm sóc này.")
            self._inv_hint.setText(
                "Bấm «Tạo hóa đơn lưu trú» để lập HĐ (tính theo ngày nếu đã đặt giá/ngày). "
                "Sau đó dùng «+ Thêm dịch vụ / sản phẩm» hoặc ghi «Cho ăn» / «Dịch vụ» ở tab Tổng quan."
            )
            self._inv_items.setRowCount(0)
            has_stay = self._stay_id is not None
            self._btn_create_inv.setEnabled(has_stay)
            self._btn_add_svc.setEnabled(False)
            self._btn_add_prod.setEnabled(False)
            self._btn_del_line.setEnabled(False)
            self._btn_pay.setEnabled(False)
            self._btn_reopen.setEnabled(False)
            return

        status_code = str(inv.get("payment_status") or "CHUA_TT")
        status_lbl = PAYMENT_STATUS_LABEL.get(status_code, status_code)
        paid = status_code == "DA_TT"

        self._inv_summary.setText(
            f"Số HĐ: {inv.get('invoice_no')}  ·  Tổng: {_fmt_money(inv.get('total_amount'))}  ·  "
            f"{status_lbl}"
        )
        if paid:
            self._inv_hint.setText(
                "Hóa đơn đã thanh toán — không thể thêm/xóa dòng. "
                "Nếu bấm nhầm, dùng «Mở lại chỉnh sửa HĐ»."
            )
        else:
            self._inv_hint.setText(
                "Chọn một dòng trong bảng (nhấn vào dòng) rồi có thể «Xóa dòng đã chọn». "
                "Thêm dịch vụ/sản phẩm bằng các nút bên dưới, sau đó «Xác nhận thanh toán»."
            )

        items = invoice_item_dao.list_by_invoice(int(inv["id"]))
        self._inv_items.setRowCount(len(items))
        for r, it in enumerate(items):
            name = it.get("item_name") or it.get("service_name") or it.get("product_name") or "—"
            qty = int(it.get("quantity") or 0)
            price = float(it.get("unit_price") or 0)
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole, int(it["id"]))
            self._inv_items.setItem(r, 0, name_item)
            self._inv_items.setItem(r, 1, QTableWidgetItem(str(qty)))
            self._inv_items.setItem(r, 2, QTableWidgetItem(_fmt_money(price)))
            self._inv_items.setItem(r, 3, QTableWidgetItem(_fmt_money(qty * price)))

        self._btn_create_inv.setEnabled(False)
        self._btn_add_svc.setEnabled(not paid)
        self._btn_add_prod.setEnabled(not paid)
        self._btn_del_line.setEnabled(not paid and len(items) > 0)
        self._btn_pay.setEnabled(not paid and len(items) > 0)
        self._btn_reopen.setEnabled(paid)

    def _refresh_billing_summary(self) -> None:
        if not self._stay_id:
            self._bill_lines.setText("Chưa có đợt chăm sóc.")
            return
        inv = invoice_dao.get_by_pet_stay(self._stay_id)
        if inv is None:
            rate = self._stay.get("daily_rate") if self._stay else 0
            self._bill_lines.setText(
                f"Tiền lưu trú/ngày: {_fmt_money(rate)}\n"
                "Chưa lập hóa đơn — mở tab Hóa đơn để tạo."
            )
            return
        items = invoice_item_dao.list_by_invoice(int(inv["id"]))
        lines = [
            f"Tổng HĐ: {_fmt_money(inv.get('total_amount'))}",
            f"Trạng thái: {inv.get('payment_status')}",
            "—" * 20,
        ]
        for it in items[:6]:
            nm = it.get("item_name") or "—"
            lines.append(
                f"{nm}: {it.get('quantity')} x {_fmt_money(it.get('unit_price'))}"
            )
        if len(items) > 6:
            lines.append(f"... và {len(items) - 6} dòng khác")
        self._bill_lines.setText("\n".join(lines))

    def _on_save_pet_info(self) -> None:
        try:
            age_val = int(self._age_spin.value())
            pet_service.update_pet(
                self._pet.id,
                self._pet.customer_id,
                self._name_edit.text(),
                self._species_edit.text(),
                self._breed_edit.text(),
                age_val if age_val > 0 else None,
                health_note=self._health_edit.toPlainText(),
            )
            row = pet_dao.get_by_id(self._pet.id)
            if row:
                self._pet = Pet(
                    id=row["id"],
                    customer_id=row["customer_id"],
                    name=row["name"],
                    species=row["species"],
                    breed=row.get("breed"),
                    age=row.get("age"),
                    gender=row.get("gender"),
                    health_note=row.get("health_note"),
                )
        except PetError as exc:
            QMessageBox.warning(self, "Lưu", str(exc))
            return
        QMessageBox.information(self, "Lưu", "Đã cập nhật thông tin thú cưng.")
        self._refresh_header()

    def _on_check_in(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Nhận thú vào chăm sóc")
        form = QFormLayout(dlg)
        emp_combo = QComboBox()
        emp_combo.addItem("— Chưa gán —", None)
        for e in self._employees:
            emp_combo.addItem(e.full_name, e.id)
        rate_spin = QDoubleSpinBox()
        rate_spin.setRange(0, 10_000_000)
        rate_spin.setDecimals(0)
        rate_spin.setSuffix(" đ/ngày")
        rate_spin.setValue(150000)
        checkout = QDateTimeEdit()
        checkout.setCalendarPopup(True)
        checkout.setDateTime(checkout.dateTime().addDays(3))
        note = QLineEdit()
        form.addRow("NV phụ trách", emp_combo)
        form.addRow("Giá lưu trú/ngày", rate_spin)
        form.addRow("Dự kiến trả", checkout)
        form.addRow("Ghi chú", note)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            pet_boarding_service.check_in(
                self._pet.id,
                employee_id=emp_combo.currentData(),
                expected_check_out_at=checkout.dateTime().toPyDateTime(),
                daily_rate=float(rate_spin.value()),
                note=note.text(),
            )
        except BoardingError as exc:
            QMessageBox.warning(self, "Nhận thú", str(exc))
            return
        self._reload_stay()
        QMessageBox.information(self, "Nhận thú", "Đã nhận thú vào chăm sóc.")

    def _on_assign_employee(self) -> None:
        if not self._stay_id:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Gán nhân viên chăm sóc")
        combo = QComboBox()
        combo.addItem("— Chưa gán —", None)
        for e in self._employees:
            combo.addItem(e.full_name, e.id)
        cur = self._stay.get("employee_id") if self._stay else None
        idx = combo.findData(cur)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        form = QFormLayout(dlg)
        form.addRow("Nhân viên", combo)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        eid = combo.currentData()
        try:
            pet_boarding_service.assign_employee(
                self._stay_id, eid, employee_name=combo.currentText()
            )
        except BoardingError as exc:
            QMessageBox.warning(self, "Nhân viên", str(exc))
            return
        self._reload_stay()

    @staticmethod
    def _format_log_content(lg: dict) -> str:
        base = str(lg.get("content") or "")
        if lg.get("product_name"):
            return base
        if lg.get("service_name"):
            return base
        return base

    def _pick_image_paths(self, parent: QWidget) -> list[str]:
        paths, _ = QFileDialog.getOpenFileNames(
            parent,
            "Chọn ảnh (có thể chọn nhiều)",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        return [p for p in paths if p]

    def _build_photo_picker(self, parent: QDialog) -> tuple[QWidget, list[str]]:
        """Khối chọn nhiều ảnh (nút + danh sách). Trả về (widget, list đường dẫn)."""
        stored: list[str] = []
        box = QWidget()
        box_lay = QVBoxLayout(box)
        box_lay.setContentsMargins(0, 0, 0, 0)
        box_lay.setSpacing(8)

        list_w = QListWidget()
        list_w.setMinimumHeight(72)
        list_w.setMaximumHeight(120)
        list_w.setStyleSheet(
            "QListWidget { border:1px solid #CBD5E1; border-radius:8px; background:#FFFFFF; }"
        )
        count_lbl = QLabel("Chưa chọn ảnh — bấm «Chọn ảnh» bên dưới")
        count_lbl.setStyleSheet("color:#64748B; font-size:9pt;")

        def _refresh_list() -> None:
            list_w.clear()
            for p in stored:
                list_w.addItem(os.path.basename(p))
            count_lbl.setText(
                f"Đã chọn {len(stored)} ảnh" if stored else "Chưa chọn ảnh — bấm «Chọn ảnh» bên dưới"
            )

        btn_row = QHBoxLayout()
        btn_add = QPushButton("📷  Chọn ảnh")
        btn_add.setObjectName("PrimaryButton")
        btn_add.setMinimumHeight(36)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rm = QPushButton("Xóa ảnh đã chọn")
        btn_rm.setObjectName("GhostButton")
        btn_rm.setMinimumHeight(36)
        btn_rm.setCursor(Qt.CursorShape.PointingHandCursor)

        def _add_images() -> None:
            picked = self._pick_image_paths(parent)
            if picked:
                stored.extend(picked)
                _refresh_list()

        btn_add.clicked.connect(_add_images)

        def _remove() -> None:
            row_idx = list_w.currentRow()
            if 0 <= row_idx < len(stored):
                stored.pop(row_idx)
                _refresh_list()
            elif stored:
                QMessageBox.information(parent, "Ảnh", "Chọn một ảnh trong danh sách để xóa.")

        btn_rm.clicked.connect(_remove)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_rm)
        btn_row.addStretch()

        box_lay.addWidget(list_w)
        box_lay.addWidget(count_lbl)
        box_lay.addLayout(btn_row)
        return box, stored

    def _on_feeding_with_product(self) -> None:
        if not self._stay_id:
            return
        products = product_service.list_products(active_only=True, category="DO_AN")
        if not products:
            products = product_service.list_products(active_only=True)
        if not products:
            QMessageBox.warning(
                self, "Cho ăn", "Chưa có sản phẩm trong shop. Thêm đồ ăn ở trang Sản phẩm."
            )
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Cho ăn — chọn đồ ăn trong shop")
        dlg.setMinimumWidth(480)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        combo = QComboBox()
        for p in products:
            cat = "Đồ ăn" if p.category == "DO_AN" else "SP"
            combo.addItem(
                f"{p.name} ({cat}) — {_fmt_money(p.price)} · Tồn: {p.stock}",
                p.id,
            )
        qty = QSpinBox()
        qty.setRange(1, 999)
        qty.setValue(1)
        note = QLineEdit()
        note.setPlaceholderText("Ghi chú thêm (tuỳ chọn)")
        form.addRow("Đồ ăn *", combo)
        form.addRow("Số lượng *", qty)
        form.addRow("Ghi chú", note)
        lay.addLayout(form)
        lay.addWidget(QLabel("Ảnh bữa ăn:"))
        photo_box, paths = self._build_photo_picker(dlg)
        lay.addWidget(photo_box)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            pet_boarding_service.record_feeding(
                self._stay_id,
                int(combo.currentData()),
                int(qty.value()),
                note.text(),
                paths,
            )
        except BoardingError as exc:
            QMessageBox.warning(self, "Cho ăn", str(exc))
            return
        self._reload_stay()
        QMessageBox.information(
            self,
            "Cho ăn",
            f"Đã ghi nhận {combo.currentText().split(' — ')[0]} × {qty.value()}"
            + (f" ({len(paths)} ảnh)" if paths else ""),
        )

    def _on_care_service_with_photos(self) -> None:
        if not self._stay_id:
            return
        services = service_service.list_services(active_only=True)
        if not services:
            QMessageBox.warning(self, "Dịch vụ", "Chưa có dịch vụ trong hệ thống.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Dịch vụ chăm sóc + ảnh")
        dlg.setMinimumWidth(480)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        combo = QComboBox()
        for s in services:
            combo.addItem(f"{s.name} — {_fmt_money(s.price)}", s.id)
        qty = QSpinBox()
        qty.setRange(1, 99)
        qty.setValue(1)
        note = QLineEdit()
        note.setPlaceholderText("Ghi chú (tuỳ chọn)")
        form.addRow("Dịch vụ *", combo)
        form.addRow("Số lượng", qty)
        form.addRow("Ghi chú", note)
        lay.addLayout(form)
        lay.addWidget(QLabel("Ảnh sau khi chăm sóc:"))
        photo_box, paths = self._build_photo_picker(dlg)
        lay.addWidget(photo_box)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            pet_boarding_service.record_care_service(
                self._stay_id,
                int(combo.currentData()),
                int(qty.value()),
                note.text(),
                paths,
            )
        except BoardingError as exc:
            QMessageBox.warning(self, "Dịch vụ", str(exc))
            return
        self._reload_stay()
        QMessageBox.information(
            self,
            "Dịch vụ",
            f"Đã ghi nhận dịch vụ × {qty.value()}"
            + (f" ({len(paths)} ảnh)" if paths else ""),
        )

    def _on_upload_media(self, media_type: str) -> None:
        if not self._stay_id:
            return
        if media_type == "IMAGE":
            path, _ = QFileDialog.getOpenFileName(
                self, "Chọn ảnh", "", "Images (*.png *.jpg *.jpeg *.webp)"
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Chọn video", "", "Video (*.mp4 *.mov *.avi *.mkv)"
            )
        if not path:
            return
        cap, ok = self._input_dialog("Mô tả", "Chú thích (tuỳ chọn):", required=False)
        if not ok:
            return
        try:
            log_id = pet_boarding_service.add_feeding_log(
                self._stay_id, f"Tải {'ảnh' if media_type == 'IMAGE' else 'video'}: {cap or path}"
            )
            pet_boarding_service.add_media(
                self._stay_id, path, media_type, cap or None, care_log_id=log_id
            )
        except BoardingError as exc:
            QMessageBox.warning(self, "Tải file", str(exc))
            return
        self._reload_stay()
        QMessageBox.information(self, "Tải file", "Đã lưu file.")

    def _on_pickup(self) -> None:
        if not self._stay_id:
            return
        ans = QMessageBox.question(
            self,
            "Khách nhận thú",
            "Xác nhận khách hàng đã nhận lại thú cưng?",
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            pet_boarding_service.mark_picked_up(self._stay_id)
        except BoardingError as exc:
            QMessageBox.warning(self, "Trả thú", str(exc))
            return
        self._reload_stay()
        QMessageBox.information(self, "Trả thú", "Đã cập nhật: khách đã nhận thú.")

    def _on_create_invoice(self) -> None:
        if not self._stay_id:
            return
        try:
            pet_boarding_service.create_stay_invoice(self._stay_id)
        except BoardingError as exc:
            QMessageBox.warning(self, "Hóa đơn", str(exc))
            return
        self._refresh_invoice_tab()
        self._refresh_billing_summary()

    def _on_remove_invoice_line(self) -> None:
        row = self._inv_items.currentRow()
        if row < 0:
            QMessageBox.information(self, "Hóa đơn", "Vui lòng chọn một dòng trong bảng trước.")
            return
        name_item = self._inv_items.item(row, 0)
        item_id = name_item.data(Qt.ItemDataRole.UserRole) if name_item else None
        if not isinstance(item_id, int):
            return
        ans = QMessageBox.question(
            self,
            "Xóa dòng",
            f"Xóa «{name_item.text()}» khỏi hóa đơn?",
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            invoice_service.remove_invoice_item(item_id)
        except invoice_service.InvoiceError as exc:
            QMessageBox.warning(self, "Hóa đơn", str(exc))
            return
        self._refresh_invoice_tab()
        self._refresh_billing_summary()

    def _on_reopen_invoice(self) -> None:
        if not self._stay_id:
            return
        ans = QMessageBox.question(
            self,
            "Mở lại hóa đơn",
            "Đặt hóa đơn về «Chưa thanh toán» để thêm/sửa dòng?\n"
            "(Không xóa lịch sử thanh toán đã ghi.)",
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            pet_boarding_service.reopen_stay_invoice(self._stay_id)
        except BoardingError as exc:
            QMessageBox.warning(self, "Hóa đơn", str(exc))
            return
        self._refresh_invoice_tab()
        self._refresh_billing_summary()
        QMessageBox.information(self, "Hóa đơn", "Đã mở lại chỉnh sửa hóa đơn.")

    def _on_add_service_to_invoice(self) -> None:
        if not self._stay_id:
            return
        svcs = service_service.list_services(active_only=True)
        if not svcs:
            QMessageBox.warning(self, "Dịch vụ", "Chưa có dịch vụ.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm dịch vụ vào hóa đơn")
        dlg.setMinimumWidth(400)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        combo = QComboBox()
        for s in svcs:
            combo.addItem(f"{s.name} — {_fmt_money(s.price)}", s.id)
        qty = QSpinBox()
        qty.setRange(1, 99)
        qty.setValue(1)
        form.addRow("Dịch vụ", combo)
        form.addRow("Số lượng", qty)
        lay.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            pet_boarding_service.add_service_to_stay_invoice(
                self._stay_id, int(combo.currentData()), int(qty.value())
            )
        except BoardingError as exc:
            QMessageBox.warning(self, "Hóa đơn", str(exc))
            return
        self._refresh_invoice_tab()
        self._refresh_billing_summary()

    def _on_add_product_to_invoice(self) -> None:
        if not self._stay_id:
            return
        prods = product_service.list_products(active_only=True)
        if not prods:
            QMessageBox.warning(self, "Sản phẩm", "Chưa có sản phẩm.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm sản phẩm vào hóa đơn")
        dlg.setMinimumWidth(400)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        combo = QComboBox()
        for p in prods:
            combo.addItem(f"{p.name} — {_fmt_money(p.price)}", p.id)
        qty = QSpinBox()
        qty.setRange(1, 99)
        form.addRow("Sản phẩm", combo)
        form.addRow("Số lượng", qty)
        lay.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            pet_boarding_service.add_product_to_stay_invoice(
                self._stay_id, int(combo.currentData()), int(qty.value())
            )
        except BoardingError as exc:
            QMessageBox.warning(self, "Hóa đơn", str(exc))
            return
        self._refresh_invoice_tab()
        self._refresh_billing_summary()

    def _on_mark_paid(self) -> None:
        inv = invoice_dao.get_by_pet_stay(self._stay_id) if self._stay_id else None
        if inv is None:
            return
        try:
            amounts = invoice_service.get_payment_amounts(int(inv["id"]))
        except invoice_service.InvoiceError as exc:
            QMessageBox.warning(self, "Thanh toán", str(exc))
            return
        remaining = amounts["remaining"]
        total = amounts["total"]
        paid = amounts["paid"]
        if int(remaining) <= 0:
            QMessageBox.information(self, "Thanh toán", "Hóa đơn đã thanh toán đủ.")
            return
        msg = f"Tổng HĐ: {_fmt_money(total)}"
        if int(paid) > 0:
            msg += f"\nĐã trả: {_fmt_money(paid)}"
        msg += f"\nCòn phải trả: {_fmt_money(remaining)}"
        msg += "\n\nXác nhận thanh toán phần còn lại?"
        ans = QMessageBox.question(self, "Thanh toán", msg)
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            payment_service.add_payment(
                int(inv["id"]),
                str(int(remaining)),
                "Tiền mặt",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Thanh toán", str(exc))
            return
        self._refresh_invoice_tab()
        self._refresh_billing_summary()
        QMessageBox.information(self, "Thanh toán", "Đã ghi nhận thanh toán.")

    def _on_open_selected_media(self) -> None:
        row = self._media_list.currentRow()
        if row < 0:
            return
        item = self._media_list.item(row, 2)
        path = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, "Mở file", "File không tồn tại.")
            return
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)

    def _input_dialog(
        self, title: str, label: str, *, required: bool = True
    ) -> tuple[str, bool]:
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        edit = QTextEdit()
        edit.setMaximumHeight(100)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(label))
        lay.addWidget(edit)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return "", False
        text = edit.toPlainText().strip()
        if required and not text:
            QMessageBox.warning(self, title, "Vui lòng nhập nội dung.")
            return "", False
        return text, True
