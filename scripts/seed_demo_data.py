"""Nạp thêm dữ liệu mẫu cho app (dashboard, bán lẻ, chăm sóc thú).

Chạy từ thư mục gốc project:
    python scripts/seed_demo_data.py           # thêm dữ liệu (bỏ qua nếu đã có)
    python scripts/seed_demo_data.py --reset   # xóa dữ liệu DEMO rồi nạp lại
    python scripts/seed_demo_data.py --force   # nạp lại (xóa DEMO trước)

Dữ liệu được đánh dấu:
  - Hóa đơn: invoice_no bắt đầu bằng DEMO-
  - Khách hàng demo: SĐT 0999xxxxxx
  - Đợt chăm sóc: note chứa [DEMO]
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from petcare_backend.config import DB_CONFIG  # noqa: E402
from petcare_backend.security import hash_password  # noqa: E402

DEMO_INVOICE_PREFIX = "DEMO-"
DEMO_PRODUCT_SKU_PREFIX = "DEMO-"
DEMO_EMPLOYEE_PREFIX = "demo_"
DEMO_EMPLOYEE_PASSWORD = "123456"
DEMO_PHONES = (
    "0999000001",  # Quảng Duy Thái
    "0999000002",  # Phạm Thị Dung
    "0999000003",  # Hoàng Văn Em
)

# (username, full_name, phone) — đăng nhập: demo_nv02 … / mật khẩu 123456
DEMO_EMPLOYEES: tuple[tuple[str, str, str], ...] = (
    ("demo_nv02", "Trần Thị Mai", "0922222202"),
    ("demo_nv03", "Lê Văn Bình", "0922222203"),
    ("demo_nv04", "Phạm Thu Hà", "0922222204"),
    ("demo_nv05", "Hoàng Minh Tuấn", "0922222205"),
    ("demo_nv06", "Võ Thị Lan", "0922222206"),
    ("demo_nv07", "Đặng Quốc Huy", "0922222207"),
    ("demo_nv08", "Bùi Ngọc Anh", "0922222208"),
    ("demo_nv09", "Nguyễn Thanh Phúc", "0922222209"),
    ("demo_nv10", "Đỗ Kim Chi", "0922222210"),
)

# (name, category, sku, price, stock, description)
DEMO_PRODUCTS: tuple[tuple[str, str, str, int, int, str], ...] = (
    # Đồ ăn
    ("Hạt SmartHeart Puppy 1kg", "DO_AN", "DEMO-FOOD-001", 185000, 45, "Hạt cho chó con dưới 12 tháng"),
    ("Hạt Catrice Adult 500g", "DO_AN", "DEMO-FOOD-002", 95000, 60, "Hạt cho mèo trưởng thành"),
    ("Pate Cesar vị bò 100g", "DO_AN", "DEMO-FOOD-003", 22000, 150, "Pate cho chó nhỏ"),
    ("Xương gặm Orgo 5 cây", "DO_AN", "DEMO-FOOD-004", 35000, 90, "Xương gặm làm sạch răng"),
    ("Sữa bột Bio Milk 200g", "DO_AN", "DEMO-FOOD-005", 78000, 40, "Sữa bột cho chó mèo con"),
    ("Hạt Me-O cá ngừ 1.2kg", "DO_AN", "DEMO-FOOD-006", 125000, 55, "Hạt cho mèo vị cá ngừ"),
    ("Pate Ganador vị gà 400g", "DO_AN", "DEMO-FOOD-007", 42000, 70, "Pate cho mèo vị gà"),
    ("Thức ăn khô Kitten 400g", "DO_AN", "DEMO-FOOD-008", 68000, 65, "Hạt cho mèo con"),
    ("Snack thịt khô vị vịt 80g", "DO_AN", "DEMO-FOOD-009", 55000, 100, "Snack tự nhiên cho chó"),
    ("Hạt Pro Plan Sensitive 1.5kg", "DO_AN", "DEMO-FOOD-010", 320000, 25, "Hạt cho chó da nhạy cảm"),
    # Phụ kiện
    ("Nệm ngủ size L", "PHU_KIEN", "DEMO-ACC-001", 280000, 15, "Nệm êm chống trượt"),
    ("Khay vệ sinh mèo có nắp", "PHU_KIEN", "DEMO-ACC-002", 165000, 20, "Khay vệ sinh kèm xẻng"),
    ("Đồ chơi chuột catnip", "PHU_KIEN", "DEMO-ACC-003", 35000, 80, "Đồ chơi kích thích mèo"),
    ("Áo mưa chó size S", "PHU_KIEN", "DEMO-ACC-004", 120000, 30, "Áo mưa phản quang"),
    ("Bàn chải lông đôi", "PHU_KIEN", "DEMO-ACC-005", 75000, 50, "Chải lông mềm 2 mặt"),
    ("Chuồng sắt size L", "PHU_KIEN", "DEMO-ACC-006", 520000, 6, "Chuồng sắt có khay hứng"),
    ("Túi đeo chó nhỏ", "PHU_KIEN", "DEMO-ACC-007", 195000, 18, "Túi vải đeo ngực"),
    ("Khay nước tự động 2L", "PHU_KIEN", "DEMO-ACC-008", 145000, 22, "Bình nước tự rót"),
    ("Xương cao su nhai", "PHU_KIEN", "DEMO-ACC-009", 48000, 75, "Đồ nhai an toàn cho chó"),
    ("Quần áo Noel size M", "PHU_KIEN", "DEMO-ACC-010", 89000, 35, "Trang phục lễ cho thú cưng"),
    ("Vòng cổ có chuông size S", "PHU_KIEN", "DEMO-ACC-011", 45000, 60, "Vòng nylon có chuông"),
    ("Dây dắt da 1.2m", "PHU_KIEN", "DEMO-ACC-012", 110000, 28, "Dây dắt da thật"),
)


def _connect():
    return mysql.connector.connect(
        host=DB_CONFIG.host,
        port=DB_CONFIG.port,
        user=DB_CONFIG.user,
        password=DB_CONFIG.password,
        database=DB_CONFIG.database,
        charset="utf8mb4",
        autocommit=False,
    )


def _scalar(cur, sql: str, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def clear_demo_data(cur) -> None:
    """Xóa dữ liệu demo (theo marker), giữ nguyên seed gốc."""
    inv_ids = []
    cur.execute(
        "SELECT id FROM invoice WHERE invoice_no LIKE %s",
        (f"{DEMO_INVOICE_PREFIX}%",),
    )
    inv_ids = [r[0] for r in cur.fetchall()]

    if inv_ids:
        placeholders = ",".join(["%s"] * len(inv_ids))
        cur.execute(f"DELETE FROM payment WHERE invoice_id IN ({placeholders})", inv_ids)
        cur.execute(
            f"DELETE FROM invoice_item WHERE invoice_id IN ({placeholders})",
            inv_ids,
        )
        cur.execute(f"DELETE FROM invoice WHERE id IN ({placeholders})", inv_ids)

    cur.execute("SELECT id FROM pet_stay WHERE note LIKE %s", ("%[DEMO]%",))
    stay_ids = [r[0] for r in cur.fetchall()]
    if stay_ids:
        ph = ",".join(["%s"] * len(stay_ids))
        cur.execute(f"DELETE FROM pet_care_media WHERE stay_id IN ({ph})", stay_ids)
        cur.execute(f"DELETE FROM pet_care_log WHERE stay_id IN ({ph})", stay_ids)
        cur.execute(f"DELETE FROM pet_stay WHERE id IN ({ph})", stay_ids)

    cur.execute("SELECT id FROM appointment WHERE note LIKE %s", ("%[DEMO]%",))
    appt_ids = [r[0] for r in cur.fetchall()]
    if appt_ids:
        ph = ",".join(["%s"] * len(appt_ids))
        cur.execute(f"DELETE FROM appointment_service WHERE appointment_id IN ({ph})", appt_ids)
        cur.execute(f"DELETE FROM appointment WHERE id IN ({ph})", appt_ids)

    cur.execute("SELECT id FROM pet WHERE health_note LIKE %s", ("%[DEMO]%",))
    pet_ids = [r[0] for r in cur.fetchall()]
    if pet_ids:
        ph = ",".join(["%s"] * len(pet_ids))
        cur.execute(f"DELETE FROM pet WHERE id IN ({ph})", pet_ids)

    cur.execute(
        "SELECT id FROM customer WHERE phone IN (" + ",".join(["%s"] * len(DEMO_PHONES)) + ")",
        DEMO_PHONES,
    )
    cust_ids = [r[0] for r in cur.fetchall()]
    if cust_ids:
        ph = ",".join(["%s"] * len(cust_ids))
        cur.execute(f"DELETE FROM customer WHERE id IN ({ph})", cust_ids)

    cur.execute(
        "DELETE FROM user WHERE username LIKE %s",
        (f"{DEMO_EMPLOYEE_PREFIX}%",),
    )
    cur.execute(
        "DELETE FROM product WHERE sku LIKE %s",
        (f"{DEMO_PRODUCT_SKU_PREFIX}%",),
    )


def seed_demo_catalog(cur) -> tuple[dict[str, int], dict[str, int]]:
    """Thêm/cập nhật nhân viên và sản phẩm mẫu (idempotent)."""
    role_id = _scalar(cur, "SELECT id FROM role WHERE name = 'EMPLOYEE' LIMIT 1")
    if role_id is None:
        raise RuntimeError("Thiếu role EMPLOYEE — chạy init_db.py trước.")
    role_id = int(role_id)
    pw_hash = hash_password(DEMO_EMPLOYEE_PASSWORD)

    emp_ids: dict[str, int] = {}
    for username, full_name, phone in DEMO_EMPLOYEES:
        uid = _scalar(cur, "SELECT id FROM user WHERE username = %s", (username,))
        if uid:
            cur.execute(
                "UPDATE user SET full_name=%s, phone=%s, role_id=%s, is_active=1 WHERE id=%s",
                (full_name, phone, role_id, uid),
            )
            emp_ids[username] = int(uid)
        else:
            cur.execute(
                """
                INSERT INTO user (role_id, username, password_hash, full_name, phone, is_active)
                VALUES (%s, %s, %s, %s, %s, 1)
                """,
                (role_id, username, pw_hash, full_name, phone),
            )
            emp_ids[username] = int(cur.lastrowid)

    cur.execute(
        "UPDATE user SET full_name = %s WHERE username = 'nv01'",
        ("Nguyễn Văn A",),
    )
    nv01 = _scalar(cur, "SELECT id FROM user WHERE username = 'nv01' LIMIT 1")
    if nv01:
        emp_ids["nv01"] = int(nv01)

    sku_map: dict[str, int] = {}
    for name, category, sku, price, stock, desc in DEMO_PRODUCTS:
        pid = _product_id(cur, sku)
        if pid:
            cur.execute(
                """
                UPDATE product
                SET name=%s, category=%s, price=%s, stock=%s, description=%s, is_active=1
                WHERE id=%s
                """,
                (name, category, price, stock, desc, pid),
            )
            sku_map[sku] = int(pid)
        else:
            cur.execute(
                """
                INSERT INTO product (name, category, sku, price, stock, description, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, 1)
                """,
                (name, category, sku, price, stock, desc),
            )
            sku_map[sku] = int(cur.lastrowid)

    return emp_ids, sku_map


def _demo_exists(cur) -> bool:
    n = _scalar(
        cur,
        "SELECT COUNT(*) FROM invoice WHERE invoice_no LIKE %s",
        (f"{DEMO_INVOICE_PREFIX}%",),
    )
    return int(n or 0) > 0


def _product_id(cur, sku: str) -> int | None:
    return _scalar(cur, "SELECT id FROM product WHERE sku = %s LIMIT 1", (sku,))


def _service_id(cur, name: str) -> int | None:
    return _scalar(cur, "SELECT id FROM service WHERE name = %s LIMIT 1", (name,))


def _employee_id(cur) -> int:
    eid = _scalar(cur, "SELECT id FROM user WHERE username = 'nv01' LIMIT 1")
    if eid is None:
        raise RuntimeError("Không tìm thấy user nv01 — chạy init_db.py trước.")
    return int(eid)


def _upsert_customer(cur, phone: str, full_name: str, address: str) -> int:
    cid = _scalar(cur, "SELECT id FROM customer WHERE phone = %s", (phone,))
    if cid:
        cur.execute(
            "UPDATE customer SET full_name=%s, address=%s WHERE id=%s",
            (full_name, address, cid),
        )
        return int(cid)
    cur.execute(
        "INSERT INTO customer (full_name, phone, address, email) VALUES (%s,%s,%s,NULL)",
        (full_name, phone, address),
    )
    return int(cur.lastrowid)


def _insert_pet(
    cur,
    customer_id: int,
    name: str,
    species: str,
    breed: str,
    age: int,
    health_note: str,
) -> int:
    cur.execute(
        "INSERT INTO pet (customer_id, name, species, breed, age, gender, health_note) "
        "VALUES (%s,%s,%s,%s,%s,NULL,%s)",
        (customer_id, name, species, breed, age, health_note),
    )
    return int(cur.lastrowid)


def _insert_retail_invoice(
    cur,
    *,
    invoice_no: str,
    customer_id: int,
    issued_at: datetime,
    created_by: int,
    lines: list[tuple[int, int, Decimal]],
) -> int:
    total = sum(qty * price for _, qty, price in lines)
    cur.execute(
        """
        INSERT INTO invoice (
            appointment_id, pet_stay_id, customer_id, invoice_type, invoice_no, issued_at,
            subtotal_amount, discount_amount, tax_amount, total_amount,
            payment_status, created_by, note
        ) VALUES (NULL, NULL, %s, 'RETAIL', %s, %s, %s, 0, 0, %s, 'DA_TT', %s, %s)
        """,
        (
            customer_id,
            invoice_no,
            issued_at,
            total,
            total,
            created_by,
            "Dữ liệu mẫu — bán lẻ",
        ),
    )
    inv_id = int(cur.lastrowid)
    for product_id, qty, price in lines:
        cur.execute(
            """
            INSERT INTO invoice_item (
                invoice_id, service_id, product_id, item_type, pet_id, quantity, unit_price
            ) VALUES (%s, NULL, %s, 'PRODUCT', NULL, %s, %s)
            """,
            (inv_id, product_id, qty, price),
        )
    cur.execute(
        "INSERT INTO payment (invoice_id, amount, method, paid_at, created_by) "
        "VALUES (%s, %s, 'TIEN_MAT', %s, %s)",
        (inv_id, total, issued_at, created_by),
    )
    return inv_id


def _insert_service_invoice(
    cur,
    *,
    invoice_no: str,
    appointment_id: int,
    customer_id: int,
    pet_id: int,
    issued_at: datetime,
    created_by: int,
    lines: list[tuple[int, int, Decimal]],
) -> int:
    total = sum(qty * price for _, qty, price in lines)
    cur.execute(
        """
        INSERT INTO invoice (
            appointment_id, pet_stay_id, customer_id, invoice_type, invoice_no, issued_at,
            subtotal_amount, discount_amount, tax_amount, total_amount,
            payment_status, created_by, note
        ) VALUES (%s, NULL, %s, 'SERVICE', %s, %s, %s, 0, 0, %s, 'DA_TT', %s, %s)
        """,
        (
            appointment_id,
            customer_id,
            invoice_no,
            issued_at,
            total,
            total,
            created_by,
            "Dữ liệu mẫu — dịch vụ",
        ),
    )
    inv_id = int(cur.lastrowid)
    for service_id, qty, price in lines:
        cur.execute(
            """
            INSERT INTO invoice_item (
                invoice_id, service_id, product_id, item_type, pet_id, quantity, unit_price
            ) VALUES (%s, %s, NULL, 'SERVICE', %s, %s, %s)
            """,
            (inv_id, service_id, pet_id, qty, price),
        )
    cur.execute(
        "INSERT INTO payment (invoice_id, amount, method, paid_at, created_by) "
        "VALUES (%s, %s, 'TIEN_MAT', %s, %s)",
        (inv_id, total, issued_at, created_by),
    )
    return inv_id


def seed_demo_data(cur) -> None:
    emp_map, demo_sku = seed_demo_catalog(cur)
    emp_id = emp_map.get("nv01") or _employee_id(cur)
    all_emp_ids = list(emp_map.values())

    # --- Khách & thú ---
    c_thai = _upsert_customer(
        cur,
        DEMO_PHONES[0],
        "Quảng Duy Thái",
        "Q. Ninh Kiều, Cần Thơ",
    )
    c_dung = _upsert_customer(
        cur,
        DEMO_PHONES[1],
        "Phạm Thị Dung",
        "Q. Cái Răng, Cần Thơ",
    )
    c_em = _upsert_customer(
        cur,
        DEMO_PHONES[2],
        "Hoàng Văn Em",
        "Q. Bình Thuỷ, Cần Thơ",
    )

    pet_nutt = _insert_pet(
        cur, c_thai, "Nutt", "Chó", "Corgi", 2, "[DEMO] Thú demo — Nutt"
    )
    pet_milu = _insert_pet(
        cur, c_dung, "Milu", "Mèo", "Ba Tư", 3, "[DEMO] Thú demo — Milu"
    )
    pet_lucky = _insert_pet(
        cur, c_em, "Lucky", "Chó", "Golden", 4, "[DEMO] Thú demo — Lucky"
    )

    # Gộp sản phẩm seed gốc + DEMO (ưu tiên có đủ cho biểu đồ)
    sku_map = dict(demo_sku)
    for sku in (
        "RC-ADL-1KG",
        "WK-CA-80",
        "PD-STX",
        "CL-LE-M",
        "LS-NY-150",
        "CG-M",
        "BW-IN-2",
        "SH-BIO-250",
    ):
        pid = _product_id(cur, sku)
        if pid:
            sku_map[sku] = int(pid)

    svc_tam = _service_id(cur, "Tắm gội cơ bản")
    svc_cat = _service_id(cur, "Cắt tỉa lông")
    svc_vaccine = _service_id(cur, "Tiêm phòng (gói cơ bản)")
    svc_spa = _service_id(cur, "Spa thư giãn")
    for sid, label in [
        (svc_tam, "Tắm gội cơ bản"),
        (svc_cat, "Cắt tỉa lông"),
        (svc_vaccine, "Tiêm phòng (gói cơ bản)"),
        (svc_spa, "Spa thư giãn"),
    ]:
        if sid is None:
            raise RuntimeError(f"Thiếu dịch vụ: {label}")

    now = datetime.now().replace(second=0, microsecond=0)
    today = date.today()

    def _line(sku_key: str, qty: int, price: int) -> tuple[int, int, Decimal]:
        return (sku_map[sku_key], qty, Decimal(price))

    # --- Hóa đơn bán lẻ 7 ngày (biểu đồ dashboard, nhiều SP) ---
    retail_plan = [
        (
            6,
            [
                _line("DEMO-FOOD-009", 2, 55000),
                _line("DEMO-FOOD-003", 3, 22000),
                _line("DEMO-ACC-003", 1, 35000),
            ],
        ),
        (
            5,
            [
                _line("DEMO-FOOD-010", 1, 320000),
                _line("DEMO-FOOD-001", 1, 185000),
            ],
        ),
        (
            4,
            [
                _line("DEMO-ACC-006", 1, 520000),
                _line("DEMO-ACC-011", 2, 45000),
            ],
        ),
        (
            3,
            [
                _line("DEMO-FOOD-006", 2, 125000),
                _line("DEMO-ACC-008", 1, 145000),
            ],
        ),
        (
            2,
            [
                _line("DEMO-ACC-001", 1, 280000),
                _line("DEMO-ACC-005", 1, 75000),
            ],
        ),
        (
            1,
            [
                _line("DEMO-FOOD-007", 4, 42000),
                _line("DEMO-FOOD-004", 2, 35000),
                _line("DEMO-ACC-012", 1, 110000),
            ],
        ),
        (
            0,
            [
                _line("DEMO-FOOD-002", 3, 95000),
                _line("DEMO-ACC-009", 2, 48000),
                _line("DEMO-ACC-010", 1, 89000),
            ],
        ),
    ]
    for day_offset, lines in retail_plan:
        d = datetime.combine(today - timedelta(days=day_offset), datetime.min.time()).replace(
            hour=14, minute=30
        )
        cust = [c_thai, c_dung, c_em][day_offset % 3]
        creator = all_emp_ids[day_offset % len(all_emp_ids)]
        _insert_retail_invoice(
            cur,
            invoice_no=f"{DEMO_INVOICE_PREFIX}BL-{day_offset:02d}",
            customer_id=cust,
            issued_at=d,
            created_by=creator,
            lines=lines,
        )

    # --- Lịch hẹn + HĐ dịch vụ (cột doanh thu, top dịch vụ) ---
    appt_specs = [
        (3, c_thai, pet_nutt, svc_tam, Decimal("150000"), svc_cat, Decimal("200000")),
        (5, c_dung, pet_milu, svc_spa, Decimal("350000"), None, None),
        (1, c_em, pet_lucky, svc_vaccine, Decimal("500000"), None, None),
    ]
    for idx, (days_ago, cust_id, pet_id, s1, p1, s2, p2) in enumerate(appt_specs):
        scheduled = now - timedelta(days=days_ago, hours=2)
        appt_emp = all_emp_ids[idx % len(all_emp_ids)]
        cur.execute(
            """
            INSERT INTO appointment (customer_id, pet_id, employee_id, scheduled_at, status, note)
            VALUES (%s, %s, %s, %s, 'HOAN_THANH', %s)
            """,
            (cust_id, pet_id, appt_emp, scheduled, "[DEMO] Lịch hẹn mẫu"),
        )
        appt_id = int(cur.lastrowid)
        lines = [(s1, 1, p1)]
        if s2 and p2:
            lines.append((s2, 1, p2))
        for svc_id, qty, price in lines:
            cur.execute(
                """
                INSERT INTO appointment_service (appointment_id, service_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
                """,
                (appt_id, svc_id, qty, price),
            )
        _insert_service_invoice(
            cur,
            invoice_no=f"{DEMO_INVOICE_PREFIX}DV-{idx:02d}",
            appointment_id=appt_id,
            customer_id=cust_id,
            pet_id=pet_id,
            issued_at=scheduled + timedelta(hours=1),
            created_by=appt_emp,
            lines=lines,
        )

    # --- Đợt chăm sóc Nutt (màn Chăm sóc — Khách đã nhận) ---
    check_in = now - timedelta(days=8)
    check_out = now - timedelta(days=1)
    cur.execute(
        """
        INSERT INTO pet_stay (
            pet_id, customer_id, employee_id, check_in_at, expected_check_out_at,
            actual_check_out_at, status, daily_rate, note
        ) VALUES (%s, %s, %s, %s, %s, %s, 'KHACH_DA_NHAN', %s, %s)
        """,
        (
            pet_nutt,
            c_thai,
            emp_id,
            check_in,
            check_in + timedelta(days=7),
            check_out,
            Decimal("150000"),
            "[DEMO] Đợt chăm sóc Nutt — khách đã nhận",
        ),
    )
    stay_id = int(cur.lastrowid)

    cur.execute(
        """
        INSERT INTO pet_care_log (stay_id, employee_id, log_type, content, product_id, quantity)
        VALUES (%s, %s, 'FEEDING', %s, %s, 2)
        """,
        (stay_id, emp_id, "Cho ăn: Snack Pedigree Dentastix × 2", sku_map["PD-STX"]),
    )
    cur.execute(
        """
        INSERT INTO pet_care_log (stay_id, employee_id, log_type, content, service_id, quantity)
        VALUES (%s, %s, 'CARE', %s, %s, 1)
        """,
        (stay_id, emp_id, "Tiêm phòng (gói cơ bản)", svc_vaccine),
    )

    # Hóa đơn lưu trú Nutt (tổng 240.000đ như màn hình mẫu)
    stay_lines: list[tuple[str, int | None, int | None, int, Decimal]] = [
        ("PRODUCT", None, sku_map["PD-STX"], 2, Decimal("45000")),
        ("SERVICE", svc_vaccine, None, 1, Decimal("150000")),
    ]
    stay_total = sum(qty * price for _, _, _, qty, price in stay_lines)
    cur.execute(
        """
        INSERT INTO invoice (
            appointment_id, pet_stay_id, customer_id, invoice_type, invoice_no, issued_at,
            subtotal_amount, discount_amount, tax_amount, total_amount,
            payment_status, created_by, note
        ) VALUES (NULL, %s, %s, 'SERVICE', %s, %s, %s, 0, 0, %s, 'DA_TT', %s, %s)
        """,
        (
            stay_id,
            c_thai,
            f"{DEMO_INVOICE_PREFIX}LT-NUTT-01",
            check_out,
            stay_total,
            stay_total,
            emp_id,
            "[DEMO] Hóa đơn lưu trú Nutt",
        ),
    )
    inv_stay = int(cur.lastrowid)
    for item_type, svc_id, prod_id, qty, price in stay_lines:
        cur.execute(
            """
            INSERT INTO invoice_item (
                invoice_id, service_id, product_id, item_type, pet_id, quantity, unit_price
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (inv_stay, svc_id, prod_id, item_type, pet_nutt, qty, price),
        )
    cur.execute(
        "INSERT INTO payment (invoice_id, amount, method, paid_at, created_by) "
        "VALUES (%s, %s, 'TIEN_MAT', %s, %s)",
        (inv_stay, stay_total, check_out, emp_id),
    )

    # --- Lịch hẹn sắp tới ---
    cur.execute(
        """
        INSERT INTO appointment (customer_id, pet_id, employee_id, scheduled_at, status, note)
        VALUES (%s, %s, %s, %s, 'CHO_XU_LY', %s)
        """,
        (c_thai, pet_nutt, emp_id, now + timedelta(days=2), "[DEMO] Lịch hẹn sắp tới"),
    )
    appt_future = int(cur.lastrowid)
    cur.execute(
        "INSERT INTO appointment_service (appointment_id, service_id, quantity, unit_price) "
        "VALUES (%s, %s, 1, %s)",
        (appt_future, svc_tam, Decimal("150000")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Nạp dữ liệu mẫu Pet Care")
    parser.add_argument(
        "--reset",
        "--force",
        action="store_true",
        dest="reset",
        help="Xóa dữ liệu DEMO cũ rồi nạp lại",
    )
    parser.add_argument(
        "--catalog-only",
        action="store_true",
        help="Chỉ thêm/cập nhật nhân viên và sản phẩm mẫu (không tạo HĐ/lịch hẹn)",
    )
    args = parser.parse_args()

    conn = _connect()
    try:
        cur = conn.cursor()
        if args.reset:
            print("[*] Xóa dữ liệu DEMO cũ...")
            clear_demo_data(cur)
            conn.commit()

        if args.catalog_only:
            print("[*] Đang nạp nhân viên + sản phẩm mẫu...")
            emp_map, sku_map = seed_demo_catalog(cur)
            conn.commit()
            print(f"[+] {len(emp_map)} nhân viên, {len(sku_map)} sản phẩm DEMO.")
            print(f"    NV demo: {DEMO_EMPLOYEE_PREFIX}nv02 … — mật khẩu {DEMO_EMPLOYEE_PASSWORD}")
            return 0

        if not args.reset and _demo_exists(cur):
            print("[*] Đã có HĐ DEMO — chỉ cập nhật nhân viên & sản phẩm...")
            emp_map, sku_map = seed_demo_catalog(cur)
            conn.commit()
            print(f"[+] {len(emp_map)} nhân viên, {len(sku_map)} sản phẩm.")
            print("    Muốn nạp lại toàn bộ: python scripts/seed_demo_data.py --reset")
            return 0

        print("[*] Đang nạp dữ liệu mẫu...")
        seed_demo_data(cur)
        conn.commit()
        print("[+] Hoàn tất. Trang Sản phẩm / Nhân viên / Trang chủ đã có thêm dữ liệu.")
        print("    admin / admin123  |  nv01 / 123456  |  demo_nv02 … / 123456")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"[!] Lỗi: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
