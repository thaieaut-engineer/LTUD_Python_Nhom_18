-- =====================================================================
-- MIGRATION: Luu duong dan anh thu cung / san pham
-- Cach chay:
--     mysql -u root -p petcare_db < database/migrations/add_catalog_image_path.sql
-- =====================================================================

USE petcare_db;

ALTER TABLE pet
    ADD COLUMN image_path VARCHAR(512) NULL
        COMMENT 'Duong dan anh da luu tren dia'
        AFTER health_note;

ALTER TABLE product
    ADD COLUMN image_path VARCHAR(512) NULL
        COMMENT 'Duong dan anh da luu tren dia'
        AFTER description;
