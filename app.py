# -*- coding: utf-8 -*-
"""
PHASE 3 - Ứng dụng demo Streamlit: gợi ý mua kèm giữa các danh mục sản phẩm Olist
Đề tài 5: Khai thác quan hệ mua kèm giữa các danh mục sản phẩm - Olist

Chạy:   streamlit run app.py
Cần:    models/rules.csv (sinh ra bởi src/phase2_mining.py)
Tùy chọn: data/processed/order_items_clean.csv (Phase 1) để khai thác lại trực tiếp trong app,
          outputs/tables/benchmark_*.csv (Phase 2) để xem tab so sánh thuật toán.
"""
import sys
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from packaging.version import Version

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

RULES_FILE = ROOT / "models" / "rules.csv"
CLEAN_FILE = ROOT / "data" / "processed" / "order_items_clean.csv"
TABLE_DIR = ROOT / "outputs" / "tables"

SOURCE_PRECOMPUTED = "Luật đã khai thác sẵn (Phase 2)"
SOURCE_LIVE = "Khai thác trực tiếp trong app"
SORT_OPTIONS = {"Lift": "lift", "Confidence": "confidence", "Support": "support"}

# Streamlit >= 1.46 thay use_container_width bằng width="stretch"
STRETCH = ({"width": "stretch"} if Version(st.__version__) >= Version("1.46")
           else {"use_container_width": True})

st.set_page_config(page_title="Olist – Gợi ý mua kèm", page_icon="🛒", layout="wide")


# ----------------------------------------------------------------------------
# Nạp & chuẩn hóa luật
# ----------------------------------------------------------------------------
def pretty(category: str) -> str:
    """bed_bath_table -> Bed Bath Table"""
    return category.replace("_", " ").title()


def prepare_rules(rules: pd.DataFrame) -> pd.DataFrame:
    """Bổ sung cột tập hợp để so khớp nhanh với giỏ hàng của người dùng."""
    rules = rules.copy()
    rules["ant_set"] = rules["antecedents_str"].str.split(", ").apply(frozenset)
    rules["cons_set"] = rules["consequents_str"].str.split(", ").apply(frozenset)
    rules["ant_len"] = rules["ant_set"].apply(len)
    return rules


@st.cache_data(show_spinner=False)
def load_precomputed(path: str) -> pd.DataFrame:
    return prepare_rules(pd.read_csv(path))


@st.cache_data(show_spinner=False)
def mine_live(path: str, algorithm: str, minsup: float, min_conf: float):
    """Chạy lại Apriori/FP-Growth trên dữ liệu đã làm sạch (Phase 1)."""
    from mlxtend.frequent_patterns import apriori, fpgrowth
    from phase2_mining import build_transactions, encode, make_rules, to_text

    df = pd.read_csv(path, usecols=["order_id", "category"])
    onehot = encode(build_transactions(df))
    func = apriori if algorithm == "Apriori" else fpgrowth

    t0 = time.perf_counter()
    freq = func(onehot, min_support=minsup, use_colnames=True, max_len=3)
    runtime = time.perf_counter() - t0

    rules = make_rules(freq, len(onehot), min_conf)
    if rules.empty:
        return pd.DataFrame(), runtime, len(freq), len(onehot)
    rules["pair_count"] = (rules["support"] * len(onehot)).round().astype(int)
    rules["antecedents_str"] = rules["antecedents"].apply(to_text)
    rules["consequents_str"] = rules["consequents"].apply(to_text)
    rules["rule"] = rules["antecedents_str"] + "  →  " + rules["consequents_str"]
    rules = rules.drop(columns=["antecedents", "consequents"])
    return prepare_rules(rules[rules["lift"] > 1]), runtime, len(freq), len(onehot)


def all_categories(rules: pd.DataFrame) -> list:
    cats = set().union(*rules["ant_set"]) | set().union(*rules["cons_set"])
    return sorted(cats)


