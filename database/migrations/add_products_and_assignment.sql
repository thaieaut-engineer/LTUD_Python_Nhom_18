-- =====================================================================
-- MIGRATION: Bo sung tinh nang ban do an / phu kien va phan cong nhan vien
-- Phien ban : v2 (sau seed.sql goc)
-- Cach chay :
--     mysql -u root -p petcare_db < database/migrations/add_products_and_assignment.sql
-- An toan: cac lenh ALTER chi them cot/bang moi, KHONG xoa du lieu cu.
-- =====================================================================

USE petcare_db;

-- ---------------------------------------------------------------------
-- 1) Bang product (do an / phu kien)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(120)    NOT NULL,
    category        VARCHAR(20)     NOT NULL DEFAULT 'PHU_KIEN'
                                    COMMENT 'DO_AN | PHU_KIEN',
    sku             VARCHAR(40)     NULL,
    price           DECIMAL(12,2)   NOT NULL DEFAULT 0 CHECK (price >= 0),
    stock           INT             NOT NULL DEFAULT 0 CHECK (stock >= 0),
    description     TEXT            NULL,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_product_name (name),
    INDEX idx_product_category (category),
    INDEX idx_product_active (is_active)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2) Mo rong invoice: cho phep hoa don ban le (khong ke lich hen)
--    - appointment_id co the NULL (POS)
--    - them customer_id (cho ban le, walk-in van co the NULL)
--    - them invoice_type: SERVICE | RETAIL
-- ---------------------------------------------------------------------

-- Doi sang nullable (idempotent)
ALTER TABLE invoice
    MODIFY COLUMN appointment_id INT NULL;

-- Rang buoc 1-1 voi appointment van duoc giu (MySQL UNIQUE cho phep nhieu NULL).
-- Quy trinh: tam drop FK -> drop unique cu -> tao unique moi voi ten on dinh
-- -> tao lai FK. Tat ca deu idempotent (chi chay khi can).

