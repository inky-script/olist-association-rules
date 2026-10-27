# -*- coding: utf-8 -*-
"""PHASE 5 – Nội dung mục 6–11 của báo cáo.

Kết quả thực nghiệm (mục 7, 8) được ĐỌC TỰ ĐỘNG từ outputs/tables/*.csv do phase2_mining.py
sinh ra: chạy lại build_report.py sau khi chạy Phase 2 là bảng, hình và câu nhận xét có số
liệu thật. Nếu chưa có output, báo cáo chèn chỗ trống tô vàng để nhóm điền.
Tham số thuật toán đọc trực tiếp từ src/phase2_mining.py nên luôn khớp với mã nguồn.
"""
import ast
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from docx.shared import Cm
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from report_lib import (bullet, bullets, code_block, figure, formula, h1, h2, h3,
                        page_break, para, table)

PH = "[[...]]"  # ô chờ điền khi chưa có output


# ----------------------------------------------------------------------------
# Tiện ích số liệu
# ----------------------------------------------------------------------------
def vn(x, d=2):
    """Định dạng số kiểu Việt Nam: 1.234,56"""
    s = f"{x:,.{d}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def pct(x, d=1):
    return vn(x * 100, d) + "%"


def num(n):
    """Số nguyên kiểu Việt Nam: 12.345"""
    return f"{int(n):,}".replace(",", ".")


def sec(x):
    return "–" if pd.isna(x) else vn(x, 3)


def read_config(src_file: Path) -> dict:
    """Đọc các hằng số cấu hình (giá trị literal) ở cấp module của phase2_mining.py."""
    tree = ast.parse(src_file.read_text(encoding="utf-8"))
    cfg = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            try:
                cfg[node.targets[0].id] = ast.literal_eval(node.value)
            except ValueError:
                pass
    return cfg


def category_winner(res):
    """Thuật toán nhanh hơn ở đa số mức minsup của kịch bản ALL (None nếu chưa có dữ liệu)."""
    b = res.get("bench")
    if b is None or b.empty:
        return None
    b = b[b["scenario"] == "all"].dropna(subset=["apriori_sec"])
    if b.empty:
        return None
    return "Apriori" if (b["apriori_sec"] < b["fpgrowth_sec"]).mean() >= 0.5 else "FP-Growth"


def product_findings(res):
    """(min_count bắt đầu FP-Growth nhanh hơn, có mức Apriori bị bỏ qua hay không)."""
    p = res.get("product")
    if p is None or p.empty:
        return None, None
    both = p.dropna(subset=["apriori_sec"])
    cross = both[both["fpgrowth_sec"] < both["apriori_sec"]]
    return (int(cross["min_count"].iloc[0]) if len(cross) else None,
            bool((p["apriori_status"] != "ok").any()))


def load_results(table_dir: Path) -> dict:
    res = {}
    for key, name in (("pairs", "pair_lift_all_vs_multi.csv"),
                      ("bench", "benchmark_apriori_vs_fpgrowth.csv"),
                      ("product", "benchmark_product_level.csv"),
                      ("top", "top20_rules.csv"),
                      ("rules", "all_rules.csv"),
                      ("baskets", "basket_size_distribution.csv")):
        f = table_dir / name
        res[key] = pd.read_csv(f) if f.exists() else None
    for key, name in (("p1", "phase1_summary.json"), ("p2", "phase2_summary.json")):
        f = table_dir / name
        res[key] = json.loads(f.read_text()) if f.exists() else {}
    return res


# ----------------------------------------------------------------------------
# Hình tự vẽ: ví dụ FP-tree, luồng xử lý app
# ----------------------------------------------------------------------------
def _node(ax, x, y, text, color="#1F3864"):
    ax.add_patch(FancyBboxPatch((x - 0.55, y - 0.25), 1.1, 0.5,
                                boxstyle="round,pad=0.02,rounding_size=0.15", fc=color, ec=color))
    ax.text(x, y, text, ha="center", va="center", color="white", fontsize=11, fontweight="bold")


def _line(ax, p1, p2, style="-", color="#334155", arrow=False):
    if arrow:
        ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=13, lw=1.3,
                                     color=color, linestyle=style))
    else:
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], style, color=color, lw=1.4)


def draw_fptree(path):
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    _node(ax, 4.6, 4.1, "root", "#64748b")
    _node(ax, 3.4, 3.0, "B : 4")
    _node(ax, 6.4, 3.0, "F : 1")
    _node(ax, 2.6, 1.9, "F : 3")
    _node(ax, 4.2, 1.9, "H : 1", "#C55A11")
    _node(ax, 6.4, 1.9, "H : 1", "#C55A11")
    _node(ax, 2.6, 0.8, "H : 1", "#C55A11")
    for p, c in (((4.6, 3.85), (3.4, 3.25)), ((4.6, 3.85), (6.4, 3.25)),
                 ((3.4, 2.75), (2.6, 2.15)), ((3.4, 2.75), (4.2, 2.15)),
                 ((6.4, 2.75), (6.4, 2.15)), ((2.6, 1.65), (2.6, 1.05))):
        _line(ax, p, c)
    # liên kết nút cùng item (node-link) của H
    _line(ax, (3.15, 0.8), (3.95, 1.68), "--", "#C55A11", arrow=True)
    _line(ax, (4.75, 1.9), (5.85, 1.9), "--", "#C55A11", arrow=True)
    # bảng header
    ax.text(0.15, 4.2, "Header table", fontsize=10.5, fontweight="bold")
    for k, (item, cnt) in enumerate((("B", 4), ("F", 4), ("H", 3))):
        ax.text(0.25, 3.7 - k * 0.45, f"{item}   support = {cnt}", fontsize=10.5,
                family="DejaVu Sans Mono")
    ax.annotate("", xy=(2.05, 0.8), xytext=(1.2, 2.75),
                arrowprops=dict(arrowstyle="-|>", ls="--", color="#C55A11"))
    ax.text(7.2, 0.5, "Nét đứt: liên kết các nút\ncùng item H (node-link)", fontsize=9.5,
            color="#C55A11")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def draw_app_flow(path):
    steps = [("Người dùng", "chọn danh mục\nhoặc giỏ hàng"),
             ("Nạp luật", "rules.csv (cache)\nhoặc khai thác lại"),
             ("So khớp", "tiền đề ⊆ giỏ,\nhệ quả ∉ giỏ"),
             ("Lọc", "conf, lift,\nsố đơn tối thiểu"),
             ("Xếp hạng", "lift / conf /\nsupport, top-N"),
             ("Hiển thị", "thẻ, biểu đồ,\ndiễn giải, bảng")]
    fig, ax = plt.subplots(figsize=(11, 2.6))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 2.6)
    ax.axis("off")
    w, gap = 1.55, 0.3
    for k, (title, sub) in enumerate(steps):
        x = 0.1 + k * (w + gap)
        color = "#C55A11" if k in (0, 5) else "#1F3864"
        ax.add_patch(FancyBboxPatch((x, 0.35), w, 1.9, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    fc=color, ec=color))
        ax.text(x + w / 2, 1.85, title, ha="center", va="center", color="white", fontsize=10.5,
                fontweight="bold")
        ax.text(x + w / 2, 1.05, sub, ha="center", va="center", color="white", fontsize=9)
        if k < len(steps) - 1:
            _line(ax, (x + w, 1.3), (x + w + gap, 1.3), arrow=True)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