# ----------------------------------------------------------------------------
# Logic gợi ý
# ----------------------------------------------------------------------------
def recommend(rules: pd.DataFrame, cart: set, min_conf: float, min_lift: float,
              min_count: int, sort_by: str, top_n: int) -> pd.DataFrame:
    """Gợi ý = các luật có tiền đề nằm TRỌN trong giỏ hàng và hệ quả CHƯA có trong giỏ.
    Mỗi danh mục gợi ý chỉ giữ luật mạnh nhất (theo tiêu chí sắp xếp)."""
    if not cart:
        return pd.DataFrame()
    mask = (rules["ant_set"].apply(lambda a: a <= cart)
            & rules["cons_set"].apply(lambda c: not (c & cart))
            & (rules["confidence"] >= min_conf)
            & (rules["lift"] >= min_lift)
            & (rules["pair_count"] >= min_count))
    matched = rules[mask].copy()
    if matched.empty:
        return matched

    # Luật có hệ quả nhiều danh mục -> tách để mỗi dòng là 1 danh mục được gợi ý
    matched["recommend"] = matched["cons_set"].apply(sorted)
    matched = matched.explode("recommend")
    best = (matched.sort_values([sort_by, "confidence"], ascending=False)
            .drop_duplicates("recommend")
            .head(top_n).reset_index(drop=True))
    best.index = best.index + 1
    return best


def explain(row) -> str:
    base = ", ".join(pretty(c) for c in sorted(row["ant_set"]))
    return (f"Khách mua **{base}** có **{row['confidence']:.1%}** khả năng mua thêm "
            f"**{pretty(row['recommend'])}** — cao gấp **{row['lift']:.1f} lần** so với "
            f"mức mua ngẫu nhiên (dựa trên {int(row['pair_count'])} đơn).")


def show_recommendations(recs: pd.DataFrame, sort_label: str, key: str) -> None:
    if recs.empty:
        st.warning("Không có gợi ý nào thỏa các ngưỡng hiện tại. "
                   "Hãy thử giảm Confidence/Lift/Số đơn tối thiểu ở thanh bên trái.")
        return

    top3 = recs.head(3)
    cols = st.columns(len(top3))
    for col, (_, r) in zip(cols, top3.iterrows()):
        col.metric(label=f"🎯 {pretty(r['recommend'])}", value=f"Lift {r['lift']:.2f}",
                   delta=f"Confidence {r['confidence']:.1%}")

    left, right = st.columns([1.1, 1])
    with left:
        chart_df = recs.assign(label=recs["recommend"].map(pretty)).iloc[::-1]
        fig = px.bar(chart_df, x="lift", y="label", orientation="h", color="confidence",
                     color_continuous_scale="Blues", text=chart_df["lift"].round(2),
                     labels={"lift": "Lift", "label": "", "confidence": "Confidence"},
                     title=f"Danh mục gợi ý mua kèm (xếp theo {sort_label})")
        fig.add_vline(x=1, line_dash="dash", line_color="gray",
                      annotation_text="Lift = 1 (độc lập)")
        fig.update_layout(height=max(320, 42 * len(chart_df) + 120), margin=dict(l=10, r=10))
        st.plotly_chart(fig, key=f"{key}_chart", **STRETCH)
    with right:
        st.markdown("**Diễn giải cho đội Marketing**")
        for _, r in recs.head(5).iterrows():
            st.markdown(f"- {explain(r)}")

    table = recs.assign(
        recommend=recs["recommend"].map(pretty),
        based_on=recs["ant_set"].apply(lambda s: ", ".join(pretty(c) for c in sorted(s))),
    )[["recommend", "based_on", "support", "pair_count", "confidence", "lift"]]
    st.dataframe(
        table, key=f"{key}_table", **STRETCH,
        column_config={
            "recommend": "Danh mục gợi ý",
            "based_on": "Dựa trên (tiền đề)",
            "support": st.column_config.NumberColumn("Support", format="%.5f"),
            "pair_count": st.column_config.NumberColumn("Số đơn", format="%d"),
            "confidence": st.column_config.ProgressColumn(
                "Confidence", format="%.3f", min_value=0.0,
                max_value=float(max(table["confidence"].max(), 1e-9))),
            "lift": st.column_config.NumberColumn("Lift", format="%.2f"),
        })


