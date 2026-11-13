#!/usr/bin/env python3
"""
Sinh dữ liệu tổng hợp cho so sánh MySQL vs MongoDB (quản lý bán hàng).

- Chỉ dùng thư viện chuẩn Python 3.8+ (không cần cài thêm).
- Tái lập: cùng --seed và cùng tham số => đầu ra giống hệt nhau từng byte.
- Một lần sinh ghi ra CẢ HAI định dạng nên hai CSDL chứa cùng dữ liệu logic:
    <out>/<scale>/mysql/*.csv     (nạp bằng LOAD DATA)
    <out>/<scale>/mongo/*.jsonl   (nạp bằng mongoimport, Extended JSON)
    <out>/<scale>/manifest.json   (số dòng, doanh thu... để đối chiếu sau khi nạp)
- Phân phối lệch (Zipf): ít sản phẩm bán rất chạy, ít khách mua rất nhiều.

Ví dụ:
    python3 04_generate_data.py --scale s            # 100 nghìn đơn
    python3 04_generate_data.py --scale m            # 1 triệu đơn
    python3 04_generate_data.py --scale l            # 10 triệu đơn (~7 GB file thô; chưa tính dung lượng CSDL và index)
    python3 04_generate_data.py --orders 250000 --seed 7
"""
import argparse
import csv
import json
import os
import random
import time
from bisect import bisect
from collections import Counter
from datetime import datetime, timedelta
from itertools import accumulate

SCALES = {
    "s": dict(orders=100_000, customers=10_000, products=5_000),
    "m": dict(orders=1_000_000, customers=100_000, products=20_000),
    "l": dict(orders=10_000_000, customers=1_000_000, products=50_000),
}
N_STORES = 50
N_ROOT, N_SUB = 10, 5                       # 10 danh mục gốc x 5 danh mục con
STOCKED_STORES_PER_PRODUCT = 10
START = datetime(2024, 1, 1)
END = datetime(2026, 1, 1)                  # đơn hàng trải trên 2 năm
SPAN = int((END - START).total_seconds())
ZIPF_S_PRODUCT = 1.1                        # độ lệch sản phẩm
ZIPF_S_CUSTOMER = 0.7                       # độ lệch khách hàng (nhẹ hơn sản phẩm)