# ============================================================================
# 6. PHƯƠNG PHÁP
# ============================================================================
def section6(doc, cfg, fig_dir: Path):
    h1(doc, "6. Phương pháp")

    h2(doc, "6.1. Các khái niệm và độ đo đánh giá luật")
    para(doc, "Cho cơ sở dữ liệu giao dịch *D* gồm *N* giao dịch. Một tập item *X* được gọi là "
              "**tập phổ biến** (frequent itemset) nếu độ hỗ trợ của nó không nhỏ hơn ngưỡng "
              "minsup. Từ mỗi tập phổ biến *Z* có thể sinh các luật *X → Y* với *X ∪ Y = Z*. Đề "
              "tài sử dụng năm độ đo sau để đánh giá luật.")
    h3(doc, "6.1.1. Support (độ hỗ trợ)")
    formula(doc, "support(X → Y) = support(X ∪ Y) = |{t ∈ D : X ∪ Y ⊆ t}| / N")
    para(doc, "Support cho biết tỷ lệ giao dịch chứa đồng thời *X* và *Y*, tức là mức độ phổ "
              "biến của luật. Support cao nghĩa là luật áp dụng được cho nhiều khách hàng; "
              "support quá thấp nghĩa là luật có thể chỉ là ngẫu nhiên. Trong báo cáo, nhóm "
              "dùng thêm **số đơn hỗ trợ** (`pair_count` = support × N) vì con số tuyệt đối dễ "
              "đánh giá độ tin cậy thống kê hơn khi support rất nhỏ.")
    h3(doc, "6.1.2. Confidence (độ tin cậy)")
    formula(doc, "confidence(X → Y) = support(X ∪ Y) / support(X) = P(Y | X)")
    para(doc, "Confidence là xác suất có điều kiện để giao dịch chứa *Y* khi đã chứa *X*. Đây "
              "là độ đo trực quan nhất cho việc gợi ý: “trong số khách mua *X*, bao nhiêu phần "
              "trăm mua thêm *Y*”. Tuy nhiên confidence có một nhược điểm nghiêm trọng: nếu *Y* "
              "là danh mục rất phổ biến, luật *X → Y* sẽ có confidence cao dù *X* và *Y* hoàn "
              "toàn độc lập.")
    h3(doc, "6.1.3. Lift (độ nâng)")
    formula(doc, "lift(X → Y) = confidence(X → Y) / support(Y) = P(X ∪ Y) / (P(X) · P(Y))")
    para(doc, "Lift khắc phục nhược điểm của confidence bằng cách so sánh với mức xác suất nền "
              "của *Y*. Lift = 1 nghĩa là *X* và *Y* độc lập thống kê; lift > 1 nghĩa là sự xuất "
              "hiện của *X* làm **tăng** khả năng xuất hiện của *Y* (quan hệ bổ trợ, phù hợp "
              "cross-selling); lift < 1 nghĩa là hai danh mục có xu hướng **loại trừ** nhau "
              "(có thể là sản phẩm thay thế). Lift có tính đối xứng: lift(X → Y) = lift(Y → X).")
    h3(doc, "6.1.4. Leverage và Conviction")
    formula(doc, "leverage(X → Y) = support(X ∪ Y) − support(X) · support(Y)")
    formula(doc, "conviction(X → Y) = (1 − support(Y)) / (1 − confidence(X → Y))")
    para(doc, "Leverage đo phần chênh lệch tuyệt đối giữa tần suất xuất hiện chung thực tế và "
              "tần suất kỳ vọng nếu độc lập; leverage bằng 0 tương ứng độc lập. Conviction đo "
              "mức độ luật “sai” ít hơn bao nhiêu lần so với trường hợp độc lập; conviction "
              "bằng 1 khi độc lập và tiến tới vô cùng khi luật luôn đúng. Hai độ đo này được "
              "dùng để tham khảo thêm bên cạnh bộ ba Support – Confidence – Lift.")
    table(doc, ["Độ đo", "Miền giá trị", "Độc lập khi", "Đối xứng", "Vai trò trong đề tài"],
          [["Support", "[0, 1]", "–", "Có", "Ngưỡng minsup; đếm số đơn hỗ trợ"],
           ["Confidence", "[0, 1]", "= support(Y)", "Không", "Xác suất mua kèm, chọn chiều luật"],
           ["Lift", "[0, +∞)", "= 1", "Có", "Tiêu chí chính: loại lift ≈ 1, xếp hạng"],
           ["Leverage", "[−0,25; 0,25]", "= 0", "Có", "Tham khảo"],
           ["Conviction", "[0, +∞]", "= 1", "Không", "Tham khảo"]],
          [2.6, 2.7, 2.6, 1.8, 5.8], cap="Bảng 6.1: Tổng hợp các độ đo đánh giá luật",
          align=["l", "c", "c", "c", "l"], font_size=11)

    h2(doc, "6.2. Thuật toán Apriori")
    h3(doc, "6.2.1. Ý tưởng")
    para(doc, "Apriori do Agrawal và Srikant đề xuất năm 1994, dựa trên **tính chất Apriori** "
              "(tính chất đóng xuống – anti-monotone): *mọi tập con của một tập phổ biến đều là "
              "tập phổ biến*; tương đương, *nếu một tập không phổ biến thì mọi tập cha của nó "
              "đều không phổ biến*. Thuật toán tìm kiếm theo chiều rộng: từ các tập phổ biến kích "
              "thước *k − 1* (*Lₖ₋₁*), sinh các tập ứng viên kích thước *k* (*Cₖ*), cắt tỉa những "
              "ứng viên có tập con không phổ biến, rồi quét cơ sở dữ liệu để đếm support và giữ "
              "lại *Lₖ*. Quá trình lặp đến khi không sinh thêm được ứng viên.")
    h3(doc, "6.2.2. Mã giả")
    code_block(doc, '''
Apriori(D, minsup):
    L1 = { i ∈ I : support({i}) ≥ minsup }
    k = 2
    while L(k-1) ≠ ∅:
        Ck = apriori_gen(L(k-1))            # nối L(k-1) với chính nó
        Ck = { c ∈ Ck : mọi tập con (k-1) phần tử của c ∈ L(k-1) }   # cắt tỉa
        for t in D:                          # quét cơ sở dữ liệu
            for c in Ck:
                if c ⊆ t: count[c] += 1
        Lk = { c ∈ Ck : count[c] / N ≥ minsup }
        k = k + 1
    return ∪ Lk''', cap="Đoạn mã 6.1: Mã giả thuật toán Apriori")
    h3(doc, "6.2.3. Ví dụ minh họa")
    para(doc, "Xét cơ sở dữ liệu nhỏ gồm 6 giao dịch với các danh mục B (bed_bath_table), "
              "F (furniture_decor), H (housewares), P (perfumery) như Bảng 6.2, ngưỡng minsup = "
              "2/6 (tức tối thiểu 2 giao dịch).")
    table(doc, ["TID", "Giao dịch", "TID", "Giao dịch"],
          [["T1", "{B, F}", "T4", "{B, H}"], ["T2", "{B, F, H}", "T5", "{F, H}"],
           ["T3", "{P}", "T6", "{B, F}"]],
          [2.0, 5.0, 2.0, 5.0], cap="Bảng 6.2: Cơ sở dữ liệu ví dụ", align=["c", "l", "c", "l"])
    bullets(doc, [
        "**Bước 1 (k = 1):** đếm support: B = 4, F = 4, H = 3, P = 1. Loại P vì 1 < 2, thu được "
        "L₁ = {B, F, H}.",
        "**Bước 2 (k = 2):** sinh C₂ = {BF, BH, FH}; đếm: BF = 3, BH = 2, FH = 2. Cả ba đều phổ "
        "biến, nên L₂ = {BF, BH, FH}.",
        "**Bước 3 (k = 3):** sinh C₃ = {BFH}; mọi tập con 2 phần tử đều thuộc L₂ nên không bị cắt "
        "tỉa; nhưng support(BFH) = 1 < 2, nên L₃ = ∅ và thuật toán dừng.",
        "**Sinh luật:** B → F có support = 3/6 = 0,50, confidence = 3/4 = 0,75, lift = 0,75 / "
        "(4/6) = 1,125. Trong khi đó B → H có confidence = 2/4 = 0,50 và lift = 0,50 / (3/6) = "
        "**1,00**: B và H hoàn toàn độc lập, nên luật này dù có confidence 50% vẫn **không có "
        "giá trị gợi ý**. Ví dụ cho thấy vì sao phải lọc theo lift.",
    ])
    h3(doc, "6.2.4. Độ phức tạp")
    para(doc, "Chi phí của Apriori đến từ hai nguồn: (1) số lần quét cơ sở dữ liệu bằng độ dài "
              "tập phổ biến lớn nhất cộng 1; (2) số lượng ứng viên, đặc biệt ở bước *k* = 2 với "
              "|C₂| = |L₁|·(|L₁| − 1)/2, tăng theo bình phương số item phổ biến. Khi minsup giảm, "
              "|L₁| tăng nhanh và số ứng viên bùng nổ. Đây là điểm yếu cốt lõi mà FP-Growth được "
              "thiết kế để khắc phục.")

    h2(doc, "6.3. Thuật toán FP-Growth")
    h3(doc, "6.3.1. Ý tưởng")
    para(doc, "FP-Growth (Frequent Pattern Growth) do Han, Pei và Yin đề xuất năm 2000, khai "
              "thác tập phổ biến **không cần sinh ứng viên**. Thuật toán nén toàn bộ cơ sở dữ "
              "liệu vào một cấu trúc cây tiền tố gọi là **FP-tree**, sau đó khai thác đệ quy "
              "theo chiến lược chia để trị trên các cây điều kiện nhỏ hơn. Toàn bộ quá trình chỉ "
              "cần **hai lần quét** cơ sở dữ liệu.")
    h3(doc, "6.3.2. Xây dựng FP-tree")
    bullets(doc, [
        "**Lần quét 1:** đếm support của từng item, loại các item không phổ biến, sắp xếp item "
        "phổ biến theo support giảm dần.",
        "**Lần quét 2:** với mỗi giao dịch, giữ các item phổ biến theo thứ tự trên rồi chèn vào "
        "cây: các giao dịch có chung tiền tố sẽ dùng chung đường đi, bộ đếm của nút được tăng "
        "thêm 1. Một bảng header lưu con trỏ tới tất cả các nút của cùng một item (node-link).",
    ])
    para(doc, "Với dữ liệu Bảng 6.2, thứ tự item là B (4), F (4), H (3); P bị loại. Các giao "
              "dịch sau sắp xếp là: {B, F}, {B, F, H}, ∅, {B, H}, {F, H}, {B, F}. FP-tree thu "
              "được như Hình 6.1: sáu giao dịch được nén thành cây chỉ có 6 nút item.")
    fptree = fig_dir / "fptree_example.png"
    draw_fptree(fptree)
    figure(doc, fptree, "Hình 6.1: FP-tree xây dựng từ cơ sở dữ liệu ví dụ", width_cm=13)
    h3(doc, "6.3.3. Khai thác FP-tree")
    para(doc, "Với mỗi item trong bảng header (đi từ item ít phổ biến nhất), thuật toán thu thập "
              "**cơ sở mẫu điều kiện** (conditional pattern base), là tập các đường đi tiền tố "
              "dẫn tới item đó. Từ cơ sở mẫu này dựng **FP-tree điều kiện**, rồi khai thác đệ "
              "quy. Ví dụ với item H: các tiền tố là {B, F}:1, {B}:1, {F}:1, nên trong cây điều "
              "kiện B có support 2 và F có support 2, đều đạt ngưỡng. Từ đó thu được các tập phổ "
              "biến {B, H}:2 và {F, H}:2; còn {B, F, H} chỉ có support 1 nên bị loại. Kết quả "
              "hoàn toàn trùng khớp với Apriori.")
    code_block(doc, '''
FP-Growth(Tree, α):                       # α: hậu tố đang xét, ban đầu = ∅
    if Tree chỉ gồm một đường đi P:
        for mỗi tổ hợp β các nút trên P:
            xuất β ∪ α với support = min support các nút trong β
    else:
        for mỗi item a trong header(Tree), từ ít phổ biến nhất:
            β = {a} ∪ α ; xuất β với support(a)
            B = conditional_pattern_base(a)
            Tree_β = build_FP_tree(B)        # bỏ item không phổ biến
            if Tree_β ≠ ∅: FP-Growth(Tree_β, β)''',
               cap="Đoạn mã 6.2: Mã giả thuật toán FP-Growth")

    h2(doc, "6.4. So sánh lý thuyết Apriori và FP-Growth")
    table(doc, ["Tiêu chí", "Apriori", "FP-Growth"],
          [["Chiến lược", "Sinh – kiểm tra ứng viên, duyệt theo chiều rộng",
            "Chia để trị trên cây điều kiện, không sinh ứng viên"],
           ["Số lần quét dữ liệu", "k_max + 1 lần", "2 lần"],
           ["Cấu trúc dữ liệu", "Danh sách ứng viên, ma trận giao dịch", "FP-tree + bảng header"],
           ["Điểm mạnh", "Đơn giản, dễ cài đặt và vector hóa; nhanh khi ít item, minsup cao",
            "Mở rộng tốt khi nhiều item, minsup thấp, mẫu dài"],
           ["Điểm yếu", "Bùng nổ ứng viên, tốn bộ nhớ khi |L₁| lớn",
            "Chi phí dựng cây; cây có thể lớn nếu dữ liệu ít trùng lặp tiền tố"],
           ["Kết quả", "Tập phổ biến đầy đủ, chính xác", "Giống hệt Apriori"]],
          [3.5, 6.0, 6.0], cap="Bảng 6.3: So sánh lý thuyết hai thuật toán", font_size=11)
    para(doc, "Cần lưu ý rằng hiệu năng thực tế còn phụ thuộc vào **cách cài đặt**. Trong thư "
              "viện `mlxtend`, hàm `apriori` được vector hóa bằng NumPy: việc đếm support của "
              "toàn bộ ứng viên ở mỗi mức được thực hiện bằng phép toán ma trận trên mảng bool, "
              "rất nhanh khi số ứng viên nhỏ, nhưng cần bộ nhớ tỷ lệ với (số giao dịch × số ứng "
              "viên). Hàm `fpgrowth` dựng cây bằng mã Python thuần, có chi phí cố định cao hơn "
              "nhưng không bị bùng nổ ứng viên. Vì vậy, nhóm kỳ vọng hai thuật toán sẽ có thứ "
              "hạng khác nhau tùy kích thước không gian item, và thiết kế thực nghiệm ở cả mức "
              "danh mục lẫn mức sản phẩm để kiểm chứng.")

    h2(doc, "6.5. Biểu diễn dữ liệu đầu vào")
    para(doc, "Cả hai hàm `apriori` và `fpgrowth` của `mlxtend` nhận cùng một đầu vào: DataFrame "
              "one-hot kiểu bool (mục 5.8), mỗi dòng là một đơn hàng, mỗi cột là một danh mục. "
              "Việc dùng chung một ma trận đảm bảo so sánh công bằng giữa hai thuật toán. Kết "
              "quả trả về là DataFrame gồm cột `support` và `itemsets` (kiểu `frozenset`), sau "
              "đó được đưa vào hàm `association_rules` để sinh luật cùng các độ đo ở mục 6.1.")
    code_block(doc, '''
freq_ap = apriori(onehot, min_support=minsup, use_colnames=True, max_len=3)
freq_fp = fpgrowth(onehot, min_support=minsup, use_colnames=True, max_len=3)
assert set(freq_ap["itemsets"]) == set(freq_fp["itemsets"])   # kiểm chứng
rules = association_rules(freq_fp, metric="confidence", min_threshold=min_conf,
                          num_itemsets=len(onehot))''',
               cap="Đoạn mã 6.3: Gọi hai thuật toán trên cùng một ma trận one-hot")

    h2(doc, "6.6. Lựa chọn tham số")
    grid_all = ", ".join(f"{v:g}" for v in cfg.get("MINSUP_GRID", {}).get("all", []))
    grid_multi = ", ".join(f"{v:g}" for v in cfg.get("MINSUP_GRID", {}).get("multi", []))
    grid_prod = ", ".join(str(v) for v in cfg.get("PRODUCT_MINCOUNT_GRID", []))
    table(doc, ["Tham số", "Giá trị", "Lý do lựa chọn"],
          [["max_len", str(cfg.get("MAX_LEN", PH)),
            "Giỏ hàng rất ngắn, tập > 3 danh mục gần như không đạt minsup"],
           ["Dải minsup – ALL", grid_all or PH,
            "Phủ từ mức chỉ có tập đơn đến mức xuất hiện nhiều tập cặp"],
           ["Dải minsup – MULTI", grid_multi or PH, "Support của cặp cao hơn khi chỉ xét giỏ đa danh mục"],
           ["Dải min_count – mức sản phẩm", grid_prod or PH,
            "Ngưỡng theo số đơn tuyệt đối vì support tương đối quá nhỏ"],
           ["Số lần chạy lặp", str(cfg.get("N_REPEATS", PH)), "Lấy trung vị thời gian để giảm nhiễu"],
           ["Kịch bản sinh luật cuối", str(cfg.get("FINAL_SCENARIO", PH)).upper(),
            "Trên ALL lift của gần như mọi cặp < 1 (mục 7.6)"],
           ["minsup luật cuối", f"{cfg.get('FINAL_MINSUP', PH):g}" if "FINAL_MINSUP" in cfg else PH,
            "Khoảng 4 đơn trong nhóm giỏ đa danh mục, giữ cả các cặp hiếm"],
           ["minconf luật cuối", f"{cfg.get('FINAL_MIN_CONF', PH):g}" if "FINAL_MIN_CONF" in cfg else PH,
            "Đặt thấp; độ mạnh của luật được kiểm soát bằng lift và số đơn"],
           ["Ngưỡng lift", f"≥ {cfg.get('MIN_LIFT', PH)}", "Loại các luật có lift xấp xỉ 1 (gần độc lập)"],
           ["Số đơn hỗ trợ tối thiểu", f"≥ {cfg.get('MIN_PAIR_COUNT', PH)}",
            "Tránh luật chỉ dựa trên vài đơn hàng ngẫu nhiên"],
           ["Số luật tiêu biểu", str(cfg.get("TOP_K", PH)), "Đúng yêu cầu 10–20 luật của đề tài"],
           ["Ngân sách bộ nhớ Apriori", f"{cfg.get('APRIORI_MEM_BUDGET_GB', PH)} GB",
            "Bỏ qua lần chạy Apriori ước tính vượt ngưỡng, tránh treo máy"]],
          [4.2, 4.8, 6.5], cap="Bảng 6.4: Các tham số thực nghiệm (đọc trực tiếp từ mã nguồn)",
          font_size=11)
    para(doc, "Ngưỡng confidence tối thiểu được đặt thấp có chủ đích. Ngay cả trong nhóm giỏ đa "
              "danh mục, mỗi danh mục có thể đi kèm với rất nhiều danh mục khác nhau, nên "
              "confidence của từng luật hiếm khi cao như các ví dụ siêu thị kinh điển (minconf "
              "0,3 trở lên). Độ mạnh của luật vì vậy được đánh giá chủ yếu qua lift và số đơn hỗ "
              "trợ.")