# ----------------------------------------------------------------------------
# Giao diện
# ----------------------------------------------------------------------------
st.title("🛒 Gợi ý mua kèm danh mục sản phẩm – Olist")
st.caption("Đề tài 5 · Thực hành Khai thác dữ liệu · Luật kết hợp Apriori & FP-Growth "
           "trên Brazilian E-Commerce Public Dataset by Olist")

# ---- Sidebar: nguồn luật & ngưỡng lọc
with st.sidebar:
    st.header("⚙️ Cấu hình")
    source = st.radio("Nguồn luật kết hợp", [SOURCE_PRECOMPUTED, SOURCE_LIVE])

    rules = pd.DataFrame()
    if source == SOURCE_PRECOMPUTED:
        if RULES_FILE.exists():
            rules = load_precomputed(str(RULES_FILE))
            st.success(f"Đã nạp {len(rules):,} luật từ `models/rules.csv`")
        else:
            st.error("Chưa có `models/rules.csv`. Hãy chạy `python src/phase2_mining.py` trước.")
    else:
        if not CLEAN_FILE.exists():
            st.error("Chưa có `data/processed/order_items_clean.csv`. "
                     "Hãy chạy `python src/phase1_preprocessing.py` trước.")
        else:
            algorithm = st.selectbox("Thuật toán", ["FP-Growth", "Apriori"])
            minsup = st.select_slider(
                "minsup", options=[0.01, 0.005, 0.002, 0.001, 0.0005, 0.0003, 0.0002, 0.0001],
                value=0.0005, format_func=lambda v: f"{v:g}")
            live_conf = st.slider("Confidence tối thiểu khi sinh luật", 0.0, 0.5, 0.01, 0.01)
            with st.spinner(f"Đang chạy {algorithm}..."):
                rules, runtime, n_freq, n_tx = mine_live(str(CLEAN_FILE), algorithm,
                                                         minsup, live_conf)
            st.success(f"{algorithm}: {runtime:.2f}s · {n_freq:,} tập phổ biến · "
                       f"{len(rules):,} luật (lift > 1) trên {n_tx:,} giỏ")

    st.divider()
    st.subheader("🔎 Ngưỡng lọc gợi ý")
    min_conf = st.slider("Confidence tối thiểu", 0.0, 1.0, 0.0, 0.01)
    min_lift = st.slider("Lift tối thiểu", 1.0, 20.0, 1.2, 0.1,
                         help="Lift ≈ 1 nghĩa là hai danh mục gần như độc lập → không nên gợi ý.")
    min_count = st.number_input("Số đơn tối thiểu chứa cả hai vế", 1, 1000, 10,
                                help="Loại các luật chỉ xuất hiện trong rất ít đơn (dễ ngẫu nhiên).")
    sort_label = st.selectbox("Xếp hạng theo", list(SORT_OPTIONS))
    top_n = st.slider("Số gợi ý tối đa", 3, 20, 10)

if rules.empty:
    st.info("Chưa có luật để hiển thị. Xem hướng dẫn ở thanh bên trái.")
    st.stop()

categories = all_categories(rules)
sort_by = SORT_OPTIONS[sort_label]

# Danh mục mặc định = danh mục làm tiền đề cho nhiều luật thỏa ngưỡng nhất,
# để màn hình đầu tiên luôn có gợi ý minh họa
strong = rules[(rules["ant_len"] == 1) & (rules["confidence"] >= min_conf)
               & (rules["lift"] >= min_lift) & (rules["pair_count"] >= min_count)]
