-- Index phụ cho workload. Tạo SAU khi nạp dữ liệu (nhanh hơn nạp có index).
-- InnoDB tự thêm khoá chính vào cuối mỗi index phụ, nên
-- (customer_id, order_date) thực chất là (customer_id, order_date, order_id).
USE shop_bench;

-- Q2: đơn gần nhất của một khách hàng
CREATE INDEX idx_orders_customer_date ON orders (customer_id, order_date);
-- Q3/Q4: lọc theo khoảng thời gian
CREATE INDEX idx_orders_date          ON orders (order_date);
-- Q3: lọc status + khoảng thời gian + sắp xếp theo thời gian
CREATE INDEX idx_orders_status_date   ON orders (status, order_date);
-- Q5/Q6: gom theo sản phẩm
CREATE INDEX idx_item_product         ON order_item (product_id);
-- Tra thanh toán theo đơn
CREATE INDEX idx_payment_order        ON payment (order_id);
-- Duyệt sản phẩm theo danh mục
CREATE INDEX idx_product_category     ON product (category_id);

ANALYZE TABLE category, customer, product, store, inventory, orders, order_item, payment;
