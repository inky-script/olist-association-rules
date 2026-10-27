# -*- coding: utf-8 -*-
"""
PHASE 2 - Tạo Transaction/One-hot, chạy Apriori & FP-Growth, so sánh hiệu năng,
sinh luật kết hợp và xuất Top 20 luật có giá trị.
Đề tài 5: Khai thác quan hệ mua kèm giữa các danh mục sản phẩm - Olist

Cách chạy (sau Phase 1):
    python src/phase2_mining.py --in-file data/processed/order_items_clean.csv

Đầu ra:
    outputs/tables/*.csv   - bảng benchmark, tập phổ biến, luật, top 20 luật
    outputs/figures/*.png  - biểu đồ dùng cho Mục 5, 7, 8 của báo cáo
    models/rules.csv       - luật (2 chiều) dùng cho app Streamlit ở Phase 3
"""

# %% 0. Thư viện & cấu hình
import argparse
import gc
import inspect
import json
import os
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # lưu ảnh, không cần màn hình
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder

UNKNOWN_CATEGORY = "unknown"
N_REPEATS = 3            # số lần chạy lặp để lấy runtime trung vị (giảm nhiễu)
MAX_LEN = 3              # độ dài itemset tối đa (danh mục/giỏ rất ít -> 3 là đủ)

# Dải minsup khảo sát cho từng kịch bản (support tương đối)
# - ALL  : toàn bộ giỏ hàng -> đa số giỏ chỉ 1 danh mục nên cặp danh mục có support rất nhỏ
# - MULTI: chỉ giỏ có >= 2 danh mục -> support của cặp lớn hơn nhiều
MINSUP_GRID = {
    "all":   [0.01, 0.005, 0.002, 0.001, 0.0005, 0.0003, 0.0002, 0.0001],
    "multi": [0.10, 0.05, 0.03, 0.02, 0.01, 0.007, 0.005, 0.003],
}
MIN_CONF_BENCH = 0.01    # confidence tối thiểu khi đếm số luật trong benchmark

# Tham số sinh luật cuối cùng. Dùng kịch bản MULTI: trên dữ liệu thật > 99% đơn chỉ có
# 1 danh mục nên ở kịch bản ALL lift của gần như mọi cặp < 1 (do khách hiếm mua 2 danh mục
# cùng lúc, không phải do 2 danh mục không liên quan). Xét riêng giỏ đa danh mục mới đo
# được danh mục nào "đi cùng nhau" hơn ngẫu nhiên. Bảng pair_lift_all_vs_multi.csv minh họa.
FINAL_SCENARIO = "multi"
FINAL_MINSUP = 0.005     # ~4 đơn trên ~700 giỏ đa danh mục
FINAL_MIN_CONF = 0.05
MIN_LIFT = 1.2           # loại luật có lift xấp xỉ 1 (A và B gần như độc lập)
MIN_PAIR_COUNT = 5       # luật phải xuất hiện trong >= 5 đơn, tránh luật ngẫu nhiên
TOP_K = 20

# Thí nghiệm mở rộng ở mức SẢN PHẨM (product_id): hàng nghìn item thay vì ~70 danh mục,
# dùng để kiểm chứng ưu thế lý thuyết của FP-Growth khi không gian item lớn.
# minsup đặt theo SỐ ĐƠN tuyệt đối vì support tương đối ở mức sản phẩm rất nhỏ.
PRODUCT_MINCOUNT_GRID = [30, 20, 15, 10, 7, 5, 4, 3, 2]
PRODUCT_REPEATS = 1      # mỗi lần chạy đã đủ dài nên nhiễu thời gian tương đối nhỏ
# Apriori (mlxtend, bản dense) đếm support bằng mảng bool kích thước
# (số giỏ x số ứng viên x độ dài itemset) -> ước lượng bộ nhớ trước khi chạy,
# vượt ngân sách thì bỏ qua và ghi nhận là "không khả thi"
APRIORI_MEM_BUDGET_GB = 1.0

plt.rcParams.update({"figure.dpi": 120, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})
COLORS = {"Apriori": "#2563eb", "FP-Growth": "#ea580c"}