# ============================================================================
# 7. KẾT QUẢ VÀ ĐÁNH GIÁ
# ============================================================================
def _bench_table(doc, b, cap):
    rule_col = [c for c in b.columns if c.startswith("n_rules_lift")][0]
    rows = []
    for _, r in b.iterrows():
        rows.append([f"{r['minsup']:g}", f"{int(r['minsup_count']):,}".replace(",", "."),
                     sec(r["apriori_sec"]), sec(r["fpgrowth_sec"]),
                     vn(r["speedup_fp_vs_ap"], 2) if pd.notna(r["speedup_fp_vs_ap"]) else "–",
                     str(int(r["n_itemsets"])), str(int(r["n_itemsets_len2plus"])),
                     str(int(r["n_rules"])), str(int(r[rule_col])),
                     "–" if pd.isna(r["same_itemsets"]) else
                     ("✔" if str(r["same_itemsets"]) == "True" else "✘")])
    table(doc, ["minsup", "Số đơn tối thiểu", "Apriori (s)", "FP-Growth (s)", "Tỷ lệ AP/FP",
                "Số tập phổ biến", "Tập ≥ 2 phần tử", "Số luật", "Luật lift ≥ ngưỡng", "Trùng khớp"],
          rows, [1.5, 1.6, 1.6, 1.7, 1.5, 1.6, 1.6, 1.4, 1.7, 1.3], cap=cap,
          align=["c", "r", "r", "r", "r", "r", "r", "r", "r", "c"], font_size=9.5)


def _bench_placeholder(doc, cap, n_rows=8):
    table(doc, ["minsup", "Apriori (s)", "FP-Growth (s)", "Số tập phổ biến", "Số luật",
                "Luật lift ≥ ngưỡng", "Trùng khớp"],
          [[PH] * 7 for _ in range(n_rows)], [2.0, 2.2, 2.3, 2.3, 2.0, 2.5, 2.2], cap=cap,
          align=["c"] * 7, font_size=10.5)


