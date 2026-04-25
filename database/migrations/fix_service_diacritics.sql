-- =====================================================================
-- MIGRATION: Bo sung dau tieng Viet cho bang `service`
-- Ly do : seed.sql ban dau insert ten/mo ta khong dau, hien thi xau tren UI.
-- An toan: chi UPDATE theo `name` cu, KHONG dong cham invoice/appointment.
-- Cach chay:
--     mysql -u root -p petcare_db < database/migrations/fix_service_diacritics.sql
-- Hoac chay tung lenh trong MySQL Workbench.
-- =====================================================================

USE petcare_db;

UPDATE service
   SET name        = N'Tắm gội cơ bản',
       description = N'Tắm, sấy khô, vệ sinh tai'
 WHERE name = 'Tam goi co ban';

UPDATE service
   SET name        = N'Tắm gội cao cấp',
       description = N'Tắm spa + xịt thơm'
 WHERE name = 'Tam goi cao cap';

UPDATE service
   SET name        = N'Cắt tỉa lông',
       description = N'Cắt theo yêu cầu'
 WHERE name = 'Cat tia long';

UPDATE service
   SET name        = N'Vệ sinh tai - mắt',
       description = N'Làm sạch tai, nhổ lông tai'
 WHERE name = 'Ve sinh tai - mat';

UPDATE service
   SET name        = N'Cắt móng',
       description = N'Cắt móng chân'
 WHERE name = 'Cat mong';

UPDATE service
   SET name        = N'Khám bệnh tổng quát',
       description = N'Khám + tư vấn'
 WHERE name = 'Kham benh tong quat';

UPDATE service
   SET name        = N'Spa thư giãn',
       description = N'Spa trọn gói'
 WHERE name = 'Spa thu gian';

UPDATE service
   SET name        = N'Tiêm phòng (gói cơ bản)',
       description = N'Vaccine cơ bản'
 WHERE name = 'Tiem phong (goi co ban)';

-- Kiem tra ket qua
SELECT id, name, price, description FROM service ORDER BY id;