def parse_args():
    parser = argparse.ArgumentParser(description="Olist - Phase 2 mining")
    parser.add_argument("--in-file", default="data/processed/order_items_clean.csv", type=Path)
    parser.add_argument("--out-dir", default="outputs", type=Path)
    parser.add_argument("--model-dir", default="models", type=Path)
    args, _ = parser.parse_known_args()
    return args


# %% 1. Tạo Transaction theo order_id
def build_transactions(df: pd.DataFrame) -> pd.Series:
    """Mỗi order_id -> danh sách danh mục KHÁC NHAU (một đơn mua 3 món cùng danh mục
    chỉ tính là 1 lần xuất hiện của danh mục đó). Bỏ danh mục 'unknown'."""
    df = df[df["category"] != UNKNOWN_CATEGORY]
    tx = df.groupby("order_id")["category"].apply(lambda s: sorted(set(s)))
    print(f"Số transaction: {len(tx):,} | Số danh mục: {df['category'].nunique()}")
    return tx


def encode(transactions: pd.Series) -> pd.DataFrame:
    """One-hot encoding: ma trận boolean (transaction x danh mục)."""
    te = TransactionEncoder()
    arr = te.fit(transactions.tolist()).transform(transactions.tolist())
    return pd.DataFrame(arr, columns=te.columns_, index=transactions.index)


def describe_baskets(tx: pd.Series, onehot: pd.DataFrame, fig_dir: Path) -> pd.DataFrame:
    sizes = tx.str.len()
    dist = sizes.value_counts().sort_index().rename("n_orders").to_frame()
    dist["pct"] = (dist["n_orders"] / len(sizes) * 100).round(3)
    print("\nPhân bố số danh mục/giỏ:\n", dist.to_string())
    density = onehot.values.mean()
    print(f"Mật độ ma trận one-hot: {density:.4%} (độ thưa {1 - density:.4%})")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    axes[0].bar(dist.index.astype(str), dist["n_orders"], color="#2563eb")
    axes[0].set_yscale("log")
    axes[0].set(title="Số danh mục khác nhau trong một đơn hàng",
                xlabel="Số danh mục", ylabel="Số đơn (thang log)")
    top = onehot.sum().sort_values(ascending=False).head(15)[::-1]
    axes[1].barh(top.index, top.values, color="#2563eb")
    axes[1].set(title="Top 15 danh mục theo số đơn", xlabel="Số đơn")
    fig.tight_layout()
    fig.savefig(fig_dir / "01_basket_distribution.png")
    plt.close(fig)
    return dist


# %% 2. Sinh luật (tương thích nhiều phiên bản mlxtend)
def make_rules(freq: pd.DataFrame, n_tx: int, min_conf: float) -> pd.DataFrame:
    if freq.empty or freq["itemsets"].str.len().max() < 2:
        return pd.DataFrame()
    kwargs = dict(metric="confidence", min_threshold=min_conf)
    # mlxtend >= 0.23.2 bắt buộc tham số num_itemsets
    if "num_itemsets" in inspect.signature(association_rules).parameters:
        kwargs["num_itemsets"] = n_tx
    return association_rules(freq, **kwargs)


# %% 3. Benchmark Apriori vs FP-Growth theo minsup
def time_algo(func, onehot, minsup, repeats=N_REPEATS):
    times, result = [], None
    for _ in range(repeats):
        t0 = time.perf_counter()
        result = func(onehot, min_support=minsup, use_colnames=True, max_len=MAX_LEN)
        times.append(time.perf_counter() - t0)
    return float(np.median(times)), result


