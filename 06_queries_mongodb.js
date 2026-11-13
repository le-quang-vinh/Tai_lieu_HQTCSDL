// =====================================================================
// WORKLOAD MongoDB (tương đương 1-1 với 05_queries_mysql.sql)
// Chạy trong mongosh:  load("06_queries_mongodb.js")
// Mọi truy vấn dùng cùng tham số và cùng thứ tự sắp xếp (kể cả tie-break theo _id)
// để kết quả khớp từng dòng với MySQL.
// =====================================================================
use("shop_bench");

const oid  = 123456, cid = 5439;
const d1   = ISODate("2025-03-01T00:00:00Z"), d2   = ISODate("2025-04-01T00:00:00Z");
const day1 = ISODate("2025-03-15T00:00:00Z"), day2 = ISODate("2025-03-22T00:00:00Z");
const EXCL = ["CANCELLED", "RETURNED"];
// Biểu thức tổng tiền của một đơn: SUM(quantity * unit_price) trên items nhúng
const orderTotal = { $sum: { $map: { input: "$items", as: "i",
                      in: { $multiply: ["$$i.quantity", "$$i.unit_price"] } } } };

// ---------------------------------------------------------------- ĐỌC
// Q1 (20%) Tra cứu đơn theo khoá: một lần đọc lấy cả items + payments
function Q1() { return db.orders.findOne({ _id: oid }); }

// Q2 (20%) 20 đơn gần nhất của khách
function Q2() {
  return db.orders.find({ customer_id: cid }, { order_date: 1, status: 1 })
    .sort({ order_date: -1, _id: -1 }).limit(20).toArray();
}

// Q3 (10%) Khoảng thời gian + trạng thái + sắp xếp + phân trang
function Q3() {
  return db.orders.find(
    { order_date: { $gte: day1, $lt: day2 }, status: "SHIPPED" },
    { customer_id: 1, order_date: 1, status: 1 })
    .sort({ order_date: 1, _id: 1 }).limit(100).toArray();
}

// Q4 (4%) Doanh thu theo tháng (không cần $unwind vì items nhúng)
function Q4() {
  return db.orders.aggregate([
    { $match: { order_date: { $gte: ISODate("2024-01-01T00:00:00Z"),
                              $lt:  ISODate("2026-01-01T00:00:00Z") },
                status: { $nin: EXCL } } },
    { $group: { _id: { $dateToString: { format: "%Y-%m", date: "$order_date" } },
                orders: { $sum: 1 }, revenue: { $sum: orderTotal } } },
    { $sort: { _id: 1 } }
  ]).toArray();
}

// Q5 (4%) Top 10 sản phẩm theo doanh thu (cần $unwind + $lookup tới products)
function Q5() {
  return db.orders.aggregate([
    { $match: { order_date: { $gte: d1, $lt: d2 }, status: { $nin: EXCL } } },
    { $unwind: "$items" },
    { $group: { _id: "$items.product_id",
                revenue: { $sum: { $multiply: ["$items.quantity", "$items.unit_price"] } } } },
    { $sort: { revenue: -1, _id: 1 } },
    { $limit: 10 },
    { $lookup: { from: "products", localField: "_id", foreignField: "_id", as: "p" } },
    { $unwind: "$p" },
    { $project: { _id: 0, product_id: "$_id", name: "$p.name", revenue: 1 } }
  ]).toArray();
}

// Q6 (3%) Doanh thu theo danh mục: gom theo sản phẩm trước rồi mới $lookup (giảm số lần join)
function Q6() {
  return db.orders.aggregate([
    { $match: { order_date: { $gte: d1, $lt: d2 }, status: { $nin: EXCL } } },
    { $unwind: "$items" },
    { $group: { _id: "$items.product_id",
                revenue: { $sum: { $multiply: ["$items.quantity", "$items.unit_price"] } } } },
    { $lookup: { from: "products", localField: "_id", foreignField: "_id", as: "p" } },
    { $unwind: "$p" },
    { $group: { _id: "$p.category_id", revenue: { $sum: "$revenue" } } },
    { $lookup: { from: "categories", localField: "_id", foreignField: "_id", as: "c" } },
    { $unwind: "$c" },
    { $project: { _id: 0, category_id: "$_id", name: "$c.name", revenue: 1 } },
    { $sort: { revenue: -1, category_id: 1 } }
  ]).toArray();
}

// Q7 (15%) Chi tiết đơn + tên khách + tên sản phẩm (2 loại tham chiếu => $lookup)
function Q7() {
  return db.orders.aggregate([
    { $match: { _id: oid } },
    { $lookup: { from: "customers", localField: "customer_id", foreignField: "_id", as: "cu" } },
    { $unwind: "$cu" },
    { $unwind: "$items" },
    { $lookup: { from: "products", localField: "items.product_id", foreignField: "_id", as: "p" } },
    { $unwind: "$p" },
    { $project: { _id: 0, order_id: "$_id", order_date: 1, status: 1,
                  full_name: "$cu.full_name", email: "$cu.email",
                  line_no: "$items.line_no", sku: "$p.sku", product_name: "$p.name",
                  quantity: "$items.quantity", unit_price: "$items.unit_price" } },
    { $sort: { line_no: 1 } }
  ]).toArray();
}