def _describe_bench(b):
    """Sinh câu nhận xét định lượng từ bảng benchmark."""
    first, last = b.iloc[0], b.iloc[-1]
    faster_ap = (b["apriori_sec"] < b["fpgrowth_sec"]).sum()
    txt = (f"Khi minsup giảm từ {first['minsup']:g} xuống {last['minsup']:g}, số tập phổ biến "
           f"tăng từ {int(first['n_itemsets'])} lên {int(last['n_itemsets'])}, số luật tăng từ "
           f"{int(first['n_rules'])} lên {int(last['n_rules'])}. Thời gian chạy của Apriori tăng "
           f"từ {sec(first['apriori_sec'])} s lên {sec(last['apriori_sec'])} s, của FP-Growth tăng "
           f"từ {sec(first['fpgrowth_sec'])} s lên {sec(last['fpgrowth_sec'])} s. Apriori nhanh "
           f"hơn ở {faster_ap}/{len(b)} mức minsup khảo sát.")
    return txt


def section7(doc, res, cfg, out_fig: Path):
    h1(doc, "7. Kết quả và đánh giá")

    h2(doc, "7.1. Môi trường thực nghiệm")
    env = res["p2"].get("environment", {})
    libs = (f"pandas {env['pandas']}, NumPy {env['numpy']}, mlxtend {env['mlxtend']} "
            if env else "pandas, NumPy, mlxtend ")
    table(doc, ["Thành phần", "Cấu hình"],
          [["CPU", f"{env['cpu']} ({env['cores']} luồng)" if env else "[[tên CPU, số nhân]]"],
           ["RAM", f"{vn(env['ram_gb'], 1)} GB" if env.get("ram_gb") else "[[dung lượng RAM]]"],
           ["Hệ điều hành", env.get("os", "[[Windows 10/11, macOS…]]")],
           ["Ngôn ngữ", f"Python {env.get('python', '[[phiên bản]]')}"],
           ["Thư viện", libs + "(apriori, fpgrowth, association_rules), matplotlib, "
                               "Streamlit, Plotly"],
           ["Đo thời gian", "`time.perf_counter()`, trung vị của nhiều lần chạy, chỉ đo bước "
                            "khai thác tập phổ biến (không tính đọc dữ liệu, mã hóa)"]],
          [3.5, 12.0], cap="Bảng 7.1: Môi trường thực nghiệm")

    b_all = b_multi = None
    if res["bench"] is not None:
        b_all = res["bench"][res["bench"]["scenario"] == "all"]
        b_multi = res["bench"][res["bench"]["scenario"] == "multi"]

    h2(doc, "7.2. Kịch bản ALL – toàn bộ giỏ hàng")
    para(doc, "Bảng 7.2 và Hình 7.1 trình bày kết quả khảo sát trên toàn bộ giao dịch hợp lệ"
              + (f" ({int(b_all['n_transactions'].iloc[0]):,} giao dịch)".replace(",", ".")
                 if b_all is not None and len(b_all) else " ([[số giao dịch]] giao dịch)") + ".")
    if b_all is not None and len(b_all):
        _bench_table(doc, b_all, "Bảng 7.2: Kết quả Apriori và FP-Growth – kịch bản ALL")
    else:
        _bench_placeholder(doc, "Bảng 7.2: Kết quả Apriori và FP-Growth – kịch bản ALL "
                                "(nguồn: outputs/tables/benchmark_apriori_vs_fpgrowth.csv)")
    figure(doc, out_fig / "02_benchmark_all.png",
           "Hình 7.1: Thời gian chạy, số tập phổ biến và số luật theo minsup – kịch bản ALL",
           width_cm=16, hint="outputs/figures/02_benchmark_all.png")
    para(doc, _describe_bench(b_all) if b_all is not None and len(b_all) else
         "[[Nhận xét: xu hướng thời gian chạy của hai thuật toán khi minsup giảm; mức minsup "
         "mà các tập 2 phần tử bắt đầu xuất hiện; tốc độ tăng của số luật.]]")
    para(doc, "Có thể quan sát hai đặc điểm. Thứ nhất, ở các mức minsup cao, chỉ có các tập "
              "một phần tử đạt ngưỡng, nên số luật bằng 0: đây là hệ quả trực tiếp của độ thưa "
              "giỏ hàng đã phân tích ở mục 5.9. Thứ hai, ngay cả khi minsup giảm tới 10⁻⁴, số luật "
              "trong kịch bản ALL vẫn rất ít và hầu như không có luật nào có lift vượt ngưỡng. "
              "Nguyên nhân được phân tích ở mục 7.6, và đây cũng là lý do luật cuối cùng được sinh "
              "từ kịch bản MULTI.")

    h2(doc, "7.3. Kịch bản MULTI – giỏ hàng có từ hai danh mục")
    if b_multi is not None and len(b_multi):
        _bench_table(doc, b_multi, "Bảng 7.3: Kết quả Apriori và FP-Growth – kịch bản MULTI")
    else:
        _bench_placeholder(doc, "Bảng 7.3: Kết quả Apriori và FP-Growth – kịch bản MULTI")
    figure(doc, out_fig / "02_benchmark_multi.png",
           "Hình 7.2: Thời gian chạy, số tập phổ biến và số luật theo minsup – kịch bản MULTI",
           width_cm=16, hint="outputs/figures/02_benchmark_multi.png")
    para(doc, _describe_bench(b_multi) if b_multi is not None and len(b_multi) else
         "[[Nhận xét kịch bản MULTI, so sánh với ALL.]]")
    para(doc, "So với kịch bản ALL, kịch bản MULTI có số giao dịch nhỏ hơn rất nhiều nên cả hai "
              "thuật toán đều chạy trong vài mili giây, và chênh lệch thời gian giữa chúng không "
              "còn ý nghĩa thực tế. Ngược lại, support của các cặp danh mục cao hơn hẳn, nên các "
              "tập hai phần tử xuất hiện ngay ở minsup tương đối cao và số luật tăng đều khi giảm "
              "minsup.")

    h2(doc, "7.4. Thí nghiệm mở rộng ở mức sản phẩm")
    para(doc, "Ở mức danh mục, không gian item chỉ khoảng 70 phần tử nên chưa đủ để thấy rõ ưu "
              "thế lý thuyết của FP-Growth. Nhóm thực hiện thêm thí nghiệm ở mức `product_id`, "
              "chỉ xét đơn có từ hai sản phẩm khác nhau, với ngưỡng là số đơn tối thiểu giảm dần.")
    p = res["product"]
    if p is not None and len(p):
        rows = [[str(int(r["min_count"])), str(int(r["n_frequent_items"])),
                 f"{int(r['n_candidate_pairs']):,}".replace(",", "."),
                 vn(r["apriori_est_mem_gb"], 2), sec(r["apriori_sec"]), sec(r["fpgrowth_sec"]),
                 str(int(r["n_itemsets"])),
                 "ok" if r["apriori_status"] == "ok" else "bỏ qua (thiếu RAM)"]
                for _, r in p.iterrows()]
        table(doc, ["min_count", "Sản phẩm phổ biến", "Cặp ứng viên", "RAM Apriori (GB)",
                    "Apriori (s)", "FP-Growth (s)", "Số tập phổ biến", "Apriori"],
              rows, [1.7, 2.0, 2.2, 2.0, 1.8, 1.9, 1.9, 2.3],
              cap=f"Bảng 7.4: Apriori và FP-Growth ở mức sản phẩm "
                  f"({int(p['n_transactions'].iloc[0]):,} giỏ đa sản phẩm)".replace(",", "."),
              align=["c", "r", "r", "r", "r", "r", "r", "c"], font_size=10)
        both = p.dropna(subset=["apriori_sec"])
        cross = both[both["fpgrowth_sec"] < both["apriori_sec"]]
        skipped = p[p["apriori_status"] != "ok"]
        txt = (f"Khi ngưỡng giảm từ {int(p['min_count'].iloc[0])} xuống "
               f"{int(p['min_count'].iloc[-1])} đơn, số sản phẩm phổ biến tăng từ "
               f"{int(p['n_frequent_items'].iloc[0])} lên {int(p['n_frequent_items'].iloc[-1])}, "
               f"kéo theo số cặp ứng viên của Apriori tăng từ "
               f"{int(p['n_candidate_pairs'].iloc[0]):,} lên "
               f"{int(p['n_candidate_pairs'].iloc[-1]):,}. ".replace(",", "."))
        if len(cross):
            txt += (f"FP-Growth bắt đầu nhanh hơn Apriori từ ngưỡng {int(cross['min_count'].iloc[0])} "
                    f"đơn trở xuống. ")
        if len(skipped):
            txt += (f"Ở ngưỡng {', '.join(str(int(v)) for v in skipped['min_count'])} đơn, Apriori "
                    f"cần ước tính tới {vn(skipped['apriori_est_mem_gb'].max(), 1)} GB RAM nên không "
                    f"thể chạy, trong khi FP-Growth vẫn hoàn thành trong "
                    f"{sec(skipped['fpgrowth_sec'].max())} s.")
        para(doc, txt)
    else:
        _bench_placeholder(doc, "Bảng 7.4: Apriori và FP-Growth ở mức sản phẩm "
                                "(nguồn: outputs/tables/benchmark_product_level.csv)", 9)
        para(doc, "[[Nhận xét: ngưỡng mà FP-Growth bắt đầu nhanh hơn; ngưỡng Apriori vượt ngân "
                  "sách bộ nhớ.]]")
    figure(doc, out_fig / "06_benchmark_product_level.png",
           "Hình 7.3: Mức sản phẩm – thời gian chạy và sự bùng nổ ứng viên khi ngưỡng giảm",
           width_cm=16, hint="outputs/figures/06_benchmark_product_level.png")

    h2(doc, "7.5. Thảo luận về hiệu năng hai thuật toán")
    para(doc, "Kết hợp hai thí nghiệm, nhóm rút ra một kết luận có điều kiện thay vì khẳng định "
              "tuyệt đối “FP-Growth luôn nhanh hơn”:")
    winner = category_winner(res)
    cross_at, skipped = product_findings(res)
    if winner == "Apriori":
        small = ("**Khi không gian item nhỏ** (khoảng 70 danh mục), Apriori nhanh hơn: số ứng viên "
                 "chỉ vài nghìn, phép đếm vector hóa của `mlxtend` hoàn thành rất nhanh, còn chi "
                 "phí dựng FP-tree bằng Python khiến FP-Growth chậm hơn.")
    elif winner == "FP-Growth":
        small = ("**Ngay ở mức danh mục**, FP-Growth đã nhanh hơn Apriori ở đa số mức minsup, cho "
                 "thấy chi phí sinh và đếm ứng viên của Apriori đã chiếm ưu thế ngay cả khi số "
                 "item chỉ khoảng 70.")
    else:
        small = ("**Khi không gian item nhỏ** (khoảng 70 danh mục): [[thuật toán nào nhanh hơn và "
                 "lý do, theo Bảng 7.2]].")
    if cross_at is not None or skipped:
        large = ("**Khi không gian item lớn và minsup thấp** (mức sản phẩm), số ứng viên tăng theo "
                 "bình phương số item phổ biến"
                 + (f"; FP-Growth nhanh hơn từ ngưỡng {cross_at} đơn trở xuống" if cross_at else "")
                 + ("; Apriori vượt ngân sách bộ nhớ ở ngưỡng thấp nhất" if skipped else "")
                 + ". FP-Growth không sinh ứng viên nên giữ được hiệu năng, đúng như ưu thế lý "
                   "thuyết đã nêu ở mục 6.4.")
    elif skipped is False:
        large = ("**Ở mức sản phẩm**, trong dải ngưỡng khảo sát Apriori vẫn chưa bị FP-Growth vượt "
                 "qua; cần giảm ngưỡng sâu hơn để thấy điểm giao nhau dự đoán bởi lý thuyết.")
    else:
        large = ("**Khi không gian item lớn và minsup thấp** (mức sản phẩm): [[ngưỡng FP-Growth "
                 "bắt đầu nhanh hơn; ngưỡng Apriori hết bộ nhớ, theo Bảng 7.4]].")
    bullets(doc, [
        small,
        large,
        "**Về độ chính xác**, ở mọi mức minsup đều có cột kiểm chứng tập phổ biến của hai thuật "
        "toán trùng khớp hoàn toàn: sự khác biệt chỉ nằm ở hiệu năng, không nằm ở kết quả.",
    ])
    para(doc, "Do đó, với bài toán gợi ý ở mức danh mục của Olist, cả hai thuật toán đều phù "
              "hợp về thời gian chạy; nếu mở rộng xuống mức sản phẩm hoặc dữ liệu lớn hơn, FP-Growth là lựa chọn "
              "an toàn hơn.")

    h2(doc, "7.6. Vì sao lift trên toàn bộ giỏ hàng nhỏ hơn 1")
    para(doc, "Bảng 7.5 so sánh lift của các cặp danh mục xuất hiện cùng nhau nhiều nhất, tính "
              "theo hai cách: trên toàn bộ giao dịch (ALL) và chỉ trên các giao dịch có từ hai "
              "danh mục (MULTI).")
    pl = res.get("pairs")
    if pl is not None and len(pl):
        rows = [[_pretty(r["cat_a"]), _pretty(r["cat_b"]), str(int(r["pair_count"])),
                 vn(r["lift_all"], 2), vn(r["lift_multi"], 2)] for _, r in pl.head(12).iterrows()]
        table(doc, ["Danh mục A", "Danh mục B", "Số đơn chung", "Lift ALL", "Lift MULTI"], rows,
              [4.6, 4.6, 2.2, 2.0, 2.1], cap="Bảng 7.5: Lift của các cặp danh mục phổ biến – "
                                             "ALL và MULTI", align=["l", "l", "r", "r", "r"],
              font_size=10.5)
        below = (pl["lift_all"] < 1).mean()
        above = (pl["lift_multi"] >= 1.2).sum()
        para(doc, f"Trong {len(pl)} cặp danh mục cùng xuất hiện ở ít nhất "
                  f"{cfg.get('MIN_PAIR_COUNT', 5)} đơn, có {pct(below, 0)} cặp có lift ALL nhỏ "
                  f"hơn 1, trong khi {above} cặp có lift MULTI từ 1,2 trở lên.")
    else:
        table(doc, ["Danh mục A", "Danh mục B", "Số đơn chung", "Lift ALL", "Lift MULTI"],
              [[PH] * 5 for _ in range(8)], [4.6, 4.6, 2.2, 2.0, 2.1],
              cap="Bảng 7.5: Lift của các cặp danh mục phổ biến – ALL và MULTI "
                  "(nguồn: outputs/tables/pair_lift_all_vs_multi.csv)", font_size=10.5)
    para(doc, "Hiện tượng này có thể giải thích bằng công thức lift = support(A ∪ B) / "
              "(support(A) · support(B)). Mẫu số là tần suất kỳ vọng nếu A và B độc lập, được "
              "tính từ **mọi** đơn có A và **mọi** đơn có B. Tuy nhiên hơn 99% đơn hàng chỉ có "
              "một danh mục, tức là về mặt cấu trúc A và B gần như không thể xuất hiện cùng nhau. "
              "Tử số vì vậy luôn nhỏ hơn mức kỳ vọng, và lift bị kéo xuống dưới 1 với hầu hết mọi "
              "cặp, kể cả những cặp có quan hệ bổ trợ rõ ràng. Nói cách khác, lift ALL đo việc "
              "“khách có mua nhiều danh mục hay không”, chứ không đo việc “danh mục nào đi với "
              "danh mục nào”. Khi xét riêng nhóm giỏ đa danh mục, yếu tố cấu trúc này bị loại bỏ "
              "và lift phản ánh đúng mức độ liên kết giữa các danh mục.")
    para(doc, "Bản thân phát hiện này đã là một insight kinh doanh quan trọng: **rào cản lớn nhất "
              "của Olist không phải là chọn gợi ý nào, mà là khách hàng gần như không có thói "
              "quen mua nhiều danh mục trong một đơn**. Chiến lược cross-selling vì vậy cần đi kèm "
              "các ưu đãi khuyến khích gộp đơn, ví dụ miễn phí vận chuyển khi đơn có từ hai danh "
              "mục.")

    h2(doc, "7.7. Đánh giá tập luật thu được (kịch bản MULTI)")
    rules = res["rules"]
    if rules is not None and len(rules):
        strong = rules[rules["lift"] >= 1.2]
        para(doc, f"Với tham số luật cuối cùng (mục 6.6) trên các giỏ đa danh mục, thu được {num(len(rules))} luật có "
                  f"confidence vượt ngưỡng, trong đó {num(len(strong))} luật có lift ≥ 1,2. Lift "
                  f"trung vị của toàn bộ luật là {vn(rules['lift'].median(), 2)}, confidence "
                  f"trung vị {pct(rules['confidence'].median())}, support trung vị "
                  f"{vn(rules['support'].median(), 5)}.")
    else:
        para(doc, "Với tham số luật cuối cùng, thu được [[số luật]] luật, trong đó [[số luật lift "
                  "≥ 1,2]] luật có lift vượt ngưỡng. Lift trung vị [[...]], confidence trung vị "
                  "[[...]].")
    figure(doc, out_fig / "03_rules_scatter.png",
           "Hình 7.4: Phân bố luật theo Support – Confidence, màu thể hiện Lift",
           width_cm=13, hint="outputs/figures/03_rules_scatter.png")
    para(doc, "Biểu đồ phân tán cho thấy phần lớn luật tập trung ở vùng support thấp, trong đó "
              "một số luật có lift cao (màu sáng). Đây là các quan hệ bổ trợ thật sự giữa hai "
              "danh mục, dù số đơn không nhiều. Ngược lại, các luật có support cao nhất thường "
              "liên quan đến các danh mục rất phổ biến (như bed_bath_table, furniture_decor) và "
              "có lift gần 1, tức là xuất hiện cùng nhau chủ yếu vì cả hai đều phổ biến, chứ "
              "không do liên kết đặc biệt.")
    figure(doc, out_fig / "05_lift_heatmap.png",
           "Hình 7.5: Heatmap lift giữa các danh mục trong các luật mạnh",
           width_cm=13, hint="outputs/figures/05_lift_heatmap.png")
    para(doc, "Heatmap có tính gần đối xứng qua đường chéo vì lift là độ đo đối xứng. Các ô có "
              "giá trị lớn tập trung thành từng cụm danh mục cùng chủ đề sử dụng; những cụm này "
              "được phân tích chi tiết ở mục 8.")