STATUS = (["PENDING", "PAID", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"],
          [5, 10, 10, 65, 7, 3])
METHOD = (["CARD", "EWALLET", "COD", "BANK_TRANSFER", "CASH"], [35, 30, 20, 10, 5])
N_ITEMS = ([1, 2, 3, 4, 5, 6, 7, 8], [30, 25, 18, 12, 7, 4, 3, 1])
QTY = ([1, 2, 3, 4, 5], [60, 20, 10, 6, 4])
ROOT_NAMES = ["Điện tử", "Thời trang", "Gia dụng", "Sách", "Thể thao",
              "Làm đẹp", "Đồ chơi", "Thực phẩm", "Văn phòng phẩm", "Ô tô - Xe máy"]
CITIES = (["Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ",
           "Huế", "Nha Trang", "Vinh", "Biên Hòa", "Buôn Ma Thuột"],
          [25, 30, 10, 8, 6, 4, 4, 4, 5, 4])
HO = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng"]
DEM = ["Văn", "Thị", "Minh", "Quốc", "Thanh", "Ngọc", "Hữu", "Đức", "Anh", "Gia"]
TEN = ["An", "Bình", "Châu", "Dũng", "Hà", "Hùng", "Lan", "Linh", "Nam", "Phúc",
       "Quang", "Sơn", "Thảo", "Trang", "Tuấn", "Việt"]
ADJ = ["Cao cấp", "Tiết kiệm", "Chính hãng", "Mini", "Pro", "Lite", "Classic", "Plus"]
NOUN = ["Tai nghe", "Áo thun", "Nồi cơm", "Sách kỹ năng", "Giày chạy", "Kem dưỡng",
        "Mô hình", "Bánh quy", "Bút bi", "Phụ kiện xe"]


def money(cents):
    return f"{cents // 100}.{cents % 100:02d}"


def ts_csv(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def ts_json(dt):
    return {"$date": dt.strftime("%Y-%m-%dT%H:%M:%SZ")}


def dec(cents):
    return {"$numberDecimal": money(cents)}


def cum(weights):
    return list(accumulate(weights))


def wpick(rng, vals, cw):
    return vals[bisect(cw, rng.random() * cw[-1])]


def zipf_table(n, s, rng):
    """Trả về (ids đã xáo trộn, trọng số cộng dồn). Xáo trộn để độ 'hot'
    không tương quan với thứ tự khoá chính."""
    ids = list(range(1, n + 1))
    rng.shuffle(ids)
    return ids, cum([1.0 / (r ** s) for r in range(1, n + 1)])


def jdump(f, obj):
    f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    f.write("\n")


def opener(path):
    return open(path, "w", newline="", encoding="utf-8", buffering=1 << 20)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", choices=SCALES, default="s")
    ap.add_argument("--orders", type=int, help="ghi đè số đơn hàng (tuỳ chỉnh quy mô)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data")
    a = ap.parse_args()

    if a.orders:
        cfg = dict(orders=a.orders, customers=max(1000, a.orders // 10),
                   products=max(2000, min(50_000, a.orders // 20)))
        label = f"custom_{a.orders}"
    else:
        cfg, label = SCALES[a.scale], a.scale
    n_ord, n_cus, n_prd = cfg["orders"], cfg["customers"], cfg["products"]

    base = os.path.join(a.out, label)
    my, mo = os.path.join(base, "mysql"), os.path.join(base, "mongo")
    os.makedirs(my, exist_ok=True)
    os.makedirs(mo, exist_ok=True)
    seed = a.seed
    # Mỗi thực thể một luồng ngẫu nhiên riêng: đổi số lượng đơn không làm đổi danh mục/sản phẩm.
    R = lambda name: random.Random(f"{seed}:{name}")
    t0 = time.time()

    # ---------------- danh mục ----------------
    with opener(f"{my}/category.csv") as fc, opener(f"{mo}/categories.jsonl") as fj:
        w = csv.writer(fc)
        cid = 0
        for r in range(1, N_ROOT + 1):
            cid += 1
            w.writerow([cid, ROOT_NAMES[r - 1], "\\N"])
            jdump(fj, {"_id": cid, "name": ROOT_NAMES[r - 1], "parent_id": None})
        for r in range(1, N_ROOT + 1):
            for k in range(1, N_SUB + 1):
                cid += 1
                nm = f"{ROOT_NAMES[r - 1]} - Loại {k}"
                w.writerow([cid, nm, r])
                jdump(fj, {"_id": cid, "name": nm, "parent_id": r})
    leaf_ids = list(range(N_ROOT + 1, N_ROOT + N_ROOT * N_SUB + 1))

    # ---------------- cửa hàng ----------------
    rs = R("stores")
    with opener(f"{my}/store.csv") as fc, opener(f"{mo}/stores.jsonl") as fj:
        w = csv.writer(fc)
        for s in range(1, N_STORES + 1):
            city = wpick(rs, CITIES[0], cum(CITIES[1]))
            w.writerow([s, f"Cửa hàng {s:02d}", city])
            jdump(fj, {"_id": s, "name": f"Cửa hàng {s:02d}", "city": city})

    # ---------------- khách hàng ----------------
    rc = R("customers")
    c_cw = cum(CITIES[1])
    t_lo, t_hi = datetime(2023, 1, 1), START
    span_c = int((t_hi - t_lo).total_seconds())
    with opener(f"{my}/customer.csv") as fc, opener(f"{mo}/customers.jsonl") as fj:
        w = csv.writer(fc)
        for i in range(1, n_cus + 1):
            name = f"{rc.choice(HO)} {rc.choice(DEM)} {rc.choice(TEN)}"
            email, phone = f"user{i}@example.com", "09" + "".join(rc.choices("0123456789", k=8))
            city = wpick(rc, CITIES[0], c_cw)
            created = t_lo + timedelta(seconds=rc.randrange(span_c))
            w.writerow([i, name, email, phone, city, ts_csv(created)])
            jdump(fj, {"_id": i, "full_name": name, "email": email, "phone": phone,
                       "city": city, "created_at": ts_json(created)})

    # ---------------- sản phẩm + tồn kho ----------------
    rp = R("products")
    price = [0] * (n_prd + 1)                     # đơn vị: cent (số nguyên, tránh sai số float)
    with opener(f"{my}/product.csv") as fp, opener(f"{mo}/products.jsonl") as fpj, \
            opener(f"{my}/inventory.csv") as fi, opener(f"{mo}/inventory.jsonl") as fij:
        wp, wi = csv.writer(fp), csv.writer(fi)
        inv_id = 0
        for i in range(1, n_prd + 1):
            cents = max(100, int(rp.lognormvariate(3.5, 1.0) * 100))
            price[i] = cents
            cat = rp.choice(leaf_ids)
            nm = f"{rp.choice(NOUN)} {rp.choice(ADJ)} #{i}"
            sku = f"SKU{i:08d}"
            created = t_lo + timedelta(seconds=rp.randrange(span_c))
            wp.writerow([i, sku, nm, cat, money(cents), ts_csv(created)])
            jdump(fpj, {"_id": i, "sku": sku, "name": nm, "category_id": cat,
                        "price": dec(cents), "created_at": ts_json(created)})
            for s in sorted(rp.sample(range(1, N_STORES + 1), STOCKED_STORES_PER_PRODUCT)):
                inv_id += 1
                q = rp.randint(0, 500)
                wi.writerow([s, i, q])
                jdump(fij, {"_id": inv_id, "store_id": s, "product_id": i, "quantity": q})
    n_inv = inv_id

    # ---------------- đơn hàng, chi tiết, thanh toán ----------------
    ro = R("orders")
    rz = R("zipf")
    prod_ids, prod_cw = zipf_table(n_prd, ZIPF_S_PRODUCT, rz)
    cust_ids, cust_cw = zipf_table(n_cus, ZIPF_S_CUSTOMER, rz)
    st_cw, me_cw = cum(STATUS[1]), cum(METHOD[1])
    ni_cw, qt_cw = cum(N_ITEMS[1]), cum(QTY[1])

    cust_cnt, prod_cnt, st_cnt = Counter(), Counter(), Counter()
    n_items_total = n_pay_total = 0
    rev_gross = rev_net = 0
    pay_id = 0
    first_dt = last_dt = None

    with opener(f"{my}/orders.csv") as fo, opener(f"{my}/order_item.csv") as fit, \
            opener(f"{my}/payment.csv") as fpay, opener(f"{mo}/orders.jsonl") as fj:
        wo, wit, wpay = csv.writer(fo), csv.writer(fit), csv.writer(fpay)
        for oid in range(1, n_ord + 1):
            cid = ro.choices(cust_ids, cum_weights=cust_cw)[0]
            sid = ro.randint(1, N_STORES)
            dt = START + timedelta(seconds=int((oid - 1 + ro.random()) * SPAN / n_ord))
            status = wpick(ro, STATUS[0], st_cw)
            k = wpick(ro, N_ITEMS[0], ni_cw)

            pids, seen = [], set()
            while len(pids) < k:
                for p in ro.choices(prod_ids, cum_weights=prod_cw, k=k + 2):
                    if p not in seen:
                        seen.add(p)
                        pids.append(p)
                        if len(pids) == k:
                            break

            items, total = [], 0
            for ln, pid in enumerate(pids, 1):
                q = wpick(ro, QTY[0], qt_cw)
                up = price[pid]
                total += q * up
                items.append({"line_no": ln, "product_id": pid, "quantity": q,
                              "unit_price": dec(up)})
                wit.writerow([oid, ln, pid, q, money(up)])
                prod_cnt[pid] += 1

            # thanh toán: 95% một lần, 5% chia làm hai lần (đơn đủ lớn)
            parts = [total]
            if total >= 200 and ro.random() < 0.05:
                half = total // 2
                parts = [half, total - half]
            if status == "PENDING":
                pst, paid = "PENDING", None
            elif status in ("PAID", "SHIPPED", "DELIVERED"):
                pst, paid = "PAID", dt + timedelta(seconds=ro.randint(0, 3600))
            elif status == "CANCELLED":
                if ro.random() < 0.5:
                    pst, paid = "FAILED", None
                else:
                    pst, paid = "REFUNDED", dt + timedelta(seconds=ro.randint(0, 3600))
            else:  # RETURNED
                pst, paid = "REFUNDED", dt + timedelta(seconds=ro.randint(0, 3600))
            pays = []
            for amt in parts:
                pay_id += 1
                m = wpick(ro, METHOD[0], me_cw)
                pays.append({"payment_id": pay_id, "method": m, "amount": dec(amt),
                             "paid_at": ts_json(paid) if paid else None, "status": pst})
                wpay.writerow([pay_id, oid, m, money(amt),
                               ts_csv(paid) if paid else "\\N", pst])

            wo.writerow([oid, cid, sid, ts_csv(dt), status])
            jdump(fj, {"_id": oid, "customer_id": cid, "store_id": sid,
                       "order_date": ts_json(dt), "status": status,
                       "items": items, "payments": pays})

            cust_cnt[cid] += 1
            st_cnt[status] += 1
            n_items_total += k
            n_pay_total += len(parts)
            rev_gross += total
            if status not in ("CANCELLED", "RETURNED"):
                rev_net += total
            first_dt = first_dt or dt
            last_dt = dt
            if oid % 500_000 == 0:
                print(f"  ... {oid:,}/{n_ord:,} đơn ({time.time() - t0:.0f}s)", flush=True)

    # ---------------- manifest ----------------
    def top_share(counter, universe, frac=0.01):
        k = max(1, int(universe * frac))
        top = sum(v for _, v in counter.most_common(k))
        return round(top / sum(counter.values()), 4)

    manifest = {
        "seed": seed, "scale": label,
        "counts": {"category": N_ROOT + N_ROOT * N_SUB, "store": N_STORES,
                   "customer": n_cus, "product": n_prd, "inventory": n_inv,
                   "orders": n_ord, "order_item": n_items_total, "payment": n_pay_total},
        "date_range": [ts_csv(first_dt), ts_csv(last_dt)],
        "orders_by_status": dict(st_cnt),
        "revenue_gross": money(rev_gross),
        "revenue_net_excluding_cancelled_returned": money(rev_net),
        "skew": {
            "zipf_s_product": ZIPF_S_PRODUCT, "zipf_s_customer": ZIPF_S_CUSTOMER,
            "top1pct_products_share_of_order_lines": top_share(prod_cnt, n_prd),
            "top1pct_customers_share_of_orders": top_share(cust_cnt, n_cus),
            "max_orders_single_customer": cust_cnt.most_common(1)[0][1],
            "hot_customer_id": cust_cnt.most_common(1)[0][0],
            "hot_product_id": prod_cnt.most_common(1)[0][0],
        },
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    with open(os.path.join(base, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
