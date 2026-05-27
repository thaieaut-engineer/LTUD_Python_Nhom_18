-- Liên kết log chăm sóc với sản phẩm (cho ăn) / dịch vụ
USE petcare_db;

SET @col := (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'pet_care_log' AND column_name = 'product_id'
);
SET @sql := IF(@col = 0,
    'ALTER TABLE pet_care_log
        ADD COLUMN product_id INT NULL AFTER content,
        ADD COLUMN service_id INT NULL AFTER product_id,
        ADD COLUMN quantity INT NULL DEFAULT 1 AFTER service_id,
        ADD CONSTRAINT fk_log_product FOREIGN KEY (product_id) REFERENCES product(id) ON UPDATE CASCADE ON DELETE SET NULL,
        ADD CONSTRAINT fk_log_service FOREIGN KEY (service_id) REFERENCES service(id) ON UPDATE CASCADE ON DELETE SET NULL',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