# ============================================================================
# 8. DIỄN GIẢI TRI THỨC VÀ ỨNG DỤNG
# ============================================================================
def _pretty(c):
    return c.replace("_", " ")


# Cụm chủ đề cho mục 8.4: (tên, tập danh mục, diễn giải). Luật thuộc cụm khi cả hai vế
# đều nằm trong tập danh mục của cụm; cụm không có luật nào sẽ tự bị bỏ qua.
CLUSTERS = [
    ("Không gian sống – phòng ngủ và trang trí nhà",
     {"bed_bath_table", "home_confort", "furniture_decor", "art", "construction_tools_lights",
      "home_construction", "furniture_living_room", "housewares", "home_comfort_2"},
     "Đây là cụm có số đơn hỗ trợ lớn nhất. Khách mua đồ giường ngủ, đồ dùng tiện nghi trong "
     "nhà, tranh ảnh, đèn hay đồ nội thất phòng khách thường đang trong quá trình **sắp xếp hoặc "
     "trang trí lại không gian sống**, nên dễ mua thêm các món cùng phong cách. Luật home "
     "confort → bed bath table có confidence rất cao cho thấy hai danh mục này gần như là một "
     "nhu cầu. Người bán nên xây dựng các bộ sản phẩm theo phòng (phòng ngủ, phòng khách) và "
     "gợi ý đồ trang trí ngay trên trang sản phẩm đồ giường, nội thất."),
    ("Mẹ và bé – đồ chơi – quà tặng",
     {"baby", "toys", "cool_stuff", "stationery", "luggage_accessories"},
     "Các danh mục đồ dùng cho bé, đồ chơi, quà lưu niệm (cool stuff) và văn phòng phẩm liên kết "
     "chặt với nhau. Hành vi chung là **mua sắm cho trẻ em hoặc mua quà**: phụ huynh mua đồ dùng "
     "cho bé kèm đồ chơi, hoặc mua đồ chơi kèm văn phòng phẩm cho mùa tựu trường. Gợi ý phù "
     "hợp là combo “đồ dùng cho bé + đồ chơi theo độ tuổi” và các bộ quà tặng sinh nhật."),
    ("Chăm sóc cá nhân và sức khỏe",
     {"health_beauty", "perfumery", "sports_leisure"},
     "Nước hoa và mỹ phẩm, chăm sóc sức khỏe là cặp có lift cao, phản ánh **nhu cầu chăm sóc bản "
     "thân** được mua trọn gói trong một lần. Liên kết giữa sức khỏe – làm đẹp và thể thao – giải "
     "trí cho thấy nhóm khách quan tâm lối sống lành mạnh. Có thể gợi ý nước hoa trên trang mỹ "
     "phẩm, và thực phẩm chức năng hoặc sản phẩm chăm sóc cơ thể cho khách mua đồ thể thao."),
    ("Thiết bị công nghệ và phụ kiện",
     {"telephony", "computers_accessories", "electronics", "audio", "watches_gifts", "auto",
      "cool_stuff"},
     "Điện thoại, linh kiện máy tính, đồ điện tử và thiết bị âm thanh thường được mua cùng nhau, "
     "do khách mua **thiết bị chính kèm phụ kiện** (ốp lưng, tai nghe, cáp sạc…). Luật audio → "
     "watches gifts có lift rất cao nhưng chỉ dựa trên 6 đơn, nên cần thêm dữ liệu trước khi "
     "triển khai rộng. Gợi ý phù hợp là khối “phụ kiện tương thích” ở trang sản phẩm công nghệ."),
    ("Sửa chữa nhà cửa và làm vườn",
     {"garden_tools", "construction_tools_construction", "home_construction"},
     "Dụng cụ làm vườn đi cùng dụng cụ xây dựng và vật tư sửa nhà, phản ánh các **dự án tự làm "
     "(DIY)** quanh nhà. Khách đang làm một dự án thường cần nhiều loại dụng cụ cùng lúc. Người "
     "bán có thể tạo các gói “bộ dụng cụ cho dự án” và gợi ý chéo giữa hai danh mục."),
]


