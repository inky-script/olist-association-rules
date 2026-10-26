# -*- coding: utf-8 -*-
"""
PHASE 1 - Nạp, kiểm tra chất lượng, ghép bảng và xử lý giá trị thiếu
Đề tài 5: Khai thác quan hệ mua kèm giữa các danh mục sản phẩm - Olist

Cách chạy:
    python src/phase1_preprocessing.py --data-dir data/raw --out-dir data/processed

Yêu cầu: tải bộ "Brazilian E-Commerce Public Dataset by Olist" từ Kaggle
(https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) và giải nén vào data/raw/.
File có thể mở trong VS Code/Jupyter theo từng cell (# %%).
"""

# %% 0. Thư viện & cấu hình
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 160)

FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "translation": "product_category_name_translation.csv",
}

# Hai danh mục có trong bảng products nhưng KHÔNG có trong bảng dịch (lỗi đã biết của dataset)
MANUAL_TRANSLATION = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_processors",
}

# Trạng thái đơn không phản ánh hành vi mua thực sự -> loại bỏ
EXCLUDED_STATUSES = ["canceled", "unavailable"]

UNKNOWN_CATEGORY = "unknown"


def parse_args():
    parser = argparse.ArgumentParser(description="Olist - Phase 1 preprocessing")
    parser.add_argument("--data-dir", default="data/raw", type=Path)
    parser.add_argument("--out-dir", default="data/processed", type=Path)
    # parse_known_args để chạy được cả trong Jupyter (kernel truyền thêm tham số -f)
    args, _ = parser.parse_known_args()
    return args


