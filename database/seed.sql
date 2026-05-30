-- =====================================================================
-- PET CARE MANAGEMENT - Seed data
-- Chay SAU khi da chay schema.sql
-- Mat khau mac dinh:
--   admin / admin123
--   nv01  / 123456
-- (password_hash duoc tao bang bcrypt - se sinh lai bang Python khi can)
-- =====================================================================

USE petcare_db;

-- ---------- role ----------
INSERT INTO role (id, name, description) VALUES
    (1, 'ADMIN',    'Quan tri he thong'),
    (2, 'EMPLOYEE', 'Nhan vien');

-- ---------- user ----------
-- LUU Y: password_hash ben duoi la bcrypt cua 'admin123' va '123456'
-- (cost=12). Ban co the re-generate bang script seed_users.py.
INSERT INTO user (role_id, username, password_hash, full_name, phone, is_active) VALUES
    (1, 'admin', '$2b$12$u1m5T7vH4M3xTqj3O2J1eOYxC2ZkQmV.QoA1h1o0yGk2cM2o2eXfW', 'Quản trị viên', '0900000000', 1),
    (2, 'nv01',  '$2b$12$QyLXx0b/2Q6p0W3G8j9cAO5f8wQkXeG7k6u9bJ4t7Y.s4b8aZhG5K', 'Nguyễn Văn A', '0911111111', 1),
    (2, 'demo_nv02', '$2b$12$QyLXx0b/2Q6p0W3G8j9cAO5f8wQkXeG7k6u9bJ4t7Y.s4b8aZhG5K', 'Trần Thị Mai', '0922222202', 1),
    (2, 'demo_nv03', '$2b$12$QyLXx0b/2Q6p0W3G8j9cAO5f8wQkXeG7k6u9bJ4t7Y.s4b8aZhG5K', 'Lê Văn Bình', '0922222203', 1),
    (2, 'demo_nv04', '$2b$12$QyLXx0b/2Q6p0W3G8j9cAO5f8wQkXeG7k6u9bJ4t7Y.s4b8aZhG5K', 'Phạm Thu Hà', '0922222204', 1),
    (2, 'demo_nv05', '$2b$12$QyLXx0b/2Q6p0W3G8j9cAO5f8wQkXeG7k6u9bJ4t7Y.s4b8aZhG5K', 'Hoàng Minh Tuấn', '0922222205', 1),
    (2, 'demo_nv06', '$2b$12$QyLXx0b/2Q6p0W3G8j9cAO5f8wQkXeG7k6u9bJ4t7Y.s4b8aZhG5K', 'Võ Thị Lan', '0922222206', 1),
    (2, 'demo_nv07', '$2b$12$QyLXx0b/2Q6p0W3G8j9cAO5f8wQkXeG7k6u9bJ4t7Y.s4b8aZhG5K', 'Đặng Quốc Huy', '0922222207', 1),
    (2, 'demo_nv08', '$2b$12$QyLXx0b/2Q6p0W3G8j9cAO5f8wQkXeG7k6u9bJ4t7Y.s4b8aZhG5K', 'Bùi Ngọc Anh', '0922222208', 1);

-- ---------- service ----------
INSERT INTO service (name, price, description, duration_min, is_active) VALUES
    (N'Tắm gội cơ bản',           150000, N'Tắm, sấy khô, vệ sinh tai',  45, 1),
    (N'Tắm gội cao cấp',          250000, N'Tắm spa + xịt thơm',         60, 1),
    (N'Cắt tỉa lông',             200000, N'Cắt theo yêu cầu',           60, 1),
    (N'Vệ sinh tai - mắt',         80000, N'Làm sạch tai, nhổ lông tai', 20, 1),
    (N'Cắt móng',                  50000, N'Cắt móng chân',              10, 1),
    (N'Khám bệnh tổng quát',      300000, N'Khám + tư vấn',              30, 1),
    (N'Spa thư giãn',             350000, N'Spa trọn gói',               90, 1),
    (N'Tiêm phòng (gói cơ bản)',  500000, N'Vaccine cơ bản',             15, 1);