def section8(doc, res, cfg, out_fig: Path):
    h1(doc, "8. Diễn giải tri thức và ứng dụng")

    h2(doc, "8.1. Quy trình chọn luật tiêu biểu")
    para(doc, "Từ tập luật thô, nhóm áp dụng bốn bước lọc để chọn ra các luật có giá trị kinh "
              "doanh:")
    bullets(doc, [
        f"**Loại luật gần độc lập:** chỉ giữ luật có lift ≥ {cfg.get('MIN_LIFT', 1.2)}. Các luật "
        "có lift xấp xỉ 1 không cho thông tin gì hơn so với gợi ý ngẫu nhiên.",
        f"**Đảm bảo độ tin cậy thống kê:** luật phải được hỗ trợ bởi ít nhất "
        f"{cfg.get('MIN_PAIR_COUNT', 10)} đơn hàng.",
        "**Khử trùng chiều:** A → B và B → A có cùng support và lift; nhóm chỉ giữ chiều có "
        "confidence cao hơn để danh sách không bị lặp ý.",
        f"**Xếp hạng:** sắp xếp theo lift giảm dần (cùng lift thì xét confidence) và lấy "
        f"{cfg.get('TOP_K', 20)} luật đầu tiên.",
    ], numbered=True)

    h2(doc, "8.2. Các luật tiêu biểu")
    top = res["top"]
    if top is not None and len(top):
        rows = [[str(int(r["rank"])), _pretty(r["antecedents_str"]), _pretty(r["consequents_str"]),
                 vn(r["support"], 4), str(int(r["pair_count"])), pct(r["confidence"]),
                 vn(r["lift"], 2)] for _, r in top.iterrows()]
        table(doc, ["#", "Tiền đề (X)", "Hệ quả (Y)", "Support", "Số đơn", "Confidence", "Lift"],
              rows, [0.9, 4.6, 4.2, 1.7, 1.4, 1.8, 1.4],
              cap=f"Bảng 8.1: Top {len(top)} luật mua kèm có giá trị nhất",
              align=["c", "l", "l", "r", "r", "r", "r"], font_size=10.5)
    else:
        table(doc, ["#", "Tiền đề (X)", "Hệ quả (Y)", "Support", "Số đơn", "Confidence", "Lift"],
              [[str(i), PH, PH, PH, PH, PH, PH] for i in range(1, 21)],
              [0.9, 4.6, 4.2, 1.7, 1.4, 1.8, 1.4],
              cap="Bảng 8.1: Top 20 luật mua kèm có giá trị nhất "
                  "(nguồn: outputs/tables/top20_rules.csv)", align=["c"] * 7, font_size=10.5)
    figure(doc, out_fig / "04_top_rules_lift.png", "Hình 8.1: Top luật mua kèm xếp theo Lift",
           width_cm=16, hint="outputs/figures/04_top_rules_lift.png")

    h2(doc, "8.3. Diễn giải từng luật")
    para(doc, "Mỗi luật được diễn giải theo một khuôn mẫu thống nhất, dễ hiểu với bộ phận kinh "
              "doanh: *“Trong các đơn có từ hai danh mục, khách mua X có c% khả năng mua thêm Y, "
              "cao gấp L lần so với một giỏ đa danh mục bất kỳ”*. Mười luật đứng đầu được diễn "
              "giải dưới đây.")
    if top is not None and len(top):
        for _, r in top.head(10).iterrows():
            bullet(doc, f"**Luật {int(r['rank'])} – {_pretty(r['antecedents_str'])} → "
                        f"{_pretty(r['consequents_str'])}:** trong các giỏ đa danh mục có "
                        f"*{_pretty(r['antecedents_str'])}*, {pct(r['confidence'])} giỏ có thêm "
                        f"*{_pretty(r['consequents_str'])}*, cao gấp {vn(r['lift'], 1)} lần tỷ lệ "
                        f"chung của *{_pretty(r['consequents_str'])}* trong nhóm này "
                        f"({pct(r['consequent support'], 1)}). Luật dựa trên "
                        f"{int(r['pair_count'])} đơn hàng thực tế.")
    else:
        for i in range(1, 4):
            bullet(doc, f"**Luật {i} – [[X]] → [[Y]]:** trong số khách mua [[X]], có [[c%]] mua "
                        f"thêm [[Y]], cao gấp [[L]] lần tỷ lệ chung. Luật dựa trên [[n]] đơn hàng.")

    h2(doc, "8.4. Nhóm insight theo chủ đề")
    para(doc, "Khi đặt các luật tiêu biểu cạnh nhau, có thể nhận ra các cụm danh mục cùng phục "
              "vụ một **nhu cầu sử dụng** hay một **sự kiện mua sắm**. Phân tích theo cụm giúp "
              "chuyển từ những luật rời rạc thành chiến lược kinh doanh. Nhóm đề xuất khung "
              "phân tích gồm các câu hỏi: các danh mục trong cụm phục vụ cùng một không gian "
              "(phòng ngủ, nhà bếp…), cùng một đối tượng (trẻ sơ sinh, thú cưng…) hay cùng một "
              "dịp (quà tặng, chuyển nhà…)? Quan hệ là bổ trợ chức năng hay tiện mua chung? "
              "Luật có đối xứng không, tức là chiều ngược lại có confidence tương đương không?")
    rules = res["rules"]
    if rules is None or rules.empty:
        para(doc, "[[Nhóm điền 3–4 cụm insight dựa trên Bảng 8.1, mỗi cụm gồm: tên cụm, các luật "
                  "thuộc cụm, giải thích hành vi khách hàng, mức độ mạnh (lift, số đơn).]]")
        return_after_clusters = True
    else:
        return_after_clusters = False
        para(doc, "Áp dụng khung trên cho các luật có lift ≥ ngưỡng, nhóm xác định được các cụm "
                  "dưới đây. Danh sách luật trong mỗi cụm được lấy tự động từ kết quả khai thác; "
                  "phần diễn giải là nhận định của nhóm.")
    strong = (rules[(rules["lift"] >= cfg.get("MIN_LIFT", 1.2))
                    & (rules["pair_count"] >= cfg.get("MIN_PAIR_COUNT", 5))]
              if not return_after_clusters else None)
    k = 0
    for name, cats, story in CLUSTERS if strong is not None else []:
        sub = strong[strong["antecedents_str"].isin(cats) & strong["consequents_str"].isin(cats)]
        if sub.empty:
            continue
        # mỗi cặp chỉ giữ chiều confidence cao hơn
        sub = sub.assign(key=[" | ".join(sorted((a, c))) for a, c in
                              zip(sub["antecedents_str"], sub["consequents_str"])])
        sub = sub.sort_values("confidence", ascending=False).drop_duplicates("key") \
                 .sort_values("lift", ascending=False)
        k += 1
        h3(doc, f"8.4.{k}. Cụm {k}: {name}")
        para(doc, story)
        for _, r in sub.iterrows():
            bullet(doc, f"{_pretty(r['antecedents_str'])} → {_pretty(r['consequents_str'])}: "
                        f"lift {vn(r['lift'], 2)}, confidence {pct(r['confidence'])}, "
                        f"{int(r['pair_count'])} đơn.")

    h2(doc, "8.5. Đề xuất chiến lược cross-selling")
    para(doc, "Không phải luật nào cũng nên được khai thác theo cùng một cách. Dựa trên đặc "
              "điểm độ đo, nhóm phân loại luật thành bốn nhóm và đề xuất hành động phù hợp cho "
              "từng nhóm (Bảng 8.2).")
    table(doc, ["Đặc điểm luật", "Ý nghĩa", "Hành động đề xuất", "Kênh triển khai"],
          [["Lift cao, confidence tương đối cao",
            "Quan hệ bổ trợ mạnh, khách thường cần cả hai",
            "Gợi ý “thường được mua cùng”, combo giảm giá khi mua cả hai",
            "Trang sản phẩm, giỏ hàng"],
           ["Lift cao, support thấp",
            "Ngách nhỏ nhưng liên kết chặt",
            "Gợi ý cá nhân hóa, email sau mua cho đúng nhóm khách",
            "Email, thông báo đẩy"],
           ["Confidence cao, lift chỉ hơi lớn hơn 1",
            "Hệ quả là danh mục phổ biến",
            "Không ưu tiên gợi ý (khách vẫn sẽ mua); dùng để tối ưu tồn kho",
            "Vận hành, kho"],
           ["Luật đối xứng (cả hai chiều đều mạnh)",
            "Cặp danh mục gắn bó hai chiều",
            "Trang tổng hợp theo chủ đề, bố trí liền kề trên trang danh mục",
            "Trang danh mục, landing page"]],
          [3.6, 3.6, 5.0, 3.3], cap="Bảng 8.2: Ma trận hành động theo đặc điểm luật",
          font_size=10.5)
    para(doc, "Với các luật trong Bảng 8.1, nhóm đề xuất các hành động cụ thể như Bảng 8.3.")
    if top is not None and len(top):
        rows = []
        for _, r in top.head(8).iterrows():
            x, y = _pretty(r["antecedents_str"]), _pretty(r["consequents_str"])
            if r["confidence"] >= top["confidence"].median():
                act = f"Hiển thị {y} trong khối “thường mua cùng” ở trang {x}; combo giảm giá"
            else:
                act = f"Email/voucher {y} gửi cho khách vừa mua {x}"
            rows.append([f"{x} → {y}", vn(r["lift"], 1), pct(r["confidence"]), act])
        table(doc, ["Luật", "Lift", "Conf.", "Hành động cross-selling"], rows,
              [5.2, 1.4, 1.7, 7.2], cap="Bảng 8.3: Đề xuất hành động cho các luật tiêu biểu",
              align=["l", "r", "r", "l"], font_size=10.5)
    else:
        table(doc, ["Luật", "Lift", "Conf.", "Hành động cross-selling"],
              [[PH, PH, PH, PH] for _ in range(6)], [5.2, 1.4, 1.7, 7.2],
              cap="Bảng 8.3: Đề xuất hành động cho các luật tiêu biểu", font_size=10.5)

    h2(doc, "8.6. Đo lường hiệu quả khi triển khai")
    para(doc, "Luật kết hợp chỉ phản ánh mối tương quan trong dữ liệu quá khứ, chưa chứng minh "
              "quan hệ nhân quả. Vì vậy, trước khi triển khai rộng, mỗi đề xuất nên được kiểm "
              "chứng bằng thử nghiệm A/B: một nhóm khách thấy gợi ý, nhóm đối chứng không thấy. "
              "Các chỉ số đánh giá đề xuất gồm:")
    bullets(doc, [
        "**Tỷ lệ mua kèm (attach rate):** tỷ lệ đơn chứa danh mục X có thêm danh mục Y.",
        "**Giá trị đơn hàng trung bình (AOV)** và **số danh mục trung bình mỗi đơn**.",
        "**Tỷ lệ nhấp (CTR)** vào khối gợi ý và **tỷ lệ chuyển đổi** từ gợi ý thành mua.",
        "**Chi phí vận chuyển trên mỗi sản phẩm**, kỳ vọng giảm khi nhiều món đi chung một đơn.",
    ])


