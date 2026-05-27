-- =====================================================================
-- MIGRATION: Luu tru / cham soc thu cung theo ngay (boarding)
-- Chay: mysql -u root -p petcare_db < database/migrations/add_pet_boarding.sql
-- =====================================================================

USE petcare_db;

CREATE TABLE IF NOT EXISTS pet_stay (
    id                      INT             AUTO_INCREMENT PRIMARY KEY,
    pet_id                  INT             NOT NULL,
    customer_id             INT             NOT NULL,
    employee_id             INT             NULL COMMENT 'Nhan vien cham soc chinh',
    check_in_at             DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expected_check_out_at   DATETIME        NULL,
    actual_check_out_at     DATETIME        NULL,
    status                  ENUM('DANG_CHAM_SOC','KHACH_DA_NHAN','HUY')
                                            NOT NULL DEFAULT 'DANG_CHAM_SOC',
    daily_rate              DECIMAL(12,2)   NOT NULL DEFAULT 0 CHECK (daily_rate >= 0),
    note                    TEXT            NULL,
    created_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                            ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_stay_pet
        FOREIGN KEY (pet_id) REFERENCES pet(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_stay_customer
        FOREIGN KEY (customer_id) REFERENCES customer(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_stay_employee
        FOREIGN KEY (employee_id) REFERENCES user(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_stay_pet (pet_id),
    INDEX idx_stay_status (status),
    INDEX idx_stay_check_in (check_in_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pet_care_log (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY,
    stay_id         INT             NOT NULL,
    employee_id     INT             NULL,
    log_type        ENUM('FEEDING','CARE','STATUS')
                                    NOT NULL DEFAULT 'CARE',
    content         TEXT            NOT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_stay
        FOREIGN KEY (stay_id) REFERENCES pet_stay(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_log_employee
        FOREIGN KEY (employee_id) REFERENCES user(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_log_stay (stay_id),
    INDEX idx_log_created (created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pet_care_media (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY,
    stay_id         INT             NOT NULL,
    care_log_id     BIGINT          NULL,
    media_type      ENUM('IMAGE','VIDEO') NOT NULL,
    file_path       VARCHAR(500)    NOT NULL,
    caption         VARCHAR(255)    NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_media_stay
        FOREIGN KEY (stay_id) REFERENCES pet_stay(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_media_log
        FOREIGN KEY (care_log_id) REFERENCES pet_care_log(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_media_stay (stay_id)
) ENGINE=InnoDB;

-- Hoa don gan voi dot luu tru
SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'invoice' AND column_name = 'pet_stay_id'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE invoice ADD COLUMN pet_stay_id INT NULL AFTER appointment_id',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @uk_exists := (
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'invoice' AND index_name = 'uk_invoice_pet_stay'
);
SET @sql := IF(@uk_exists = 0,
    'ALTER TABLE invoice ADD UNIQUE KEY uk_invoice_pet_stay (pet_stay_id)',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @fk_exists := (
    SELECT COUNT(*) FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'invoice' AND constraint_name = 'fk_inv_pet_stay'
);
SET @sql := IF(@fk_exists = 0,
    'ALTER TABLE invoice ADD CONSTRAINT fk_inv_pet_stay FOREIGN KEY (pet_stay_id) REFERENCES pet_stay(id) ON UPDATE CASCADE ON DELETE RESTRICT',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