-- 2.1 Drop FK fk_inv_appointment neu dang ton tai
SET @fk_exists := (
    SELECT COUNT(*) FROM information_schema.table_constraints
    WHERE table_schema = DATABASE()
      AND table_name = 'invoice'
      AND constraint_name = 'fk_inv_appointment'
);
SET @sql := IF(@fk_exists > 0,
    'ALTER TABLE invoice DROP FOREIGN KEY fk_inv_appointment',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 2.2 Neu chua co unique 'uk_invoice_appointment' thi tao moi
SET @uk_exists := (
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'invoice'
      AND index_name = 'uk_invoice_appointment'
);
SET @sql := IF(@uk_exists = 0,
    'ALTER TABLE invoice ADD UNIQUE KEY uk_invoice_appointment (appointment_id)',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 2.3 Drop unique cu 'appointment_id' (chi khi chac chan da co unique moi roi)
SET @idx_exists := (
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'invoice'
      AND index_name = 'appointment_id'
);
SET @sql := IF(@idx_exists > 0,
    'ALTER TABLE invoice DROP INDEX appointment_id',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 2.4 Tao lai FK fk_inv_appointment (no se dung uk_invoice_appointment)
SET @fk_exists := (
    SELECT COUNT(*) FROM information_schema.table_constraints
    WHERE table_schema = DATABASE()
      AND table_name = 'invoice'
      AND constraint_name = 'fk_inv_appointment'
);
SET @sql := IF(@fk_exists = 0,
    'ALTER TABLE invoice ADD CONSTRAINT fk_inv_appointment FOREIGN KEY (appointment_id) REFERENCES appointment(id) ON UPDATE CASCADE ON DELETE RESTRICT',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Them cot customer_id, invoice_type (idempotent)
SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'invoice'
      AND column_name = 'customer_id'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE invoice ADD COLUMN customer_id INT NULL AFTER appointment_id',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'invoice'
      AND column_name = 'invoice_type'
);
SET @sql := IF(@col_exists = 0,
    "ALTER TABLE invoice ADD COLUMN invoice_type ENUM('SERVICE','RETAIL') NOT NULL DEFAULT 'SERVICE' AFTER customer_id",
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Them FK invoice -> customer
SET @fk_exists := (
    SELECT COUNT(*) FROM information_schema.table_constraints
    WHERE table_schema = DATABASE()
      AND table_name = 'invoice'
      AND constraint_name = 'fk_inv_customer'
);
SET @sql := IF(@fk_exists = 0,
    'ALTER TABLE invoice ADD CONSTRAINT fk_inv_customer FOREIGN KEY (customer_id) REFERENCES customer(id) ON UPDATE CASCADE ON DELETE SET NULL',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Sao chep customer_id tu appointment cho cac hoa don dich vu cu
-- Tat tam safe-update mode (MySQL Workbench bat mac dinh) vi UPDATE nay
-- khong loc theo khoa chinh.
SET @old_safe_updates := @@SQL_SAFE_UPDATES;
SET SQL_SAFE_UPDATES = 0;

UPDATE invoice i
JOIN appointment a ON a.id = i.appointment_id
   SET i.customer_id = a.customer_id
 WHERE i.customer_id IS NULL;

SET SQL_SAFE_UPDATES = @old_safe_updates;

-- ---------------------------------------------------------------------
-- 3) Mo rong invoice_item: ho tro SERVICE va PRODUCT
--    - service_id chuyen sang nullable
--    - them product_id, item_type
-- ---------------------------------------------------------------------
ALTER TABLE invoice_item
    MODIFY COLUMN service_id INT NULL;

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'invoice_item'
      AND column_name = 'product_id'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE invoice_item ADD COLUMN product_id INT NULL AFTER service_id',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'invoice_item'
      AND column_name = 'item_type'
);
SET @sql := IF(@col_exists = 0,
    "ALTER TABLE invoice_item ADD COLUMN item_type ENUM('SERVICE','PRODUCT') NOT NULL DEFAULT 'SERVICE' AFTER product_id",
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @fk_exists := (
    SELECT COUNT(*) FROM information_schema.table_constraints
    WHERE table_schema = DATABASE()
      AND table_name = 'invoice_item'
      AND constraint_name = 'fk_item_product'
);
SET @sql := IF(@fk_exists = 0,
    'ALTER TABLE invoice_item ADD CONSTRAINT fk_item_product FOREIGN KEY (product_id) REFERENCES product(id) ON UPDATE CASCADE ON DELETE RESTRICT',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Index ho tro
SET @idx_exists := (
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'invoice_item'
      AND index_name = 'idx_item_product'
);
SET @sql := IF(@idx_exists = 0,
    'ALTER TABLE invoice_item ADD INDEX idx_item_product (product_id)',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ---------------------------------------------------------------------
-- 4) Seed du lieu mau cho product (chi them khi bang con trong)
-- ---------------------------------------------------------------------
INSERT INTO product (name, category, sku, price, stock, description, is_active)
SELECT * FROM (
    SELECT N'Hạt Royal Canin Adult 1kg' AS name, 'DO_AN' AS category, 'RC-ADL-1KG' AS sku, 220000 AS price, 30 AS stock, N'Thức ăn hạt cho chó trưởng thành' AS description, 1 AS is_active UNION ALL
    SELECT N'Pate Whiskas vị cá 80g',     'DO_AN',    'WK-CA-80',    18000,  120, N'Pate cho mèo, vị cá biển',          1 UNION ALL
    SELECT N'Snack Pedigree Dentastix',   'DO_AN',    'PD-STX',      45000,  80,  N'Snack chăm sóc răng miệng cho chó', 1 UNION ALL
    SELECT N'Vòng cổ da size M',          'PHU_KIEN', 'CL-LE-M',     85000,  25,  N'Vòng cổ da bò size M',              1 UNION ALL
    SELECT N'Dây dắt nylon 1.5m',         'PHU_KIEN', 'LS-NY-150',   60000,  40,  N'Dây dắt nylon dài 1.5m',            1 UNION ALL
    SELECT N'Lồng vận chuyển size M',     'PHU_KIEN', 'CG-M',        450000, 8,   N'Lồng nhựa di chuyển thú cưng',      1 UNION ALL
    SELECT N'Bát ăn inox đôi',            'PHU_KIEN', 'BW-IN-2',     95000,  50,  N'Bát ăn inox kèm đế cao su',         1 UNION ALL
    SELECT N'Sữa tắm bưởi Bio 250ml',     'PHU_KIEN', 'SH-BIO-250',  130000, 35,  N'Sữa tắm hương bưởi cho thú cưng',   1
) AS seed_data
WHERE NOT EXISTS (SELECT 1 FROM product LIMIT 1);

-- ---------------------------------------------------------------------
-- 5) View tien loi: hoa don kem ten nhan vien tao (User - Invoice)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_invoice_with_creator AS
SELECT
    i.id                AS invoice_id,
    i.invoice_no,
    i.issued_at,
    i.invoice_type,
    i.appointment_id,
    i.customer_id,
    COALESCE(c.full_name, cust_a.full_name) AS customer_name,
    COALESCE(c.phone, cust_a.phone)         AS customer_phone,
    i.total_amount,
    i.payment_status,
    i.created_by        AS created_by_id,
    u.full_name         AS created_by_name,
    u.username          AS created_by_username
FROM invoice i
LEFT JOIN customer c        ON c.id = i.customer_id
LEFT JOIN appointment a     ON a.id = i.appointment_id
LEFT JOIN customer cust_a   ON cust_a.id = a.customer_id
LEFT JOIN user u            ON u.id = i.created_by;

-- ---------------------------------------------------------------------
-- 6) View tien loi: lich hen kem ten NV phu trach (User - Appointment)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_appointment_with_employee AS
SELECT
    a.id                AS appointment_id,
    a.scheduled_at,
    a.status,
    a.note,
    a.customer_id,
    c.full_name         AS customer_name,
    c.phone             AS customer_phone,
    a.pet_id,
    p.name              AS pet_name,
    a.employee_id,
    u.full_name         AS employee_name,
    u.username          AS employee_username
FROM appointment a
JOIN customer c     ON c.id = a.customer_id
LEFT JOIN pet p     ON p.id = a.pet_id
LEFT JOIN user u    ON u.id = a.employee_id;

-- ---------------------------------------------------------------------
-- DONE.
-- ---------------------------------------------------------------------
SELECT 'Migration add_products_and_assignment.sql DONE' AS status;