default_cat = (strong["antecedents_str"].value_counts().index[0] if len(strong)
               else categories[0])

tab_cat, tab_cart, tab_rules, tab_algo, tab_help = st.tabs(
    ["🎯 Gợi ý theo danh mục", "🧺 Gợi ý theo giỏ hàng", "📋 Khám phá luật",
     "⚡ So sánh thuật toán", "ℹ️ Hướng dẫn"])

# ---- Tab 1: chọn 1 danh mục
with tab_cat:
    st.subheader("Khách hàng đang xem / vừa mua danh mục nào?")
    chosen = st.selectbox("Chọn danh mục sản phẩm", categories,
                          index=categories.index(default_cat), format_func=pretty)
    recs = recommend(rules, {chosen}, min_conf, min_lift, min_count, sort_by, top_n)
    show_recommendations(recs, sort_label, key="by_category")

# ---- Tab 2: giỏ hàng nhiều danh mục
with tab_cart:
    st.subheader("Mô phỏng giỏ hàng nhiều danh mục")
    st.caption("Hệ thống dùng cả luật 1 → 1 và luật 2 → 1 có tiền đề nằm trọn trong giỏ, "
               "đồng thời bỏ qua các danh mục đã có trong giỏ.")
    cart = st.multiselect("Các danh mục đang có trong giỏ", categories,
                          default=[default_cat], format_func=pretty)
    recs = recommend(rules, set(cart), min_conf, min_lift, min_count, sort_by, top_n)
    show_recommendations(recs, sort_label, key="by_cart")

# ---- Tab 3: khám phá toàn bộ luật
with tab_rules:
    st.subheader("Toàn bộ luật thỏa ngưỡng")
    keyword = st.text_input("Lọc theo tên danh mục (vd: furniture, health)").strip().lower()
    view = rules[(rules["confidence"] >= min_conf) & (rules["lift"] >= min_lift)
                 & (rules["pair_count"] >= min_count)]
    if keyword:
        view = view[view["rule"].str.lower().str.contains(keyword, regex=False)]
    view = view.sort_values(sort_by, ascending=False)

    c1, c2, c3 = st.columns(3)
    c1.metric("Số luật", f"{len(view):,}")
    c2.metric("Lift trung vị", f"{view['lift'].median():.2f}" if len(view) else "–")
    c3.metric("Confidence trung vị", f"{view['confidence'].median():.1%}" if len(view) else "–")

    if len(view):
        fig = px.scatter(view, x="support", y="confidence", color="lift", size="pair_count",
                         hover_name="rule", log_x=True, color_continuous_scale="Viridis",
                         title="Support vs Confidence (màu = Lift, kích thước = số đơn)")
        st.plotly_chart(fig, **STRETCH)
    cols = ["rule", "support", "pair_count", "confidence", "lift", "leverage", "conviction"]
    st.dataframe(view[[c for c in cols if c in view.columns]], **STRETCH, hide_index=True)
    st.download_button("⬇️ Tải các luật (CSV)",
                       view.drop(columns=["ant_set", "cons_set"]).to_csv(index=False)
                       .encode("utf-8-sig"),
                       file_name="olist_association_rules.csv", mime="text/csv")