def apriori_mem_gb(onehot: pd.DataFrame, minsup: float) -> float:
    """Ước lượng bộ nhớ Apriori (mlxtend, dense) ở bước sinh cặp k = 2, bước tốn kém nhất:
    mảng bool (số giỏ x số cặp ứng viên x 2) cộng kết quả trung gian ~ 3 byte/ô."""
    n_freq = int((onehot.mean() >= minsup).sum())
    return len(onehot) * (n_freq * (n_freq - 1) // 2) * 3 / 1024 ** 3


def benchmark(onehot: pd.DataFrame, scenario: str) -> pd.DataFrame:
    rows = []
    n_tx = len(onehot)
    for minsup in MINSUP_GRID[scenario]:
        t_fp, f_fp = time_algo(fpgrowth, onehot, minsup)
        est_gb = apriori_mem_gb(onehot, minsup)
        if est_gb <= APRIORI_MEM_BUDGET_GB:
            t_ap, f_ap = time_algo(apriori, onehot, minsup)
            # Kiểm chứng: hai thuật toán phải ra CÙNG tập phổ biến
            same = set(f_ap["itemsets"]) == set(f_fp["itemsets"])
        else:
            t_ap, same = np.nan, np.nan
            print(f"[{scenario}] minsup={minsup}: bỏ qua Apriori (ước tính {est_gb:.1f} GB RAM)")
        gc.collect()
        rules = make_rules(f_fp, n_tx, MIN_CONF_BENCH)
        n_rules_lift = int((rules["lift"] >= MIN_LIFT).sum()) if len(rules) else 0

        rows.append({
            "scenario": scenario, "n_transactions": n_tx, "minsup": minsup,
            "minsup_count": int(np.ceil(minsup * n_tx)),
            "apriori_est_mem_gb": round(est_gb, 3),
            "apriori_sec": round(t_ap, 4), "fpgrowth_sec": round(t_fp, 4),
            "speedup_fp_vs_ap": round(t_ap / t_fp, 2) if t_fp > 0 else np.nan,
            "n_itemsets": len(f_fp),
            "n_itemsets_len2plus": int((f_fp["itemsets"].str.len() >= 2).sum()),
            "n_rules": len(rules), f"n_rules_lift>={MIN_LIFT}": n_rules_lift,
            "same_itemsets": same,
        })
        print(f"[{scenario}] minsup={minsup:<7} Apriori={t_ap:.3f}s FP={t_fp:.3f}s "
              f"itemsets={len(f_fp):>4} rules={len(rules):>4} same={same}")
    return pd.DataFrame(rows)


def plot_benchmark(bench: pd.DataFrame, fig_dir: Path) -> None:
    rule_col = f"n_rules_lift>={MIN_LIFT}"
    for scenario, g in bench.groupby("scenario"):
        title_sc = "Toàn bộ giỏ hàng" if scenario == "all" else "Giỏ có ≥ 2 danh mục"
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

        ax = axes[0]
        ax.plot(g["minsup"], g["apriori_sec"], "o-", label="Apriori", color=COLORS["Apriori"])
        ax.plot(g["minsup"], g["fpgrowth_sec"], "s-", label="FP-Growth", color=COLORS["FP-Growth"])
        ax.set_xscale("log")
        ax.invert_xaxis()  # minsup giảm dần từ trái sang phải
        ax.set(title=f"Thời gian chạy theo minsup – {title_sc}",
               xlabel="minsup (thang log, giảm dần →)", ylabel="Thời gian (giây, trung vị)")
        ax.legend()

        ax = axes[1]
        x = np.arange(len(g))
        ax.bar(x - 0.2, g["n_itemsets"], 0.4, label="Số tập phổ biến", color="#64748b")
        ax.bar(x + 0.2, g[rule_col], 0.4, label=f"Số luật (lift ≥ {MIN_LIFT})", color="#16a34a")
        ax.set_xticks(x, [f"{m:g}" for m in g["minsup"]], rotation=45)
        ax.set(title=f"Số tập phổ biến & số luật – {title_sc}", xlabel="minsup", ylabel="Số lượng")
        ax.legend()

        fig.tight_layout()
        fig.savefig(fig_dir / f"02_benchmark_{scenario}.png")
        plt.close(fig)


# %% 3b. Thí nghiệm mở rộng: Apriori vs FP-Growth ở mức product_id
def product_level_benchmark(df: pd.DataFrame, fig_dir: Path, tab_dir: Path) -> pd.DataFrame:
    """Transaction = các product_id KHÁC NHAU trong một đơn, chỉ xét đơn có >= 2 sản phẩm
    khác nhau (đơn 1 sản phẩm không thể sinh quan hệ mua kèm sản phẩm)."""
    tx = df.groupby("order_id")["product_id"].apply(lambda s: sorted(set(s)))
    tx = tx[tx.str.len() >= 2]
    n_tx = len(tx)
    if n_tx == 0:
        print("Không có đơn nào chứa >= 2 sản phẩm khác nhau - bỏ qua thí nghiệm.")
        return pd.DataFrame()

    # Lọc trước các sản phẩm có số đơn < ngưỡng nhỏ nhất của lưới. Theo tính chất
    # Apriori (anti-monotone), các sản phẩm này không thể nằm trong tập phổ biến nào,
    # nên việc lọc KHÔNG làm thay đổi kết quả mà chỉ thu nhỏ ma trận one-hot.
    item_count = tx.explode().value_counts()
    keep = set(item_count[item_count >= min(PRODUCT_MINCOUNT_GRID)].index)
    onehot = encode(tx.apply(lambda items: [i for i in items if i in keep]))
    print(f"Giỏ đa sản phẩm: {n_tx:,} | Sản phẩm khác nhau: {len(item_count):,} | "
          f"Giữ lại sau lọc (>= {min(PRODUCT_MINCOUNT_GRID)} đơn): {onehot.shape[1]:,}")

    col_count = onehot.sum()
    rows = []
    for min_count in PRODUCT_MINCOUNT_GRID:
        minsup = min_count / n_tx
        n_freq_items = int((col_count >= min_count).sum())

        t_fp, f_fp = time_algo(fpgrowth, onehot, minsup, PRODUCT_REPEATS)

        # Ước lượng bộ nhớ Apriori ở bước sinh cặp (k = 2), bước tốn kém nhất
        n_cand_pairs = n_freq_items * (n_freq_items - 1) // 2
        est_gb = n_tx * n_cand_pairs * 3 / 1024 ** 3
        if est_gb <= APRIORI_MEM_BUDGET_GB:
            t_ap, f_ap = time_algo(apriori, onehot, minsup, PRODUCT_REPEATS)
            same = set(f_ap["itemsets"]) == set(f_fp["itemsets"])
            status = "ok"
        else:
            t_ap, same = np.nan, np.nan
            status = f"bỏ qua: cần ~{est_gb:.1f} GB RAM"

        rows.append({
            "n_transactions": n_tx, "min_count": min_count, "minsup": round(minsup, 6),
            "n_frequent_items": n_freq_items, "n_candidate_pairs": n_cand_pairs,
            "apriori_est_mem_gb": round(est_gb, 3),
            "apriori_sec": round(t_ap, 4) if not np.isnan(t_ap) else np.nan,
            "fpgrowth_sec": round(t_fp, 4),
            "speedup_fp_vs_ap": round(t_ap / t_fp, 2) if not np.isnan(t_ap) and t_fp > 0 else np.nan,
            "n_itemsets": len(f_fp),
            "n_itemsets_len2plus": int((f_fp["itemsets"].str.len() >= 2).sum()),
            "same_itemsets": same, "apriori_status": status,
        })
        ap_txt = f"{t_ap:.3f}s" if not np.isnan(t_ap) else status
        print(f"[product] min_count={min_count:<3} items={n_freq_items:>5} "
              f"cand_pairs={n_cand_pairs:>9,} Apriori={ap_txt} FP={t_fp:.3f}s "
              f"itemsets={len(f_fp):>5}")

    bench = pd.DataFrame(rows)
    bench.to_csv(tab_dir / "benchmark_product_level.csv", index=False)
    plot_product_benchmark(bench, fig_dir)
    return bench


def plot_product_benchmark(bench: pd.DataFrame, fig_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    x = bench["min_count"].astype(str)

    ax = axes[0]
    ok = bench["apriori_sec"].notna()
    ax.plot(x[ok], bench.loc[ok, "apriori_sec"], "o-", label="Apriori", color=COLORS["Apriori"])
    ax.plot(x, bench["fpgrowth_sec"], "s-", label="FP-Growth", color=COLORS["FP-Growth"])
    if (~ok).any():
        # Đánh dấu các mức minsup Apriori không khả thi về bộ nhớ
        y_mark = np.nanmax(bench[["apriori_sec", "fpgrowth_sec"]].values) * 1.6
        ax.scatter(x[~ok], [y_mark] * (~ok).sum(), marker="x", s=80, color=COLORS["Apriori"],
                   label=f"Apriori vượt {APRIORI_MEM_BUDGET_GB:g} GB RAM")
    ax.set_yscale("log")
    ax.set(title="Mức sản phẩm: thời gian chạy theo ngưỡng số đơn",
           xlabel="min_count (số đơn tối thiểu, giảm dần →)", ylabel="Thời gian (giây, thang log)")
    ax.legend()

    ax = axes[1]
    ax.bar(x, bench["n_candidate_pairs"], color="#64748b", label="Số cặp ứng viên của Apriori")
    ax.set_yscale("log")
    ax.set(title="Bùng nổ ứng viên khi minsup giảm", xlabel="min_count", ylabel="Số lượng (thang log)")
    ax2 = ax.twinx()
    ax2.plot(x, bench["n_frequent_items"], "o-", color="#16a34a", label="Số sản phẩm phổ biến")
    ax2.set_ylabel("Số sản phẩm phổ biến")
    ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(fig_dir / "06_benchmark_product_level.png")
    plt.close(fig)


# %% 4. Luật cuối cùng: lọc, khử trùng, xếp hạng
def to_text(itemset) -> str:
    return ", ".join(sorted(itemset))


def environment() -> dict:
    """Cấu hình máy chạy thực nghiệm (cho Bảng 7.1 của báo cáo)."""
    import platform
    import subprocess

    import mlxtend
    cpu = platform.processor()
    ram_gb = None
    if platform.system() == "Windows":
        try:
            cpu = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Processor | Select-Object -First 1).Name"],
                capture_output=True, text=True, timeout=30).stdout.strip() or cpu
        except (OSError, subprocess.SubprocessError):
            pass
        import ctypes

        class MemStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        st = MemStatus()
        st.dwLength = ctypes.sizeof(MemStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
            ram_gb = round(st.ullTotalPhys / 1024 ** 3, 1)
    elif hasattr(os, "sysconf"):
        ram_gb = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3, 1)
    release = platform.release()
    # platform báo Windows 11 là "10"; build >= 22000 mới là Windows 11
    if platform.system() == "Windows" and release == "10" \
            and int(platform.version().split(".")[-1]) >= 22000:
        release = "11"
    return {"cpu": cpu, "cores": os.cpu_count(), "ram_gb": ram_gb,
            "os": f"{platform.system()} {release} ({platform.version()})",
            "python": platform.python_version(), "pandas": pd.__version__,
            "numpy": np.__version__, "mlxtend": mlxtend.__version__}


