-- =====================================================================
-- PET CARE MANAGEMENT - MySQL Schema
-- Database: petcare_db
-- Charset : utf8mb4
-- Engine  : InnoDB
-- =====================================================================

DROP DATABASE IF EXISTS petcare_db;
CREATE DATABASE petcare_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE petcare_db;

-- ---------------------------------------------------------------------
-- 1. role
-- ---------------------------------------------------------------------
CREATE TABLE role (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(20)     NOT NULL UNIQUE COMMENT 'ADMIN | EMPLOYEE',
    description     VARCHAR(100)    NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. user (tai khoan dang nhap he thong)
-- ---------------------------------------------------------------------
CREATE TABLE user (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    role_id         INT             NOT NULL,
    username        VARCHAR(50)     NOT NULL UNIQUE,
    password_hash   VARCHAR(255)    NOT NULL,
    full_name       VARCHAR(100)    NOT NULL,
    phone           VARCHAR(20)     NULL,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_role
        FOREIGN KEY (role_id) REFERENCES role(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_user_role (role_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. customer (khach hang)
-- ---------------------------------------------------------------------
CREATE TABLE customer (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(100)    NOT NULL,
    phone           VARCHAR(20)     NOT NULL UNIQUE,
    address         VARCHAR(255)    NULL,
    email           VARCHAR(100)    NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_customer_name (full_name)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 4. pet (thu cung)
-- ---------------------------------------------------------------------
CREATE TABLE pet (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    customer_id     INT             NOT NULL,
    name            VARCHAR(50)     NOT NULL,
    species         VARCHAR(30)     NOT NULL COMMENT 'Cho, Meo, ...',
    breed           VARCHAR(50)     NULL,
    age             INT             NULL,
    gender          VARCHAR(10)     NULL COMMENT 'Duc | Cai',
    health_note     TEXT            NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_pet_customer
        FOREIGN KEY (customer_id) REFERENCES customer(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    INDEX idx_pet_customer (customer_id),
    INDEX idx_pet_name (name)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 5. service (dich vu)
-- ---------------------------------------------------------------------
CREATE TABLE service (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL UNIQUE,
    price           DECIMAL(12,2)   NOT NULL DEFAULT 0 CHECK (price >= 0),
    description     TEXT            NULL,
    duration_min    INT             NULL COMMENT 'Thoi gian thuc hien (phut)',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 6. appointment (lich hen)
-- ---------------------------------------------------------------------
CREATE TABLE appointment (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    customer_id     INT             NOT NULL,
    pet_id          INT             NOT NULL,
    employee_id     INT             NULL COMMENT 'Nhan vien phu trach',
    scheduled_at    DATETIME        NOT NULL,
    status          ENUM('CHO_XU_LY','DANG_THUC_HIEN','HOAN_THANH','HUY')
                                    NOT NULL DEFAULT 'CHO_XU_LY',
    note            TEXT            NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_app_customer
        FOREIGN KEY (customer_id) REFERENCES customer(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_app_pet
        FOREIGN KEY (pet_id) REFERENCES pet(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_app_employee
        FOREIGN KEY (employee_id) REFERENCES user(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_app_customer (customer_id),
    INDEX idx_app_pet (pet_id),
    INDEX idx_app_employee (employee_id),
    INDEX idx_app_scheduled (scheduled_at),
    INDEX idx_app_status (status)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 7. appointment_service (bang trung gian - dich vu trong lich hen)
-- ---------------------------------------------------------------------
CREATE TABLE appointment_service (
    appointment_id  INT             NOT NULL,
    service_id      INT             NOT NULL,
    quantity        INT             NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price      DECIMAL(12,2)   NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (appointment_id, service_id),
    CONSTRAINT fk_apps_appointment
        FOREIGN KEY (appointment_id) REFERENCES appointment(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_apps_service
        FOREIGN KEY (service_id) REFERENCES service(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 8. invoice (hoa don)
-- ---------------------------------------------------------------------
CREATE TABLE invoice (
    id                  INT             AUTO_INCREMENT PRIMARY KEY,
    appointment_id      INT             NOT NULL UNIQUE COMMENT 'Moi appointment chi co 1 hoa don',
    invoice_no          VARCHAR(30)     NOT NULL UNIQUE,
    issued_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subtotal_amount     DECIMAL(14,2)   NOT NULL DEFAULT 0 CHECK (subtotal_amount >= 0),
    discount_amount     DECIMAL(14,2)   NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    tax_amount          DECIMAL(14,2)   NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
    total_amount        DECIMAL(14,2)   NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    payment_status      ENUM('CHUA_TT','DA_TT','HOAN_TIEN')
                                        NOT NULL DEFAULT 'CHUA_TT',
    created_by          INT             NULL COMMENT 'User tao hoa don',
    note                TEXT            NULL,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_inv_appointment
        FOREIGN KEY (appointment_id) REFERENCES appointment(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_inv_user
        FOREIGN KEY (created_by) REFERENCES user(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_inv_issued (issued_at),
    INDEX idx_inv_status (payment_status)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 9. invoice_item (chi tiet hoa don)
-- ---------------------------------------------------------------------
CREATE TABLE invoice_item (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    invoice_id      INT             NOT NULL,
    service_id      INT             NOT NULL,
    quantity        INT             NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price      DECIMAL(12,2)   NOT NULL CHECK (unit_price >= 0),
    line_total      DECIMAL(14,2)   GENERATED ALWAYS AS (quantity * unit_price) STORED,
    CONSTRAINT fk_item_invoice
        FOREIGN KEY (invoice_id) REFERENCES invoice(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_item_service
        FOREIGN KEY (service_id) REFERENCES service(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_item_invoice (invoice_id),
    INDEX idx_item_service (service_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 10. payment (thanh toan)
-- ---------------------------------------------------------------------
CREATE TABLE payment (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    invoice_id      INT             NOT NULL,
    amount          DECIMAL(14,2)   NOT NULL CHECK (amount > 0),
    method          ENUM('TIEN_MAT','CHUYEN_KHOAN','THE')
                                    NOT NULL DEFAULT 'TIEN_MAT',
    paid_at         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note            VARCHAR(255)    NULL,
    created_by      INT             NULL,
    CONSTRAINT fk_pay_invoice
        FOREIGN KEY (invoice_id) REFERENCES invoice(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_pay_user
        FOREIGN KEY (created_by) REFERENCES user(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_pay_invoice (invoice_id),
    INDEX idx_pay_paid_at (paid_at)
) ENGINE=InnoDB;

-- =====================================================================
-- VIEWS tien loi cho bao cao
-- =====================================================================

CREATE OR REPLACE VIEW v_invoice_summary AS
SELECT
    i.id                AS invoice_id,
    i.invoice_no,
    i.issued_at,
    i.total_amount,
    i.payment_status,
    c.id                AS customer_id,
    c.full_name         AS customer_name,
    c.phone             AS customer_phone,
    a.id                AS appointment_id,
    a.scheduled_at
FROM invoice i
JOIN appointment a ON a.id = i.appointment_id
JOIN customer    c ON c.id = a.customer_id;

CREATE OR REPLACE VIEW v_revenue_by_day AS
SELECT
    DATE(i.issued_at)                       AS revenue_date,
    COUNT(*)                                AS invoice_count,
    SUM(i.total_amount)                     AS total_revenue
FROM invoice i
WHERE i.payment_status = 'DA_TT'
GROUP BY DATE(i.issued_at);

CREATE OR REPLACE VIEW v_popular_services AS
SELECT
    s.id                                    AS service_id,
    s.name                                  AS service_name,
    COALESCE(SUM(ii.quantity), 0)           AS total_sold,
    COALESCE(SUM(ii.line_total), 0)         AS total_revenue
FROM service s
LEFT JOIN invoice_item ii ON ii.service_id = s.id
LEFT JOIN invoice i       ON i.id = ii.invoice_id AND i.payment_status = 'DA_TT'
GROUP BY s.id, s.name;