# ---- Tab 4: kết quả benchmark của Phase 2
with tab_algo:
    st.subheader("Apriori vs FP-Growth")
    bench_file = TABLE_DIR / "benchmark_apriori_vs_fpgrowth.csv"
    if not bench_file.exists():
        st.info("Chưa có kết quả benchmark. Hãy chạy `python src/phase2_mining.py`.")
    else:
        bench = pd.read_csv(bench_file)
        names = {"all": "Toàn bộ giỏ hàng", "multi": "Giỏ có ≥ 2 danh mục"}
        scenario = st.radio("Kịch bản", list(names), format_func=names.get, horizontal=True)
        b = bench[bench["scenario"] == scenario]
        long = b.melt(id_vars="minsup", value_vars=["apriori_sec", "fpgrowth_sec"],
                      var_name="Thuật toán", value_name="Thời gian (s)")
        long["Thuật toán"] = long["Thuật toán"].map({"apriori_sec": "Apriori",
                                                     "fpgrowth_sec": "FP-Growth"})
        left, right = st.columns(2)
        fig = px.line(long, x="minsup", y="Thời gian (s)", color="Thuật toán", markers=True,
                      log_x=True, title="Thời gian chạy theo minsup")
        fig.update_xaxes(autorange="reversed", exponentformat="none")
        left.plotly_chart(fig, **STRETCH)
        rule_col = [c for c in b.columns if c.startswith("n_rules_lift")][0]
        counts = b.assign(minsup_label=b["minsup"].map(lambda v: f"{v:g}")).melt(
            id_vars="minsup_label", value_vars=["n_itemsets", rule_col])
        counts["variable"] = counts["variable"].map(
            {"n_itemsets": "Số tập phổ biến", rule_col: f"Số luật ({rule_col[8:]})"})
        fig = px.bar(counts, x="minsup_label", y="value", color="variable",
                     barmode="group", title="Số tập phổ biến và số luật",
                     labels={"minsup_label": "minsup", "value": "Số lượng", "variable": ""})
        fig.update_xaxes(type="category")  # nhãn minsup là chuỗi, tránh plotly hiểu thành số
        right.plotly_chart(fig, **STRETCH)
        st.dataframe(b, **STRETCH, hide_index=True)

    product_file = TABLE_DIR / "benchmark_product_level.csv"
    if product_file.exists():
        st.markdown("#### Thí nghiệm mở rộng ở mức sản phẩm (product_id)")
        pb = pd.read_csv(product_file)
        long = pb.melt(id_vars="min_count", value_vars=["apriori_sec", "fpgrowth_sec"],
                       var_name="Thuật toán", value_name="Thời gian (s)").dropna()
        long["Thuật toán"] = long["Thuật toán"].map({"apriori_sec": "Apriori",
                                                     "fpgrowth_sec": "FP-Growth"})
        long["min_count"] = long["min_count"].astype(str)
        fig = px.line(long, x="min_count", y="Thời gian (s)", color="Thuật toán",
                      markers=True, log_y=True,
                      title="Mức sản phẩm: Apriori bùng nổ ứng viên khi ngưỡng giảm")
        st.plotly_chart(fig, **STRETCH)
        st.dataframe(pb, **STRETCH, hide_index=True)

# ---- Tab 5: hướng dẫn & ý nghĩa độ đo
with tab_help:
    st.markdown("""
**Luồng xử lý:** Dữ liệu Olist → ghép `order_items` + `products` + bảng dịch theo khóa
→ transaction theo `order_id` → one-hot → Apriori / FP-Growth → luật kết hợp → lọc → gợi ý.

| Độ đo | Công thức | Ý nghĩa kinh doanh |
|---|---|---|
| **Support** | P(A ∪ B) | Tỷ lệ đơn chứa cả A và B – mức phổ biến của cặp |
| **Confidence** | P(B \\| A) | Trong các đơn có A, bao nhiêu % có B – xác suất mua kèm |
| **Lift** | Confidence / P(B) | > 1: mua A làm *tăng* khả năng mua B; ≈ 1: độc lập; < 1: thay thế |

**Cách dùng:** chọn danh mục (hoặc giỏ hàng) → hệ thống trả về các danh mục nên gợi ý mua kèm,
xếp hạng theo Lift/Confidence/Support. Các ngưỡng ở thanh bên trái giúp loại luật yếu
(lift ≈ 1) hoặc luật chỉ dựa trên rất ít đơn hàng.
""")
