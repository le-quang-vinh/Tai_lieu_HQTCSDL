// Index MongoDB tương đương index MySQL (02_mysql_indexes.sql).
// Chạy SAU mongoimport:  mongosh --file 03b_mongodb_indexes.js
use("shop_bench");

db.customers.createIndex({ email: 1 }, { unique: true });          // uq_customer_email
db.products.createIndex({ sku: 1 }, { unique: true });             // uq_product_sku
db.products.createIndex({ category_id: 1 });                       // idx_product_category
db.inventory.createIndex({ store_id: 1, product_id: 1 }, { unique: true });  // PK (store_id, product_id)

// Q2 - khớp idx_orders_customer_date; _id ở cuối để sort ổn định như InnoDB (PK ẩn cuối index)
db.orders.createIndex({ customer_id: 1, order_date: -1, _id: -1 });
// Q3/Q4 - khớp idx_orders_date và idx_orders_status_date
db.orders.createIndex({ order_date: 1 });
db.orders.createIndex({ status: 1, order_date: 1, _id: 1 });
// Q5/Q6 - multikey, tương đương idx_item_product
db.orders.createIndex({ "items.product_id": 1 });
// payments nhúng trong order nên không cần index riêng như idx_payment_order

printjson(db.orders.getIndexes().map(i => i.name));