# ============================================================================
# 9. SẢN PHẨM DEMO
# ============================================================================
def section9(doc, fig_dir: Path, shot_dir: Path):
    h1(doc, "9. Sản phẩm demo")

    h2(doc, "9.1. Mục tiêu và công nghệ")
    para(doc, "Sản phẩm demo là một ứng dụng web xây dựng bằng **Streamlit**, giúp người dùng "
              "không chuyên kỹ thuật (nhân viên marketing, nhà bán hàng) tra cứu gợi ý mua kèm "
              "trực tiếp từ kết quả khai thác. Streamlit được chọn vì cho phép xây dựng giao diện "
              "tương tác hoàn toàn bằng Python, tích hợp tự nhiên với pandas và mlxtend; biểu "
              "đồ tương tác dùng **Plotly**.")
    table(doc, ["Tệp", "Vai trò"],
          [["`app.py`", "Mã nguồn ứng dụng (giao diện, logic gợi ý)"],
           ["`models/rules.csv`", "Luật kết hợp hai chiều, lift > 1, sinh bởi Phase 2"],
           ["`outputs/tables/benchmark_*.csv`", "Kết quả benchmark hiển thị ở tab so sánh"],
           ["`data/processed/order_items_clean.csv`", "Dữ liệu sạch cho chế độ khai thác trực tiếp"],
           ["`requirements.txt`", "Danh sách thư viện cần cài"]],
          [6.0, 9.5], cap="Bảng 9.1: Các thành phần của ứng dụng demo")

    h2(doc, "9.2. Chức năng")
    table(doc, ["Khu vực", "Chức năng"],
          [["Thanh bên – Nguồn luật",
            "Chọn dùng luật đã khai thác sẵn, hoặc khai thác trực tiếp với thuật toán (Apriori/"
            "FP-Growth) và minsup do người dùng chọn; hiển thị thời gian chạy, số tập phổ biến, "
            "số luật"],
           ["Thanh bên – Ngưỡng lọc",
            "Confidence tối thiểu, lift tối thiểu (mặc định 1,2), số đơn tối thiểu, tiêu chí xếp "
            "hạng, số gợi ý tối đa"],
           ["Tab Gợi ý theo danh mục",
            "Chọn một danh mục; hiển thị 3 thẻ gợi ý hàng đầu, biểu đồ lift có vạch lift = 1, "
            "câu diễn giải cho marketing và bảng chi tiết"],
           ["Tab Gợi ý theo giỏ hàng",
            "Chọn nhiều danh mục đang có trong giỏ; dùng cả luật 1 → 1 và 2 → 1; loại danh mục "
            "đã có trong giỏ"],
           ["Tab Khám phá luật",
            "Lọc luật theo từ khóa, biểu đồ phân tán support – confidence, tải luật ra CSV"],
           ["Tab So sánh thuật toán",
            "Biểu đồ và bảng benchmark hai kịch bản và thí nghiệm mức sản phẩm"],
           ["Tab Hướng dẫn", "Luồng xử lý, công thức và ý nghĩa kinh doanh của các độ đo"]],
          [4.5, 11.0], cap="Bảng 9.2: Chức năng của ứng dụng", font_size=11)

    h2(doc, "9.3. Luồng xử lý gợi ý")
    flow = fig_dir / "app_flow.png"
    draw_app_flow(flow)
    figure(doc, flow, "Hình 9.1: Luồng xử lý khi tạo gợi ý mua kèm", width_cm=16)
    para(doc, "Khi người dùng chọn một danh mục hoặc một giỏ hàng *G*, ứng dụng duyệt tập luật và "
              "giữ lại các luật *X → Y* thỏa: (1) *X ⊆ G*, tức toàn bộ tiền đề có trong giỏ; "
              "(2) *Y ∩ G = ∅*, tức không gợi ý thứ khách đã có; (3) thỏa các ngưỡng confidence, "
              "lift và số đơn. Nếu một danh mục được gợi ý bởi nhiều luật, ứng dụng chỉ giữ luật "
              "mạnh nhất theo tiêu chí xếp hạng, rồi trả về top-N. Luật được nạp một lần và lưu "
              "cache bằng `st.cache_data`, nên mỗi lần thay đổi ngưỡng chỉ tốn vài mili giây.")
    code_block(doc, '''
mask = (rules["ant_set"].apply(lambda a: a <= cart)            # X ⊆ giỏ
        & rules["cons_set"].apply(lambda c: not (c & cart))    # Y ∉ giỏ
        & (rules["confidence"] >= min_conf)
        & (rules["lift"] >= min_lift)
        & (rules["pair_count"] >= min_count))
best = (matched.sort_values([sort_by, "confidence"], ascending=False)
        .drop_duplicates("recommend").head(top_n))''',
               cap="Đoạn mã 9.1: Logic so khớp và xếp hạng gợi ý")

    h2(doc, "9.4. Giao diện")
    for name, cap in (("app_category.png", "Hình 9.2: Tab gợi ý theo danh mục"),
                      ("app_cart.png", "Hình 9.3: Tab gợi ý theo giỏ hàng"),
                      ("app_rules.png", "Hình 9.4: Tab khám phá luật"),
                      ("app_algo.png", "Hình 9.5: Tab so sánh thuật toán")):
        figure(doc, shot_dir / name, cap, width_cm=15.5,
               hint=f"ảnh chụp màn hình, lưu tại report/screenshots/{name}")

    h2(doc, "9.5. Hướng dẫn cài đặt và chạy")
    code_block(doc, '''
pip install -r requirements.txt
python src/phase1_preprocessing.py      # làm sạch, ghép bảng
python src/phase2_mining.py             # khai thác, sinh models/rules.csv
streamlit run app.py                    # mở http://localhost:8501''',
               cap="Đoạn mã 9.2: Các lệnh cài đặt và chạy ứng dụng")
    para(doc, "Ứng dụng xử lý trường hợp chưa có tệp luật hoặc dữ liệu sạch bằng thông báo hướng "
              "dẫn rõ ràng, và tự chọn danh mục mặc định là danh mục có nhiều luật mạnh nhất để "
              "màn hình đầu tiên luôn có kết quả minh họa.")