# %% 1. Nạp dữ liệu
def load_data(data_dir: Path) -> dict:
    missing = [f for f in FILES.values() if not (data_dir / f).exists()]
    if missing:
        raise FileNotFoundError(f"Thiếu file trong {data_dir.resolve()}: {missing}")

    date_cols = [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    dfs = {
        "orders": pd.read_csv(data_dir / FILES["orders"], parse_dates=date_cols),
        "order_items": pd.read_csv(data_dir / FILES["order_items"],
                                   parse_dates=["shipping_limit_date"]),
        "products": pd.read_csv(data_dir / FILES["products"]),
        # utf-8-sig: file dịch có BOM ở header, đọc thường sẽ ra cột "﻿product_category_name"
        "translation": pd.read_csv(data_dir / FILES["translation"], encoding="utf-8-sig"),
    }
    return dfs


# %% 2. Báo cáo chất lượng dữ liệu (dùng cho Mục 4 của báo cáo)
def quality_report(dfs: dict) -> pd.DataFrame:
    rows = []
    for name, df in dfs.items():
        rows.append({
            "table": name,
            "n_rows": len(df),
            "n_cols": df.shape[1],
            "n_duplicate_rows": int(df.duplicated().sum()),
            "n_cells_missing": int(df.isna().sum().sum()),
            "pct_cells_missing": round(df.isna().mean().mean() * 100, 2),
        })
    report = pd.DataFrame(rows)
    print("\n=== TỔNG QUAN CHẤT LƯỢNG DỮ LIỆU ===")
    print(report.to_string(index=False))

    for name, df in dfs.items():
        na = df.isna().sum()
        na = na[na > 0]
        if not na.empty:
            print(f"\n[{name}] cột có giá trị thiếu:")
            print(pd.DataFrame({"n_missing": na,
                                "pct": (na / len(df) * 100).round(2)}).to_string())
    return report


def check_keys(dfs: dict) -> None:
    """Kiểm tra tính duy nhất của khóa chính và toàn vẹn tham chiếu trước khi merge."""
    o, oi, p, t = dfs["orders"], dfs["order_items"], dfs["products"], dfs["translation"]
    print("\n=== KIỂM TRA KHÓA ===")
    print(f"orders.order_id duy nhất:                {o['order_id'].is_unique}")
    print(f"products.product_id duy nhất:            {p['product_id'].is_unique}")
    print(f"translation.product_category_name duy nhất: {t['product_category_name'].is_unique}")
    print(f"(order_id, order_item_id) duy nhất:      "
          f"{not oi.duplicated(['order_id', 'order_item_id']).any()}")
    print(f"order_items.product_id không có trong products: "
          f"{(~oi['product_id'].isin(p['product_id'])).sum()}")
    print(f"order_items.order_id không có trong orders:     "
          f"{(~oi['order_id'].isin(o['order_id'])).sum()}")
    untranslated = sorted(set(p["product_category_name"].dropna())
                          - set(t["product_category_name"]))
    print(f"Danh mục trong products chưa có bản dịch: {untranslated}")


# %% 3. Ghép bảng
def merge_tables(dfs: dict) -> pd.DataFrame:
    orders = dfs["orders"][["order_id", "customer_id", "order_status",
                            "order_purchase_timestamp"]]
    items = dfs["order_items"][["order_id", "order_item_id", "product_id",
                                "seller_id", "price", "freight_value"]]
    products = dfs["products"][["product_id", "product_category_name"]]
    translation = dfs["translation"]

    # order_items (N) -> products (1): khóa product_id
    df = items.merge(products, on="product_id", how="left", validate="many_to_one")
    # -> translation (1): khóa product_category_name
    df = df.merge(translation, on="product_category_name", how="left",
                  validate="many_to_one")
    # -> orders (1): khóa order_id; inner để chỉ giữ dòng có thông tin đơn hàng
    df = df.merge(orders, on="order_id", how="inner", validate="many_to_one")

    assert len(df) == len(items), "Số dòng thay đổi sau merge -> khóa bị nhân bản!"
    print(f"\n=== MERGE === {len(df):,} dòng x {df.shape[1]} cột (bằng số dòng order_items)")
    return df


# %% 4. Xử lý giá trị thiếu, lọc trạng thái, kiểm tra ngoại lệ
def handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n_no_cat = df["product_category_name"].isna().sum()

    # (a) Sản phẩm không có danh mục -> gán nhãn 'unknown' (giữ lại để thống kê,
    #     sẽ loại khỏi giỏ hàng ở Phase 2 vì không mang ý nghĩa danh mục)
    df["product_category_name"] = df["product_category_name"].fillna(UNKNOWN_CATEGORY)

    # (b) Danh mục có tên Bồ Đào Nha nhưng thiếu bản dịch -> bổ sung thủ công, sau đó
    #     fallback về tên gốc nếu vẫn thiếu
    mask = df["product_category_name_english"].isna()
    n_no_trans = (mask & (df["product_category_name"] != UNKNOWN_CATEGORY)).sum()
    df.loc[mask, "product_category_name_english"] = (
        df.loc[mask, "product_category_name"].map(MANUAL_TRANSLATION)
        .fillna(df.loc[mask, "product_category_name"])
    )
    df = df.rename(columns={"product_category_name_english": "category"})

    print("\n=== XỬ LÝ THIẾU ===")
    print(f"Dòng thiếu danh mục -> '{UNKNOWN_CATEGORY}': {n_no_cat:,}")
    print(f"Dòng thiếu bản dịch -> bổ sung thủ công/fallback: {n_no_trans:,}")
    print(f"Còn thiếu ở cột category: {df['category'].isna().sum()}")
    return df


def filter_orders(df: pd.DataFrame) -> pd.DataFrame:
    print("\n=== PHÂN BỐ TRẠNG THÁI ĐƠN (theo order_id) ===")
    print(df.drop_duplicates("order_id")["order_status"].value_counts().to_string())
    before = df["order_id"].nunique()
    df = df[~df["order_status"].isin(EXCLUDED_STATUSES)].copy()
    print(f"Loại {EXCLUDED_STATUSES}: {before:,} -> {df['order_id'].nunique():,} đơn")
    return df


def check_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Đánh dấu ngoại lệ giá theo IQR. KHÔNG xóa: khai thác luật kết hợp chỉ dựa vào
    sự xuất hiện của danh mục trong giỏ, giá cao không làm sai lệch transaction."""
    df = df.copy()
    print("\n=== NGOẠI LỆ GIÁ / PHÍ VẬN CHUYỂN ===")
    print(df[["price", "freight_value"]].describe().round(2).to_string())
    q1, q3 = df["price"].quantile([0.25, 0.75])
    upper = q3 + 1.5 * (q3 - q1)
    df["is_price_outlier"] = df["price"] > upper
    print(f"Ngưỡng IQR trên của price: {upper:.2f} BRL -> "
          f"{df['is_price_outlier'].sum():,} dòng ({df['is_price_outlier'].mean():.1%})")
    print(f"price <= 0: {(df['price'] <= 0).sum()} | freight_value < 0: "
          f"{(df['freight_value'] < 0).sum()}")
    return df


# %% 5. Thống kê giỏ hàng (tiền đề cho Phase 2)
def basket_stats(df: pd.DataFrame) -> None:
    known = df[df["category"] != UNKNOWN_CATEGORY]
    items_per_order = df.groupby("order_id").size()
    cats_per_order = known.groupby("order_id")["category"].nunique()

    print("\n=== THỐNG KÊ GIỎ HÀNG ===")
    print(f"Số đơn: {df['order_id'].nunique():,} | Số sản phẩm: {df['product_id'].nunique():,}"
          f" | Số danh mục (kể cả unknown): {df['category'].nunique()}")
    print(f"Số item/đơn: TB {items_per_order.mean():.2f}, max {items_per_order.max()}")
    print("Phân bố số danh mục KHÁC NHAU trong 1 đơn:")
    print(cats_per_order.value_counts().sort_index().to_string())
    multi = (cats_per_order >= 2).sum()
    print(f"-> Đơn có >= 2 danh mục: {multi:,} ({multi / len(cats_per_order):.2%})."
          " Đây là lý do minsup ở Phase 2 phải rất nhỏ hoặc lọc riêng giỏ đa danh mục.")
    print("\nTop 10 danh mục theo số đơn:")
    print(known.groupby("category")["order_id"].nunique()
          .sort_values(ascending=False).head(10).to_string())


# %% 6. Main
def main():
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    dfs = load_data(args.data_dir)
    report = quality_report(dfs)
    check_keys(dfs)

    df = merge_tables(dfs)
    df = handle_missing(df)
    df = filter_orders(df)
    df = check_outliers(df)
    basket_stats(df)

    out_file = args.out_dir / "order_items_clean.csv"
    df.to_csv(out_file, index=False)
    report.to_csv(args.out_dir / "data_quality_report.csv", index=False)
    print(f"\nĐã lưu: {out_file} ({len(df):,} dòng) và data_quality_report.csv")


if __name__ == "__main__":
    main()
