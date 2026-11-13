# So sánh MySQL và MongoDB trong quản lý bán hàng – Mục tiêu 3 và 4

Thiết kế mô hình dữ liệu, sinh dữ liệu tổng hợp, nạp vào hai hệ và (sắp tới) so sánh truy vấn có/không có Index.
Chi tiết thiết kế: xem `07_bao_cao_thiet_ke.md`.

## Các tệp

| Tệp | Nội dung |
|---|---|
| `01_mysql_schema.sql` | Lược đồ MySQL 3NF (8 bảng) |
| `02_mysql_indexes.sql` | Index phụ MySQL (một cấu hình đầy đủ, chưa chia mức) |
| `03_mongodb_schema.js` | 6 collection + validator (xoá collection cũ nếu có) |
| `03b_mongodb_indexes.js` | Index MongoDB tương đương |
| `04_generate_data.py` | Bộ sinh dữ liệu: seed cố định, phân phối Zipf, ghi CSV (MySQL) và JSONL (MongoDB) |
| `05_queries_mysql.sql` | Workload phía MySQL (Q1–Q8, W1–W3) |
| `06_queries_mongodb.js` | Workload phía MongoDB (tương đương), kèm `verifyLoad()` |
| `08_load_mysql.sql` | Nạp CSV vào MySQL (**cần sửa đường dẫn CSV cho máy bạn**) |
| `data/<quy_mô>/manifest.json` | Số dòng, doanh thu, số đơn theo trạng thái để đối chiếu |

## Trạng thái hiện tại
- Đã nạp và đối chiếu khớp `manifest.json` ở cả MySQL và MongoDB (quy mô 3 triệu đơn).
- **Chưa kiểm tra** truy vấn Q1–Q8 cho cùng kết quả giữa hai hệ, chưa đo hiệu năng, chưa chia các mức Index.

## Môi trường đã dùng (máy của Vinh; có thể khác trên máy bạn)
MySQL Server 26.10.0 (cổng 3308), MySQL Workbench 26.10.0, MongoDB 8.3.11 (cổng 27017),
mongosh 2.12.0, MongoDB Database Tools 100.20.1 (`mongoimport`), Python 3.
Nên chốt cùng một phiên bản server cho cả nhóm.

## Cách tái lập
1. Sinh dữ liệu (seed 42 mặc định; cùng seed và tham số cho ra dữ liệu giống hệt):
   ```
   python 04_generate_data.py --orders 3000000 --out data
   ```
   Kết quả: `data/custom_3000000/{mysql,mongo}/` và `manifest.json`.
2. MySQL: chạy `01_mysql_schema.sql`, sửa đường dẫn trong `08_load_mysql.sql` (dùng dấu `/`),
   bật `local_infile`, chạy `08_load_mysql.sql`, đối chiếu số dòng với `manifest.json`.
   Khi nạp lượng lớn, chạy `SET sql_log_bin = 0;` trước để tránh binlog phình to.
3. MongoDB: `mongosh --file 03_mongodb_schema.js`, nạp từng tệp `.jsonl` bằng `mongoimport`
   (`--db shop_bench --collection <tên>`), rồi `load("06_queries_mongodb.js"); verifyLoad()` để đối chiếu.
4. **Chưa chạy `02_mysql_indexes.sql` và `03b_mongodb_indexes.js`** khi muốn đo mức chưa có index.

## Số kỳ vọng ở quy mô 3 triệu đơn (seed 42)
category 60, store 50, customer 300000, product 50000, inventory 500000,
orders 3000000, order_item 8101297, payment 3150127, doanh thu gộp 816887197.08.

## Lưu ý
- Dữ liệu là **tổng hợp**; độ lệch (Zipf) và tỉ lệ trạng thái là giả định, không đo từ cửa hàng thật.
- Không commit mật khẩu hay tệp dữ liệu lớn (xem `.gitignore`).