def pair_lift_comparison(onehot_all: pd.DataFrame, onehot_multi: pd.DataFrame) -> pd.DataFrame:
    """Lift của từng cặp danh mục tính trên toàn bộ giỏ (ALL) và trên giỏ đa danh mục (MULTI),
    cho các cặp xuất hiện cùng nhau trong >= MIN_PAIR_COUNT đơn."""
    m = onehot_multi.astype(np.int32)
    co = m.T @ m                                   # số đơn chứa đồng thời 2 danh mục
    n_all, n_multi = len(onehot_all), len(onehot_multi)
    cnt_all, cnt_multi = onehot_all.sum(), onehot_multi.sum()
    rows = []
    cats = list(co.columns)
    for i, a in enumerate(cats):
        for b in cats[i + 1:]:
            n = int(co.at[a, b])
            if n >= MIN_PAIR_COUNT:
                rows.append({"cat_a": a, "cat_b": b, "pair_count": n,
                             "lift_all": n * n_all / (cnt_all[a] * cnt_all[b]),
                             "lift_multi": n * n_multi / (cnt_multi[a] * cnt_multi[b])})
    return pd.DataFrame(rows).sort_values("pair_count", ascending=False).reset_index(drop=True)


def final_rules(onehot: pd.DataFrame):
    n_tx = len(onehot)
    freq = fpgrowth(onehot, min_support=FINAL_MINSUP, use_colnames=True, max_len=MAX_LEN)
    rules = make_rules(freq, n_tx, FINAL_MIN_CONF)
    if rules.empty:
        print("Không sinh được luật nào - hãy giảm FINAL_MINSUP/FINAL_MIN_CONF.")
        return freq, rules, rules

    rules = rules.copy()
    rules["pair_count"] = (rules["support"] * n_tx).round().astype(int)
    rules["antecedents_str"] = rules["antecedents"].apply(to_text)
    rules["consequents_str"] = rules["consequents"].apply(to_text)
    rules["rule"] = rules["antecedents_str"] + "  →  " + rules["consequents_str"]
    keep_cols = ["rule", "antecedents_str", "consequents_str", "antecedent support",
                 "consequent support", "support", "pair_count", "confidence", "lift",
                 "leverage", "conviction"]
    rules = rules[keep_cols].sort_values("lift", ascending=False).reset_index(drop=True)

    # Lọc luật có giá trị: lift rõ rệt > 1 và đủ số đơn hỗ trợ
    valuable = rules[(rules["lift"] >= MIN_LIFT) & (rules["pair_count"] >= MIN_PAIR_COUNT)].copy()

    # Khử trùng chiều: A→B và B→A có cùng support & lift -> giữ chiều confidence cao hơn
    # (list comprehension thay cho apply: apply trên DataFrame rỗng trả về DataFrame -> lỗi)
    valuable["itemset_key"] = [
        to_text(set(a.split(", ")) | set(c.split(", ")))
        for a, c in zip(valuable["antecedents_str"], valuable["consequents_str"])]
    top = (valuable.sort_values("confidence", ascending=False)
           .drop_duplicates("itemset_key")
           .sort_values(["lift", "confidence"], ascending=False)
           .head(TOP_K).drop(columns="itemset_key").reset_index(drop=True))
    top.index = top.index + 1

    print(f"\nTổng luật (conf ≥ {FINAL_MIN_CONF}): {len(rules)} | "
          f"Luật có giá trị (lift ≥ {MIN_LIFT}, ≥ {MIN_PAIR_COUNT} đơn): {len(valuable)} | "
          f"Top {len(top)} sau khử trùng chiều")
    return freq, rules, top