-- ---------- customer ----------
INSERT INTO customer (full_name, phone, address, email) VALUES
    (N'Nguyễn Văn An',   '0901234567', N'123 Lê Lợi, Q.1, TP.HCM', 'an.nv@example.com'),
    (N'Trần Thị Bình',   '0902345678', N'45 Nguyễn Huệ, Q.1, TP.HCM', 'binh.tt@example.com'),
    (N'Lê Hoàng Chí',    '0903456789', N'78 Võ Văn Tần, Q.3, TP.HCM', NULL);

-- ---------- pet ----------
INSERT INTO pet (customer_id, name, species, breed, age, gender, health_note) VALUES
    (1, 'Milu',  N'Chó', N'Poodle',       3, N'Cái', N'Dị ứng hải sản'),
    (1, 'Bông',  N'Mèo', N'Anh lông ngắn', 2, N'Đực', NULL),
    (2, 'Kitty', N'Mèo', N'Ba tư',         4, N'Cái', N'Đã tiêm phòng đầy đủ'),
    (3, 'Rex',   N'Chó', N'Husky',         5, N'Đực', NULL);

-- ---------- appointment (demo) ----------
INSERT INTO appointment (customer_id, pet_id, employee_id, scheduled_at, status, note) VALUES
    (1, 1, 2, DATE_ADD(NOW(), INTERVAL 1 DAY), 'CHO_XU_LY', N'Khách yêu cầu tắm + cắt móng'),
    (2, 3, 2, DATE_ADD(NOW(), INTERVAL 2 DAY), 'CHO_XU_LY', NULL);

-- ---------- appointment_service ----------
INSERT INTO appointment_service (appointment_id, service_id, quantity, unit_price) VALUES
    (1, 1, 1, 150000),
    (1, 5, 1, 50000),
    (2, 2, 1, 250000);

-- ---------- Lich hen da hoan thanh + hoa don DA_TT (de dashboard / bao cao co du lieu) ----------
INSERT INTO appointment (customer_id, pet_id, employee_id, scheduled_at, status, note) VALUES
    (1, 1, 2, DATE_SUB(NOW(), INTERVAL 2 DAY),  'HOAN_THANH', N'Hoàn thành — tắm + cắt móng'),
    (2, 3, 2, DATE_SUB(NOW(), INTERVAL 4 DAY),  'HOAN_THANH', NULL),
    (3, 4, 2, DATE_SUB(NOW(), INTERVAL 6 DAY),  'HOAN_THANH', NULL);

INSERT INTO appointment_service (appointment_id, service_id, quantity, unit_price) VALUES
    (3, 1, 1, 150000),
    (3, 5, 1, 50000),
    (4, 2, 1, 250000),
    (5, 3, 1, 200000);

INSERT INTO invoice (
    appointment_id, customer_id, invoice_type, invoice_no, issued_at,
    subtotal_amount, discount_amount, tax_amount, total_amount,
    payment_status, created_by, note
) VALUES
    (3, 1, 'SERVICE', 'INV-DV-SEED-001', DATE_SUB(NOW(), INTERVAL 2 DAY),
     200000, 0, 0, 200000, 'DA_TT', 2, NULL),
    (4, 2, 'SERVICE', 'INV-DV-SEED-002', DATE_SUB(NOW(), INTERVAL 4 DAY),
     250000, 0, 0, 250000, 'DA_TT', 2, NULL),
    (5, 3, 'SERVICE', 'INV-DV-SEED-003', DATE_SUB(NOW(), INTERVAL 6 DAY),
     200000, 0, 0, 200000, 'DA_TT', 2, NULL);

INSERT INTO invoice_item (invoice_id, service_id, product_id, item_type, pet_id, quantity, unit_price) VALUES
    (1, 1, NULL, 'SERVICE', 1, 1, 150000),
    (1, 5, NULL, 'SERVICE', 1, 1, 50000),
    (2, 2, NULL, 'SERVICE', 3, 1, 250000),
    (3, 3, NULL, 'SERVICE', 4, 1, 200000);

