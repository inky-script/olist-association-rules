# Checklist nộp bài – đối chiếu thang điểm

Tài liệu đối chiếu: *Yêu cầu nộp bài và thang điểm đồ án nhóm – Thực hành Khai thác dữ liệu*.

## 0. Ba điều phải xử lý trước tiên

- [ ] **Báo cáo Word phải do nhóm tự viết.** Đề bài ghi rõ: báo cáo có dấu hiệu dùng AI sẽ bị **0 điểm nội dung**.
      File `report/BaoCao_DoAn_Olist.docx` hiện có trong repo được sinh bằng AI, nên **không được nộp file này**.
      Chỉ dùng nó để tham khảo số liệu và hình.
- [ ] **Số liệu Word, code và video phải khớp nhau** (mâu thuẫn → 0 điểm phần mâu thuẫn).
      Lấy mọi con số từ lần chạy `NhomXX_Code.ipynb` dùng để nộp: thời gian chạy thay đổi mỗi lần chạy.
- [ ] **Bảng phân công:** dùng tên thật, ghi *công việc chính*, *công việc hỗ trợ*, và tỷ lệ đóng góp
      **cộng lại bằng 100%** (ví dụ 34% – 33% – 33%). Ghi mỗi người 100% sẽ bị trừ điểm.

## 1. Sản phẩm và tên tệp

| Sản phẩm | Tên tệp | Trạng thái |
|---|---|---|
| Báo cáo Word | `NhomXX_BaoCao.docx` | Nhóm tự viết |
| Notebook | `NhomXX_Code.ipynb` | Đã có, chạy được Run All |
| Link video (≤ 12 phút) | Ghi trong Phụ lục của Word | Nhóm quay |
| File nén | `NhomXX_TenDeTai.zip`: docx + ipynb + requirements.txt + README.md | Khi nộp |

Thay `XX` bằng số nhóm. Không đưa thư mục `data/` vào file nén; notebook tự báo cách tải dữ liệu.

## 2. Cấu trúc Word bắt buộc

- [ ] Trang bìa: tên học phần, mã/tên đề tài, lớp, 3 thành viên, giảng viên, **học kỳ**
- [ ] Bảng phân công (xem mục 0)
- [ ] Mục lục, danh mục hình, danh mục bảng (dùng *References → Insert Table of Figures*)
- [ ] Chương 1 – Tổng quan bài toán và dữ liệu
- [ ] Chương 2 – Tiền xử lý và chuẩn bị dữ liệu
- [ ] Chương 3 – Phương pháp (Apriori **và** FP-Growth, tham số, lý do chọn)
- [ ] Chương 4 – Thực nghiệm, kết quả, diễn giải, mô tả demo
- [ ] Chương 5 – Kết luận, hạn chế, **các trường hợp có thể gây sai lệch**, hướng phát triển
- [ ] Tài liệu tham khảo (trích dẫn nhất quán, có nguồn dữ liệu Kaggle)
- [ ] Phụ lục: **link video**, link GitHub, cấu trúc thư mục, hướng dẫn chạy, bảng kết quả đầy đủ

## 3. Đối chiếu nội dung Word với notebook

| Nội dung trong Word | Lấy từ notebook |
|---|---|
| Kích thước, giá trị thiếu, trạng thái đơn | §1 |
| Kiểm tra khóa, ghép bảng, xử lý thiếu, lọc, IQR | §2, `phase1_summary.json` |
| Transaction, one-hot, phân bố giỏ, kịch bản ALL/MULTI | §3, Hình `01_basket_distribution.png` |
| Benchmark Apriori vs FP-Growth theo minsup | §4, `benchmark_apriori_vs_fpgrowth.csv`, Hình `02_*` |
| Thí nghiệm mức sản phẩm | §4.1, `benchmark_product_level.csv`, Hình `06_*` |
| Lift ALL vs MULTI (lý do chọn MULTI) | §5.1, `pair_lift_all_vs_multi.csv` |
| Top 20 luật, support/confidence/lift | §5.2, `top20_rules.csv`, Hình `03_*`, `04_*`, `05_*` |
| Số liệu tổng hợp | §6, `phase2_summary.json` |

Mỗi hình và bảng trong Word cần có số thứ tự, tên, được nhắc tới trong phần phân tích, và ghi nguồn
(ví dụ: *Nguồn: kết quả chạy notebook, §4*). Không dùng ảnh chụp code thay cho bảng kết quả.

## 4. Gợi ý chia nội dung video (≤ 12 phút, cả 3 người cùng nói)

| Phút | Người | Nội dung |
|---|---|---|
| 0–3 | Thành viên A | Bài toán, dữ liệu, các quyết định tiền xử lý quan trọng |
| 3–7 | Thành viên B | Apriori vs FP-Growth, tham số, kết quả benchmark, vì sao chọn MULTI |
| 7–11 | Thành viên C | Giải thích ít nhất 1 luật tiêu biểu, insight; **demo chạy notebook hoặc app** |
| 11–12 | Cả nhóm | Kết luận, hạn chế |

Link video phải để chế độ công khai hoặc "ai có link đều xem được".