def plot_rules(rules: pd.DataFrame, top: pd.DataFrame, fig_dir: Path) -> None:
    if rules.empty:
        return
    # (a) Scatter support - confidence, màu = lift
    fig, ax = plt.subplots(figsize=(8, 5.5))
    sc = ax.scatter(rules["support"], rules["confidence"], c=rules["lift"], cmap="viridis",
                    s=18 + 4 * np.clip(rules["lift"], 0, 20), alpha=0.75, edgecolors="none")
    ax.set_xscale("log")
    ax.set(title="Phân bố luật: Support vs Confidence (màu = Lift)",
           xlabel="Support (thang log)", ylabel="Confidence")
    fig.colorbar(sc, ax=ax, label="Lift")
    fig.tight_layout()
    fig.savefig(fig_dir / "03_rules_scatter.png")
    plt.close(fig)

    # (b) Top luật theo lift
    if not top.empty:
        fig, ax = plt.subplots(figsize=(11, 0.42 * len(top) + 1.5))
        t = top.iloc[::-1]
        ax.barh(t["rule"], t["lift"], color="#16a34a")
        for y, (lift, conf) in enumerate(zip(t["lift"], t["confidence"])):
            ax.text(lift, y, f"  lift={lift:.1f} | conf={conf:.1%}", va="center", fontsize=8)
        ax.set(title=f"Top {len(top)} luật mua kèm theo Lift", xlabel="Lift")
        ax.set_xlim(0, t["lift"].max() * 1.35)
        fig.tight_layout()
        fig.savefig(fig_dir / "04_top_rules_lift.png")
        plt.close(fig)

    # (c) Heatmap lift cho luật 1 → 1 giữa các danh mục xuất hiện trong luật mạnh
    pair = rules[(~rules["antecedents_str"].str.contains(","))
                 & (~rules["consequents_str"].str.contains(","))
                 & (rules["lift"] >= MIN_LIFT) & (rules["pair_count"] >= MIN_PAIR_COUNT)]
    if len(pair):
        cats = pd.concat([pair["antecedents_str"], pair["consequents_str"]]) \
                 .value_counts().head(15).index
        mat = pair.pivot_table(index="antecedents_str", columns="consequents_str",
                               values="lift").reindex(index=cats, columns=cats)
        fig, ax = plt.subplots(figsize=(10, 8.5))
        im = ax.imshow(mat.values, cmap="YlOrRd")
        ax.set_xticks(range(len(cats)), cats, rotation=60, ha="right", fontsize=8)
        ax.set_yticks(range(len(cats)), cats, fontsize=8)
        ax.grid(False)
        for i in range(len(cats)):
            for j in range(len(cats)):
                v = mat.values[i, j]
                if not np.isnan(v):
                    ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7)
        ax.set(title="Heatmap Lift giữa các danh mục (hàng → cột)",
               xlabel="Hệ quả (consequent)", ylabel="Tiền đề (antecedent)")
        fig.colorbar(im, ax=ax, label="Lift")
        fig.tight_layout()
        fig.savefig(fig_dir / "05_lift_heatmap.png")
        plt.close(fig)