INSERT INTO payment (invoice_id, amount, method, paid_at, created_by) VALUES
    (1, 200000, 'TIEN_MAT', DATE_SUB(NOW(), INTERVAL 2 DAY),  2),
    (2, 250000, 'TIEN_MAT', DATE_SUB(NOW(), INTERVAL 4 DAY),  2),
    (3, 200000, 'CHUYEN_KHOAN', DATE_SUB(NOW(), INTERVAL 6 DAY), 2);

-- ---------- product (do an / phu kien) ----------
INSERT INTO product (name, category, sku, price, stock, description, is_active) VALUES
    (N'Hạt Royal Canin Adult 1kg', 'DO_AN',    'RC-ADL-1KG',  220000, 30,  N'Thức ăn hạt cho chó trưởng thành', 1),
    (N'Pate Whiskas vị cá 80g',    'DO_AN',    'WK-CA-80',    18000,  120, N'Pate cho mèo, vị cá biển',         1),
    (N'Snack Pedigree Dentastix',  'DO_AN',    'PD-STX',      45000,  80,  N'Snack chăm sóc răng miệng cho chó',1),
    (N'Vòng cổ da size M',         'PHU_KIEN', 'CL-LE-M',     85000,  25,  N'Vòng cổ da bò size M',             1),
    (N'Dây dắt nylon 1.5m',        'PHU_KIEN', 'LS-NY-150',   60000,  40,  N'Dây dắt nylon dài 1.5m',           1),
    (N'Lồng vận chuyển size M',    'PHU_KIEN', 'CG-M',        450000, 8,   N'Lồng nhựa di chuyển thú cưng',     1),
    (N'Bát ăn inox đôi',           'PHU_KIEN', 'BW-IN-2',     95000,  50,  N'Bát ăn inox kèm đế cao su',        1),
    (N'Sữa tắm bưởi Bio 250ml',    'PHU_KIEN', 'SH-BIO-250',  130000, 35,  N'Sữa tắm hương bưởi cho thú cưng',  1),
    (N'Hạt SmartHeart Puppy 1kg',  'DO_AN',    'DEMO-FOOD-001', 185000, 45, N'Hạt cho chó con dưới 12 tháng', 1),
    (N'Hạt Catrice Adult 500g',    'DO_AN',    'DEMO-FOOD-002', 95000,  60, N'Hạt cho mèo trưởng thành', 1),
    (N'Pate Cesar vị bò 100g',     'DO_AN',    'DEMO-FOOD-003', 22000,  150,N'Pate cho chó nhỏ', 1),
    (N'Hạt Me-O cá ngừ 1.2kg',     'DO_AN',    'DEMO-FOOD-006', 125000, 55, N'Hạt cho mèo vị cá ngừ', 1),
    (N'Nệm ngủ size L',            'PHU_KIEN', 'DEMO-ACC-001',  280000, 15, N'Nệm êm chống trượt', 1),
    (N'Khay vệ sinh mèo có nắp',   'PHU_KIEN', 'DEMO-ACC-002',  165000, 20, N'Khay vệ sinh kèm xẻng', 1),
    (N'Đồ chơi chuột catnip',      'PHU_KIEN', 'DEMO-ACC-003',  35000,  80, N'Đồ chơi kích thích mèo', 1),
    (N'Chuồng sắt size L',         'PHU_KIEN', 'DEMO-ACC-006',  520000, 6,  N'Chuồng sắt có khay hứng', 1);

-- Hoa don ban le (sau khi da co bang product)
INSERT INTO invoice (
    appointment_id, customer_id, invoice_type, invoice_no, issued_at,
    subtotal_amount, discount_amount, tax_amount, total_amount,
    payment_status, created_by, note
) VALUES
    (NULL, 1, 'RETAIL', 'INV-BL-SEED-001', DATE_SUB(NOW(), INTERVAL 1 DAY),
     220000, 0, 0, 220000, 'DA_TT', 2, N'Mua hạt demo');

INSERT INTO invoice_item (invoice_id, service_id, product_id, item_type, pet_id, quantity, unit_price) VALUES
    (4, NULL, 1, 'PRODUCT', NULL, 1, 220000);

INSERT INTO payment (invoice_id, amount, method, paid_at, created_by) VALUES
    (4, 220000, 'TIEN_MAT', DATE_SUB(NOW(), INTERVAL 1 DAY), 2);
