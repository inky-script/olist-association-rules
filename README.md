# Đề tài 5 – Khai thác quan hệ mua kèm giữa các danh mục sản phẩm (Olist)

Đồ án môn Thực hành Khai thác dữ liệu – HUIT.

## Cấu trúc thư mục

```
olist-association-rules/
├── app.py                      # Phase 3 – ứng dụng demo Streamlit
├── requirements.txt
├── src/
│   ├── phase1_preprocessing.py # nạp, kiểm tra khóa, merge, xử lý thiếu/ngoại lệ
│   └── phase2_mining.py        # transaction, one-hot, Apriori vs FP-Growth, luật
├── data/
│   ├── raw/                    # đặt 4 file CSV của Olist vào đây
│   └── processed/              # sinh bởi Phase 1
├── outputs/{tables,figures}/   # sinh bởi Phase 2 (bảng + biểu đồ cho báo cáo)
└── models/rules.csv            # sinh bởi Phase 2, app dùng để gợi ý
```

## Cách chạy

1. Tải dataset tại https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce và giải nén
   4 file `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`,
   `olist_products_dataset.csv`, `product_category_name_translation.csv` vào `data/raw/`.
2. Cài thư viện (khuyến nghị dùng môi trường ảo):
   ```
   pip install -r requirements.txt
   ```
3. Chạy lần lượt:
   ```
   python src/phase1_preprocessing.py
   python src/phase2_mining.py
   streamlit run app.py
   ```
   Phase 2 có benchmark ở minsup rất nhỏ nên có thể mất 10–20 phút.
