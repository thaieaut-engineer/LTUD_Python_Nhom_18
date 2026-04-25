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
    (1, 'admin', '$2b$12$u1m5T7vH4M3xTqj3O2J1eOYxC2ZkQmV.QoA1h1o0yGk2cM2o2eXfW', 'Quan tri vien', '0900000000', 1),
    (2, 'nv01',  '$2b$12$QyLXx0b/2Q6p0W3G8j9cAO5f8wQkXeG7k6u9bJ4t7Y.s4b8aZhG5K', 'Nhan vien 01', '0911111111', 1);

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