// Q8 (4%) Top 10 khách theo chi tiêu
function Q8() {
  return db.orders.aggregate([
    { $match: { order_date: { $gte: d1, $lt: d2 }, status: { $nin: EXCL } } },
    { $group: { _id: "$customer_id", spend: { $sum: orderTotal } } },
    { $sort: { spend: -1, _id: 1 } },
    { $limit: 10 },
    { $lookup: { from: "customers", localField: "_id", foreignField: "_id", as: "cu" } },
    { $unwind: "$cu" },
    { $project: { _id: 0, customer_id: "$_id", full_name: "$cu.full_name", spend: 1 } }
  ]).toArray();
}

// ---------------------------------------------------------------- GHI
// W1 (10%) Thêm đơn mới: 1 insert (đơn+items+payments nhúng) + trừ tồn kho.
// Phiên bản A (mặc định, không transaction): insert đơn là nguyên tử trên 1 document;
// trừ tồn kho dùng điều kiện quantity >= n để không âm.
// Một thân hàm dùng cho cả hai chế độ: truyền sdb = db (không transaction)
// hoặc session.getDatabase("shop_bench") (có transaction).
function W1_body(sdb, newOid, payId, storeId, lines /* [{pid, qty}] */) {
  const price = Object.fromEntries(
    sdb.products.find({ _id: { $in: lines.map(l => l.pid) } }).toArray()
       .map(p => [p._id, p.price]));
  const cents = d => Math.round(parseFloat(d.toString()) * 100);   // giá có tối đa 2 chữ số thập phân
  const totalCents = lines.reduce((t, l) => t + l.qty * cents(price[l.pid]), 0);
  sdb.orders.insertOne({ _id: newOid, customer_id: cid, store_id: storeId,
    order_date: new Date(), status: "PENDING",
    items: lines.map((l, k) => ({ line_no: k + 1, product_id: l.pid,
                                  quantity: l.qty, unit_price: price[l.pid] })),
    payments: [{ payment_id: payId, method: "CARD",
                 amount: NumberDecimal((totalCents / 100).toFixed(2)),
                 paid_at: null, status: "PENDING" }] });
  const r = sdb.inventory.bulkWrite(lines.map(l => ({ updateOne: {
    filter: { store_id: storeId, product_id: l.pid, quantity: { $gte: l.qty } },
    update: { $inc: { quantity: -l.qty } } } })));
  // Hết hàng: ném lỗi => transaction tự abort. Ở chế độ KHÔNG transaction, đơn đã
  // được chèn và phải bù trừ thủ công (đây là điểm khác biệt về nhất quán cần nêu trong báo cáo).
  if (r.modifiedCount !== lines.length) throw new Error("OUT_OF_STOCK");
}
function W1_noTxn(newOid, payId, storeId, lines) {
  return W1_body(db, newOid, payId, storeId, lines);
}
// Phiên bản B (có transaction đa-document, cần replica set) để so sánh công bằng
// với giao dịch ACID của MySQL:
function W1_txn(newOid, payId, storeId, lines) {
  const s = db.getMongo().startSession();
  try {
    s.withTransaction(
      () => W1_body(s.getDatabase("shop_bench"), newOid, payId, storeId, lines),
      { writeConcern: { w: "majority", j: true } });
  } finally { s.endSession(); }
}
// Khi viết harness đo thật (Python/pymongo) nên dùng cùng logic này, tính amount ở
// client bằng Decimal để amount == SUM(quantity*unit_price) như MySQL.

// W2 (7%) Cập nhật trạng thái đơn + payment đang PENDING (1 document => nguyên tử, không cần transaction)
function W2() {
  return db.orders.updateOne(
    { _id: oid, status: "PENDING" },
    { $set: { status: "PAID", "payments.$[p].status": "PAID", "payments.$[p].paid_at": new Date() } },
    { arrayFilters: [{ "p.status": "PENDING" }] });
}

// W3 (3%) Điều chỉnh tồn kho
function W3() {
  return db.inventory.updateOne({ store_id: 7, product_id: 1124 }, { $inc: { quantity: 50 } });
}

// ---------------------------------------------------------------- ĐỐI CHIẾU SAU NẠP
function verifyLoad() {
  const counts = {};
  ["categories", "stores", "customers", "products", "inventory", "orders"]
    .forEach(c => counts[c] = db[c].countDocuments());
  counts.order_item = db.orders.aggregate([{ $group: { _id: null, n: { $sum: { $size: "$items" } } } }]).toArray()[0].n;
  counts.payment    = db.orders.aggregate([{ $group: { _id: null, n: { $sum: { $size: "$payments" } } } }]).toArray()[0].n;
  const gross = db.orders.aggregate([{ $group: { _id: null, r: { $sum: orderTotal } } }]).toArray()[0].r;
  const byStatus = db.orders.aggregate([{ $group: { _id: "$status", n: { $sum: 1 } } }]).toArray();
  printjson({ counts, revenue_gross: gross.toString(), byStatus });   // so với manifest.json
}
