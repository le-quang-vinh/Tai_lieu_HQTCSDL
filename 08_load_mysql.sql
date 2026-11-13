-- =====================================================================
-- Nạp CSV vào MySQL bằng MySQL Workbench (LOAD DATA LOCAL INFILE)
-- TRƯỚC KHI CHẠY:
--  1) Đã chạy 01_mysql_schema.sql (tạo CSDL shop_bench và 8 bảng).
--  2) Bật local_infile ở server:   SET GLOBAL local_infile = 1;
--  3) Bật ở phía client: Workbench > Manage Server Connections > chọn connection >
--     Edit > tab Advanced > ô "Others" thêm dòng:  OPT_LOCAL_INFILE=1
--     rồi ĐÓNG và MỞ LẠI connection.
--  4) Dùng chức năng Find/Replace (Ctrl+H) đổi  C:/baitap/bansale/data/s/mysql/
--     thành đường dẫn thật tới thư mục mysql của bạn. Dùng dấu / (không dùng \).
--     Quy mô khác: đổi "s" thành "m" hoặc "l".
-- Thứ tự nạp bên dưới phải giữ nguyên vì có khoá ngoại.
-- =====================================================================
USE shop_bench;

SET unique_checks = 0;
SET foreign_key_checks = 0;

LOAD DATA LOCAL INFILE 'C:/UET/Uet2026-2027/HQTCSDL/Bo_sinh_du_lieu/data/custom_3000000/mysql/category.csv' INTO TABLE category
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';

LOAD DATA LOCAL INFILE 'C:/UET/Uet2026-2027/HQTCSDL/Bo_sinh_du_lieu/data/custom_3000000/mysql/store.csv' INTO TABLE store
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';

LOAD DATA LOCAL INFILE 'C:/UET/Uet2026-2027/HQTCSDL/Bo_sinh_du_lieu/data/custom_3000000/mysql/customer.csv' INTO TABLE customer
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';

LOAD DATA LOCAL INFILE 'C:/UET/Uet2026-2027/HQTCSDL/Bo_sinh_du_lieu/data/custom_3000000/mysql/product.csv' INTO TABLE product
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';

LOAD DATA LOCAL INFILE 'C:/UET/Uet2026-2027/HQTCSDL/Bo_sinh_du_lieu/data/custom_3000000/mysql/inventory.csv' INTO TABLE inventory
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';

LOAD DATA LOCAL INFILE 'C:/UET/Uet2026-2027/HQTCSDL/Bo_sinh_du_lieu/data/custom_3000000/mysql/orders.csv' INTO TABLE orders
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';

LOAD DATA LOCAL INFILE 'C:/UET/Uet2026-2027/HQTCSDL/Bo_sinh_du_lieu/data/custom_3000000/mysql/order_item.csv' INTO TABLE order_item
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';

LOAD DATA LOCAL INFILE 'C:/UET/Uet2026-2027/HQTCSDL/Bo_sinh_du_lieu/data/custom_3000000/mysql/payment.csv' INTO TABLE payment
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';

SET foreign_key_checks = 1;
SET unique_checks = 1;

-- ---------------------------------------------------------------------
-- ĐỐI CHIẾU: so với manifest.json (quy mô s: orders=100000, order_item=270597,
-- payment=104845, customer=10000, product=5000, inventory=50000, category=60, store=50;
-- revenue_gross=39470749.34)
-- ---------------------------------------------------------------------
SELECT 'category' AS t, COUNT(*) AS n FROM category UNION ALL
SELECT 'store', COUNT(*) FROM store UNION ALL
SELECT 'customer', COUNT(*) FROM customer UNION ALL
SELECT 'product', COUNT(*) FROM product UNION ALL
SELECT 'inventory', COUNT(*) FROM inventory UNION ALL
SELECT 'orders', COUNT(*) FROM orders UNION ALL
SELECT 'order_item', COUNT(*) FROM order_item UNION ALL
SELECT 'payment', COUNT(*) FROM payment;

SELECT SUM(quantity * unit_price) AS revenue_gross FROM order_item;

-- Sau khi số liệu khớp, chạy tiếp 02_mysql_indexes.sql để tạo index.