# ============================================================================
# 10. KẾT LUẬN
# ============================================================================
def section10(doc, res):
    h1(doc, "10. Kết luận, hạn chế và hướng phát triển")

    h2(doc, "10.1. Kết quả đạt được")
    para(doc, "Đề tài đã hoàn thành đầy đủ các mục tiêu đề ra, cụ thể qua việc trả lời năm câu "
              "hỏi khai thác:")
    bk = res["baskets"]
    if bk is not None and len(bk):
        multi_share = bk.loc[bk.iloc[:, 0] >= 2, "n_orders"].sum() / bk["n_orders"].sum()
        q1 = (f"chỉ khoảng {pct(multi_share, 2)} đơn hàng chứa từ hai danh mục trở lên; hành vi "
              f"mua kèm hiếm nhưng không phải không có.")
    else:
        q1 = "chỉ khoảng [[x%]] đơn hàng chứa từ hai danh mục trở lên; hành vi mua kèm hiếm."
    winner = category_winner(res)
    cross_at, skipped = product_findings(res)
    q4 = "hai thuật toán cho tập phổ biến giống hệt nhau; "
    q4 += (f"ở mức danh mục {winner} nhanh hơn ở đa số mức minsup" if winner
           else "ở mức danh mục [[thuật toán nhanh hơn]]")
    if cross_at is not None or skipped:
        q4 += "; ở mức sản phẩm với minsup thấp FP-Growth vượt trội"
        q4 += " và Apriori không chạy được do bùng nổ ứng viên." if skipped else "."
    else:
        q4 += "; ở mức sản phẩm [[nhận xét theo Bảng 7.4]]."
    top = res["top"]
    q2 = (f"đã xác định {len(top)} luật tiêu biểu, mạnh nhất là "
          f"{_pretty(top.iloc[0]['antecedents_str'])} → {_pretty(top.iloc[0]['consequents_str'])} "
          f"với lift {vn(top.iloc[0]['lift'], 1)}." if top is not None and len(top)
          else "đã xác định [[n]] luật tiêu biểu, mạnh nhất là [[X → Y]] với lift [[L]].")
    bullets(doc, [
        f"**Q1 – Mức độ mua kèm:** {q1}",
        f"**Q2 – Cặp danh mục liên kết mạnh:** {q2}",
        "**Q3 – Gợi ý cho từng danh mục:** được cung cấp trực tiếp qua ứng dụng Streamlit với "
        "các ngưỡng tùy chỉnh.",
        f"**Q4 – So sánh thuật toán:** {q4}",
        "**Q5 – Hành động kinh doanh:** đề xuất ma trận hành động theo đặc điểm luật và các hành "
        "động cụ thể cho từng luật tiêu biểu, kèm bộ chỉ số đo lường.",
    ])
    para(doc, "Về mặt kỹ thuật, quy trình tiền xử lý có kiểm chứng (validate quan hệ khóa, assert "
              "số dòng) đảm bảo dữ liệu đầu vào đúng; toàn bộ thực nghiệm có thể tái lập bằng ba "
              "lệnh, và báo cáo tự động cập nhật số liệu từ kết quả chạy.")

    h2(doc, "10.2. Hạn chế")
    bullets(doc, [
        "**Dữ liệu rất thưa:** phần lớn đơn chỉ có một danh mục, nên luật phải khai thác trên "
        "nhóm giỏ đa danh mục; confidence và support là xác suất có điều kiện trong nhóm này, và "
        "số đơn hỗ trợ mỗi luật còn nhỏ.",
        "**Mức danh mục còn thô:** một số danh mục rất rộng (ví dụ housewares) gộp nhiều loại "
        "sản phẩm khác nhau, làm giảm độ cụ thể của gợi ý.",
        "**Chỉ xét trong một đơn hàng:** chưa khai thác hành vi mua lặp lại của cùng khách hàng "
        "qua nhiều đơn (khách Olist phần lớn chỉ mua một lần).",
        "**Tương quan, không phải nhân quả:** luật chưa được kiểm chứng bằng thử nghiệm thực tế.",
        "**Dữ liệu cũ và theo vùng:** giai đoạn 2016–2018 tại Brazil, có thể không còn phản ánh "
        "đúng hành vi hiện tại hoặc ở thị trường khác.",
    ])

    h2(doc, "10.3. Hướng phát triển")
    bullets(doc, [
        "**Khai thác luật tuần tự** theo `customer_unique_id` để gợi ý cho lần mua tiếp theo.",
        "**Khai thác đa mức** (multi-level association rules) kết hợp danh mục và sản phẩm, hoặc "
        "nhóm danh mục thành phân cấp để tăng support.",
        "**Phân đoạn luật** theo bang, mùa vụ, khoảng giá để có gợi ý theo ngữ cảnh.",
        "**Kết hợp với lọc cộng tác** (collaborative filtering) hoặc mô hình embedding để xử lý "
        "các danh mục ít dữ liệu.",
        "**Triển khai ứng dụng** lên Streamlit Community Cloud và thử nghiệm A/B với dữ liệu "
        "thực tế.",
    ])


# ============================================================================
# 11. TÀI LIỆU THAM KHẢO
# ============================================================================
REFERENCES = [
    "Agrawal, R., Imieliński, T., & Swami, A. (1993). Mining association rules between sets of "
    "items in large databases. *Proceedings of the 1993 ACM SIGMOD International Conference on "
    "Management of Data*, 207–216.",
    "Agrawal, R., & Srikant, R. (1994). Fast algorithms for mining association rules. "
    "*Proceedings of the 20th International Conference on Very Large Data Bases (VLDB)*, 487–499.",
    "Brin, S., Motwani, R., Ullman, J. D., & Tsur, S. (1997). Dynamic itemset counting and "
    "implication rules for market basket data. *Proceedings of the 1997 ACM SIGMOD International "
    "Conference on Management of Data*, 255–264.",
    "Chapman, P., Clinton, J., Kerber, R., Khabaza, T., Reinartz, T., Shearer, C., & Wirth, R. "
    "(2000). *CRISP-DM 1.0: Step-by-step data mining guide*. SPSS Inc.",
    "Han, J., Kamber, M., & Pei, J. (2012). *Data mining: Concepts and techniques* (3rd ed.). "
    "Morgan Kaufmann.",
    "Han, J., Pei, J., & Yin, Y. (2000). Mining frequent patterns without candidate generation. "
    "*Proceedings of the 2000 ACM SIGMOD International Conference on Management of Data*, 1–12.",
    "Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. *Computing in Science & "
    "Engineering, 9*(3), 90–95.",
    "McKinney, W. (2010). Data structures for statistical computing in Python. *Proceedings of the "
    "9th Python in Science Conference*, 56–61.",
    "Olist, & Sionek, A. (2018). *Brazilian e-commerce public dataset by Olist* [Data set]. "
    "Kaggle. https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce",
    "Piatetsky-Shapiro, G. (1991). Discovery, analysis, and presentation of strong rules. In "
    "G. Piatetsky-Shapiro & W. J. Frawley (Eds.), *Knowledge discovery in databases* (pp. "
    "229–248). AAAI/MIT Press.",
    "Raschka, S. (2018). MLxtend: Providing machine learning and data science utilities and "
    "extensions to Python's scientific computing stack. *Journal of Open Source Software, 3*(24), "
    "638.",
    "Streamlit Inc. (n.d.). *Streamlit documentation*. https://docs.streamlit.io",
    "Tan, P.-N., Steinbach, M., Karpatne, A., & Kumar, V. (2019). *Introduction to data mining* "
    "(2nd ed.). Pearson.",
]


def section11(doc):
    h1(doc, "11. Tài liệu tham khảo")
    for i, ref in enumerate(REFERENCES, 1):
        p = para(doc, f"[{i}] {ref}", indent=False, align="justify")
        p.paragraph_format.left_indent = Cm(0.9)        # thụt treo
        p.paragraph_format.first_line_indent = Cm(-0.9)


def build_part2(doc, root: Path, out_dir: Path, report_fig: Path):
    cfg = read_config(root / "src" / "phase2_mining.py")
    res = load_results(out_dir / "tables")
    out_fig = out_dir / "figures"
    page_break(doc)
    section6(doc, cfg, report_fig)
    page_break(doc)
    section7(doc, res, cfg, out_fig)
    page_break(doc)
    section8(doc, res, cfg, out_fig)
    page_break(doc)
    section9(doc, report_fig, root / "report" / "screenshots")
    page_break(doc)
    section10(doc, res)
    page_break(doc)
    section11(doc)
    return res
