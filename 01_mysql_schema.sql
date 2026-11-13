-- =====================================================================
-- MỤC TIÊU 3 - MySQL 8.x: lược đồ quan hệ chuẩn hoá 3NF cho quản lý bán hàng
-- Chạy: mysql -u root -p < 01_mysql_schema.sql
-- Index phụ (secondary) nằm ở 02_mysql_indexes.sql, tạo SAU khi nạp dữ liệu
-- để nạp nhanh hơn. Khi đo đạc phải tạo đủ index trước khi chạy workload.
-- Quy ước thời gian: DATETIME lưu theo UTC (không có múi giờ).
-- =====================================================================
CREATE DATABASE IF NOT EXISTS shop_bench
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE shop_bench;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS payment, order_item, orders, inventory,
                     product, customer, store, category;
SET FOREIGN_KEY_CHECKS = 1;

-- Danh mục 2 cấp (root -> leaf), tự tham chiếu
CREATE TABLE category (
  category_id SMALLINT UNSIGNED NOT NULL,
  name        VARCHAR(100)      NOT NULL,
  parent_id   SMALLINT UNSIGNED NULL,
  PRIMARY KEY (category_id),
  CONSTRAINT fk_category_parent FOREIGN KEY (parent_id)
    REFERENCES category (category_id)
) ENGINE=InnoDB;

CREATE TABLE customer (
  customer_id INT UNSIGNED NOT NULL,
  full_name   VARCHAR(120) NOT NULL,
  email       VARCHAR(150) NOT NULL,
  phone       VARCHAR(20)  NOT NULL,
  city        VARCHAR(60)  NOT NULL,
  created_at  DATETIME     NOT NULL,
  PRIMARY KEY (customer_id),
  UNIQUE KEY uq_customer_email (email)
) ENGINE=InnoDB;

CREATE TABLE product (
  product_id  INT UNSIGNED      NOT NULL,
  sku         VARCHAR(20)       NOT NULL,
  name        VARCHAR(150)      NOT NULL,
  category_id SMALLINT UNSIGNED NOT NULL,
  price       DECIMAL(12,2)     NOT NULL,   -- giá niêm yết hiện tại
  created_at  DATETIME          NOT NULL,
  PRIMARY KEY (product_id),
  UNIQUE KEY uq_product_sku (sku),
  CONSTRAINT fk_product_category FOREIGN KEY (category_id)
    REFERENCES category (category_id)
) ENGINE=InnoDB;

CREATE TABLE store (
  store_id SMALLINT UNSIGNED NOT NULL,
  name     VARCHAR(100)      NOT NULL,
  city     VARCHAR(60)       NOT NULL,
  PRIMARY KEY (store_id)
) ENGINE=InnoDB;

-- Tồn kho: quan hệ N-N giữa cửa hàng và sản phẩm
CREATE TABLE inventory (
  store_id   SMALLINT UNSIGNED NOT NULL,
  product_id INT UNSIGNED      NOT NULL,
  quantity   INT               NOT NULL,
  PRIMARY KEY (store_id, product_id),
  CONSTRAINT fk_inv_store   FOREIGN KEY (store_id)   REFERENCES store (store_id),
  CONSTRAINT fk_inv_product FOREIGN KEY (product_id) REFERENCES product (product_id),
  CONSTRAINT ck_inv_qty CHECK (quantity >= 0)
) ENGINE=InnoDB;

-- Lưu ý 3NF: KHÔNG có cột total_amount (suy ra được = SUM(quantity*unit_price)).
CREATE TABLE orders (
  order_id    BIGINT UNSIGNED   NOT NULL,
  customer_id INT UNSIGNED      NOT NULL,
  store_id    SMALLINT UNSIGNED NOT NULL,
  order_date  DATETIME          NOT NULL,
  status      ENUM('PENDING','PAID','SHIPPED','DELIVERED','CANCELLED','RETURNED') NOT NULL,
  PRIMARY KEY (order_id),
  CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customer (customer_id),
  CONSTRAINT fk_orders_store    FOREIGN KEY (store_id)    REFERENCES store (store_id)
) ENGINE=InnoDB;

-- unit_price là giá TẠI THỜI ĐIỂM đặt hàng (snapshot), phụ thuộc vào khoá
-- (order_id, line_no) chứ không suy ra từ product.price -> vẫn đúng 3NF.
CREATE TABLE order_item (
  order_id   BIGINT UNSIGNED   NOT NULL,
  line_no    TINYINT UNSIGNED  NOT NULL,
  product_id INT UNSIGNED      NOT NULL,
  quantity   SMALLINT UNSIGNED NOT NULL,
  unit_price DECIMAL(12,2)     NOT NULL,
  PRIMARY KEY (order_id, line_no),
  CONSTRAINT fk_item_order   FOREIGN KEY (order_id)   REFERENCES orders (order_id),
  CONSTRAINT fk_item_product FOREIGN KEY (product_id) REFERENCES product (product_id),
  CONSTRAINT ck_item_qty CHECK (quantity > 0)
) ENGINE=InnoDB;

CREATE TABLE payment (
  payment_id BIGINT UNSIGNED NOT NULL,
  order_id   BIGINT UNSIGNED NOT NULL,
  method     ENUM('CARD','EWALLET','COD','BANK_TRANSFER','CASH') NOT NULL,
  amount     DECIMAL(14,2)   NOT NULL,
  paid_at    DATETIME        NULL,
  status     ENUM('PENDING','PAID','FAILED','REFUNDED') NOT NULL,
  PRIMARY KEY (payment_id),
  CONSTRAINT fk_payment_order FOREIGN KEY (order_id) REFERENCES orders (order_id)
) ENGINE=InnoDB;