# %% 5. Main
def main():
    args = parse_args()
    tab_dir, fig_dir = args.out_dir / "tables", args.out_dir / "figures"
    for d in (tab_dir, fig_dir, args.model_dir):
        d.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.in_file, usecols=["order_id", "product_id", "category"])

    print("=== 1. TRANSACTION & ONE-HOT ===")
    tx_all = build_transactions(df)
    onehot_all = encode(tx_all)
    tx_multi = tx_all[tx_all.str.len() >= 2]
    onehot_multi = encode(tx_multi)
    print(f"Giỏ có >= 2 danh mục: {len(tx_multi):,} ({len(tx_multi) / len(tx_all):.2%})")
    print("Ví dụ 5 transaction đa danh mục:\n", tx_multi.head().to_string())
    dist = describe_baskets(tx_all, onehot_all, fig_dir)
    dist.to_csv(tab_dir / "basket_size_distribution.csv")
    # Số liệu tóm tắt cho báo cáo (report/build_report.py đọc file này)
    (tab_dir / "phase2_summary.json").write_text(json.dumps({
        "n_transactions": len(onehot_all), "n_categories": onehot_all.shape[1],
        "density": float(onehot_all.values.mean()), "n_multi": len(tx_multi),
        "environment": environment(),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== 2. BENCHMARK APRIORI vs FP-GROWTH ===")
    bench = pd.concat([benchmark(onehot_all, "all"), benchmark(onehot_multi, "multi")],
                      ignore_index=True)
    bench.to_csv(tab_dir / "benchmark_apriori_vs_fpgrowth.csv", index=False)
    plot_benchmark(bench, fig_dir)
    print("\n", bench.to_string(index=False))

    print("\n=== 2b. THÍ NGHIỆM MỞ RỘNG MỨC SẢN PHẨM (product_id) ===")
    product_level_benchmark(df, fig_dir, tab_dir)

    print("\n=== 2c. LIFT CỦA CÁC CẶP DANH MỤC: ALL vs MULTI ===")
    pairs = pair_lift_comparison(onehot_all, onehot_multi)
    pairs.to_csv(tab_dir / "pair_lift_all_vs_multi.csv", index=False)
    print(pairs.head(15).to_string(index=False))

    print(f"\n=== 3. LUẬT KẾT HỢP CUỐI CÙNG (kịch bản {FINAL_SCENARIO.upper()}) ===")
    freq, rules, top = final_rules(onehot_multi if FINAL_SCENARIO == "multi" else onehot_all)
    freq.assign(itemsets=freq["itemsets"].apply(to_text),
                length=freq["itemsets"].str.len()) \
        .sort_values("support", ascending=False) \
        .to_csv(tab_dir / "frequent_itemsets.csv", index=False)
    rules.to_csv(tab_dir / "all_rules.csv", index=False)
    top.to_csv(tab_dir / f"top{TOP_K}_rules.csv", index_label="rank")
    plot_rules(rules, top, fig_dir)

    # Luật cho app: giữ CẢ HAI chiều để tra cứu theo bất kỳ danh mục nào được chọn
    if not rules.empty:
        rules[rules["lift"] > 1].to_csv(args.model_dir / "rules.csv", index=False)

    with pd.option_context("display.float_format", "{:.4f}".format, "display.width", 200):
        print(f"\nTOP {TOP_K} LUẬT:")
        print(top[["rule", "support", "pair_count", "confidence", "lift"]].to_string())
    print(f"\nĐã lưu bảng vào {tab_dir}, biểu đồ vào {fig_dir}, luật cho app vào {args.model_dir}")


if __name__ == "__main__":
    main()
