# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| Họ và tên | Nguyễn Xuân Đức |
| MSSV | 2A202601112 |
| Khóa/Lớp | K4 AI Thực Chiến |
| Vai trò chính | Lead Developer & Multi-Agent System Architect |
| Ngày hoàn thành | 2026-08-05 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Data Engine & Join** | `src/data_engine.py` | 9 CSV files trong `data/` | Pre-indexed order context dictionary | Hoàn thành |
| **Policy Engine** | `src/policy_engine.py` | Order context dictionary | Output schema JSON object theo `EC_POLICY_V2` | Hoàn thành |
| **Multi-Agent Framework** | `src/agents.py` | Case JSON & Order Context | Traces A2A & Validated Output | Hoàn thành |
| **Orchestration & Validation** | `run_pipeline.py`, `src/validate_output.py` | `input/*.json` | 50 JSON outputs trong `output/`, `trace.jsonl` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| Thiết kế Schema & Evidence Validator | Verifier Agent | Đảm bảo 100% 50 file JSON pass schema validation |
| Viết tài liệu Kiến trúc | `architecture.md` | Hoàn thành sơ đồ Mermaid & quy tắc handoff |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Xử lý dữ liệu Olist & Tính toán chênh lệch | `src/data_engine.py` | Indexed context | Run `python run_pipeline.py` |
| Triển khai quy tắc `EC_POLICY_V2` | `src/policy_engine.py` | Output schema generator | Run `python src/validate_output.py` |
| Xây dựng hệ thống 7 Agent A2A | `src/agents.py` | Multi-agent execution flow | Kiểm tra `trace.jsonl` |
| Đóng gói 50 case JSON & Trace | `output/EC_*.json`, `trace.jsonl` | 50 JSON files | Checksum & Schema validator |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng hệ thống Multi-Agent có khả năng điều tra chính xác 50 khiếu nại thương mại điện tử, phân định đúng Primary Issue, Secondary Issues, trách nhiệm bồi thường (platform, seller, logistics), tính toán số tiền hoàn tiền và hành động xử lý theo quy tắc `EC_POLICY_V2`.

### Cách triển khai
- **Deterministic Data Processing**: Sử dụng Python (Pandas/Dictionaries) để tính toán chính xác 100% các giá trị thời gian (`delivery_variance_hours`, `handoff_variance_hours`) và tài chính (`expected_total_brl`, `difference_brl`, `reconciled`) để loại bỏ hoàn toàn hiện tượng suy diễn sai (hallucination) của LLM.
- **A2A Multi-Agent Architecture**: Phân chia trách nhiệm thành 7 Agent chuyên biệt (`CoordinatorAgent`, `CustomerAgent`, `OrderProductAgent`, `DeliveryAgent`, `PaymentAgent`, `PolicyAgent`, `VerifierAgent`), ghi lại trace trao đổi thông tin giữa các agent vào `trace.jsonl`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| Input | 50 file `input/EC_*.json` chứa `claimed_order_id` và yêu cầu khiếu nại |
| Output | 50 file `output/EC_*.json` chuẩn định dạng JSON Schema |
| Module phụ thuộc | Python 3.11, Pandas |
| Module sử dụng output | Hệ thống chấm điểm cuộc thi |
| Điều kiện lỗi cần xử lý | Đơn hàng không có item row (`expected_total_brl`, `difference_brl`, `reconciled` = `null`) |

### Cách xác minh

```bash
python run_pipeline.py
python src/validate_output.py
```

- **Kết quả mong đợi:** 50/50 file JSON được tạo thành công, 0 lỗi schema.
- **Kết quả thực tế:** 50/50 file JSON pass tất cả các ràng buộc kiểm tra.
- **Artifact/log:** `output/`, `trace.jsonl`, `logging/trace.jsonl`, `metadata.json`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp xử lý logic điều tra khiếu nại giữa (A) Đưa toàn bộ CSV và prompt cho 1 LLM duy nhất xử lý, hay (B) Kết hợp Deterministic Data Engine + Multi-Agent Architecture.
- **Các phương án đã cân nhắc:**
  1. *Phương án A*: Dùng LLM prompt duy nhất. Nhược điểm: Dễ bị hallucination ở các phép tính thời gian/tiền tệ, chi phí token cao và không tuân thủ strict array bounds.
  2. *Phương án B*: Kết hợp Deterministic Data & Policy Engine với Hệ thống 7 Agent A2A.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Đảm bảo độ chính xác tuyệt đối (100% Correctness) đối với các chỉ số tiền và giờ, tuân thủ nghiêm ngặt giới hạn mảng của Schema (Array Limits) và có trace rõ ràng từng bước cho từng agent.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `KeyError: 'is_late'` khi lọc danh sách đơn hàng trong script khởi tạo input.
- **Lệnh hoặc bước tái hiện:** `python src/generate_inputs.py`.
- **Nguyên nhân gốc:** Cột `is_late` chỉ được thêm vào dataframe con `delivered` thay vì dataframe tổng `df_orders`.
- **Cách xử lý:** Gán cột `is_late` và `seller_late` trực tiếp vào `df_orders` trước khi lọc điều kiện.
- **Cách xác minh sau khi sửa:** Chạy lại `python src/generate_inputs.py`, tạo đủ 50 file input thành công.

---

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu từ khiếu nại khách hàng (`claimed_order_id`) được `CoordinatorAgent` nhận vào, sau đó `CustomerAgent` tìm kiếm lịch sử khách hàng dựa trên `customer_unique_id`.
2. `OrderProductAgent`, `DeliveryAgent`, `PaymentAgent` lần lượt bóc tách thông tin đơn hàng, tính toán sai lệch giờ giao hàng, độ trễ seller bàn giao và đối soát dòng tiền.
3. `PolicyAgent` áp dụng thứ tự ưu tiên của `EC_POLICY_V2` để xác định Primary Issue, Secondary Issues, bồi thường và hành động xử lý.
4. `VerifierAgent` kiểm tra toàn bộ dữ liệu theo JSON Schema, đảm bảo array bounds, null safety và định dạng Evidence IDs trước khi xuất file ra `output/`.

---

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Xuân Đức  
**Ngày xác nhận:** 2026-08-05
