# Trích xuất cây gia phả bằng LLM cục bộ (Qwen2.5-7B + LoRA/Unsloth)

Fine-tune `Qwen/Qwen2.5-7B-Instruct` (4-bit, LoRA) để đọc đoạn gia phả tiếng Việt và trả về JSON
gồm `persons` và `relations`.

Chạy mọi lệnh **từ gốc repo**. Dữ liệu nằm trong repo dữ liệu `data/` (không commit), script tự tìm
`data/` bằng cách đi ngược lên từ thư mục script; đặt `LLM_DATA_ROOT=/đường/dẫn/data` để chỉ định khác.

```
research/llm_extraction/
  _paths.py                 đường dẫn chung (data/, nơi lưu adapter)
  generate_synthetic.py     sinh bộ tổng hợp (seed cố định, kết quả giống hệt)
  build_vgp_dataset.py      dựng bộ thật từ corpus VGP (văn xuôi)
  validate_data.py          kiểm tra dữ liệu
  train.py                  train LoRA
  test.py                   thử adapter với một đoạn gia phả mới

data/01_interim/llm_synthetic/giapha_train.jsonl   300 mẫu tổng hợp (100 dễ / 100 trung bình / 100 khó)
data/01_interim/llm_synthetic/giapha_test.jsonl     50 mẫu tổng hợp, không trùng Input và tên người với train
data/03_derived/llm_sft/v3_persons/                 bộ VGP: train.jsonl, test.jsonl, stats.json, review_test.md
data/03_derived/models/giapha_lora_adapter/         adapter sau khi train
```

Trang soát nhãn nằm trong web chung: **Nghiên cứu → Trích xuất LLM → Soát nhãn LLM**
(`/nghien-cuu/soat-llm`), API ở `nlp_family_extractor/app/doi_chieu/llm_soat.py`.

## Bộ thật từ VGP (văn xuôi)

```bash
python research/llm_extraction/build_vgp_dataset.py      # ~40 giây
python research/llm_extraction/validate_data.py --real --quiet-warn \
  data/03_derived/llm_sft/v3_persons/train.jsonl data/03_derived/llm_sft/v3_persons/test.jsonl
```

- Input = `pha_ky.txt` cắt theo dòng thành đoạn ≤ 1.800 ký tự; email, URL, số điện thoại được thay bằng
  `[email]`, `[url]`, `[số điện thoại]`.
- Người = tên trong **sơ đồ gốc** (`pha_he.json`) hoặc trong nhãn silver Gemini, **xuất hiện nguyên văn** trong đoạn.
- Đời, vợ chồng, cha/mẹ – con lấy từ sơ đồ gốc khi tên khớp đúng một người. Quan hệ Gemini được giữ nếu
  không mâu thuẫn với sơ đồ. Năm sinh/mất chỉ lấy khi đứng ngay sau tên, ví dụ "X (1890 - 1960)" hoặc "X sinh năm 1890".
- Không có thông tin thì để `null` (đời, giới tính, năm), không suy đoán. Nguồn của từng nhãn ghi trong `meta`.
- Chia theo cây: test = 5 cây test cũ của v2 và 20% số cây có quan hệ; đoạn trùng chữ với test bị loại khỏi train.

## Trang soát nhãn (web chung)

```bash
cd nlp_family_extractor && uvicorn api:app --reload --port 8002     # backend
cd family-saga-io && npm run dev                                      # http://localhost:8080/nghien-cuu/soat-llm
```

- Cần đăng nhập **admin**. Chạy được cả khi `RESEARCH_MODE=1` (route nằm dưới `/api/doi-chieu/`).
- Máy chủ tự tìm mọi file `.jsonl` dạng Instruction/Input/Response trong `data/01_interim/llm_synthetic/`
  (nhóm "Tổng hợp") và `data/03_derived/llm_sft/` (nhóm "VGP", quét 2 cấp). Thêm, sinh lại hay sửa file
  thì trang tự cập nhật trong vòng 3 giây. Muốn chỉ định thư mục khác: `LLM_SOAT_DIRS=/a:/b`.
  Chạy bằng Docker thì phải mount thư mục dữ liệu vào container và đặt `LLM_SOAT_DIRS`, nếu không trang báo
  "Chưa có bộ dữ liệu".
- Trang chi tiết: tên trong đoạn văn được tô màu, cây vẽ theo đời, dòng sơ đồ gốc có nhắc các tên đó,
  cảnh báo giống `validate_data.py`, bảng sửa người và quan hệ.
- Kết quả soát lưu ở `<tên file>.reviews.json` cạnh file gốc (khoá theo nội dung đoạn, sinh lại file vẫn giữ).
  File gốc không bị sửa. Nút "Xuất bản đã soát" ghi `<tên file>.reviewed.jsonl` (nhãn đã sửa + trạng thái trong `meta`).
- Phím tắt: `Ctrl/⌘ S` lưu · `Ctrl/⌘ Enter` đã soát và sang mẫu sau · `Alt ←/→` mẫu trước/sau.

## Định dạng dữ liệu

Mỗi dòng là một JSON `{"text": "..."}`; `text` có 3 phần:

```
### Instruction:
Trích xuất thực thể và quan hệ gia phả từ văn bản sau. Trả về dạng JSON.

### Input:
<đoạn gia phả 3–6 câu>

### Response:
{"persons": [...], "relations": [...]}
```

- `persons`: `name` (họ tên đầy đủ, đúng như trong văn bản), `birth`, `death` (số năm hoặc `null` khi
  không rõ / còn sống), `generation` (cụ tổ = 1), `gender` (`male`/`female`). Dâu và rể cùng đời với
  người phối ngẫu.
- `relations`: chỉ 5 loại, đọc là "`from` là `type` của `to`":

  | type | ý nghĩa | ví dụ |
  |---|---|---|
  | `spouse` | chồng → vợ (ghi một chiều) | Ông A → Bà B |
  | `father` | cha → con | A → C |
  | `mother` | mẹ → con | B → C |
  | `son` / `daughter` | con → cha và con → mẹ | C → A, C → B |

  Mỗi cặp cha mẹ – con có đủ 4 quan hệ (`father`, `mother`, và 2 quan hệ ngược `son`/`daughter`).
  Ngoại lệ: **con riêng** của vợ kế chỉ có quan hệ với mẹ, không gán cha.

Mức độ:

| Mức | Số đời | Số người | Đặc điểm |
|---|---|---|---|
| Dễ | 2–3 | 4–6 | một vợ, văn phong hiện đại |
| Trung bình | 4–5 | 7–10 | có dâu, rể; một số mẫu có cháu ngoại (mang họ rể) |
| Khó | 3 | 5–9 | văn phong cổ "húy là, tự là, hiệu là", năm can chi; kết hợp 2–4 yếu tố: hai vợ (chính thất / kế thất), con nuôi, con riêng, thiếu năm sinh, cháu trùng tên cụ tổ |

Lưu ý: tự và hiệu (ví dụ "tự là Mạnh Đạt, hiệu là Tùng Am") **không** phải người, không có trong `persons`.
Khi hai người trùng tên ở hai đời, `relations` dùng tên nên có thể nhập nhằng; `generation` giúp phân biệt.

Bộ tổng hợp sinh bằng `generate_synthetic.py` theo mẫu câu (seed `20261127`),
không phải gia phả thật. Muốn đổi tỉ lệ, mẫu câu hay số mẫu thì sửa script rồi chạy
`python research/llm_extraction/generate_synthetic.py` (ghi đè `data/01_interim/llm_synthetic/`), sau đó chạy lại `validate_data.py`.
Mỗi mẫu bị giới hạn tối đa 3.600 ký tự (`MAX_CHARS`) để tránh vượt 2048 token.
Mô hình học tốt trên dữ liệu này chưa chứng minh được nó tổng quát hóa trên văn bản gia phả thật.

## 1. Kiểm tra dữ liệu (trên máy local)

```bash
python research/llm_extraction/validate_data.py      # mặc định: 2 file tổng hợp
```

Kiểm tra: JSON từng dòng, field `text`, đủ và đúng thứ tự Instruction/Input/Response, Response là JSON
đúng schema, type quan hệ thuộc 5 loại, tên trong `relations` có trong `persons`, giới tính khớp
(`father`/`son` là nam…), quy tắc "A cha của C và A chỉ có một vợ B → phải có B mẹ của C",
và Input không trùng giữa train/test. In ra số dòng bị lỗi; mã thoát 1 nếu có lỗi.

## 2. Train trên Vast.ai (RTX 4090, 24 GB)

1. Thuê máy: chọn 1× RTX 4090, ổ ≥ 50 GB, image có sẵn PyTorch + CUDA 12.x
   (ví dụ `pytorch/pytorch:2.4.0-cuda12.1-cudnn9-devel`). Lưu ý: máy tính tiền theo giờ.
2. Đưa thư mục lên máy (thay `PORT`, `IP` bằng thông tin trên trang instance):

   ```bash
   scp -P PORT -r research/llm_extraction root@IP:/workspace/
   scp -P PORT -r data/01_interim/llm_synthetic data/03_derived/llm_sft/v3_persons root@IP:/workspace/data_train/
   ```

3. Trên máy Vast.ai:

   ```bash
   cd /workspace
   pip install unsloth          # kéo theo transformers, trl, peft, bitsandbytes, datasets
   export LLM_DATA_ROOT=/workspace/data   # adapter ghi vào $LLM_DATA_ROOT/03_derived/models/
   python llm_extraction/validate_data.py data_train/llm_synthetic/*.jsonl
   python llm_extraction/train.py --data data_train/llm_synthetic/giapha_train.jsonl
   # trộn thêm bộ VGP: thêm --data data_train/v3_persons/train.jsonl
   ```

   Đầu lượt train, script in số token dài nhất; nếu có mẫu vượt 2048 token sẽ cảnh báo.
   Với 300 mẫu, batch hiệu dụng 2 × 4 = 8, 3 epoch ≈ 114 bước.
   Adapter được lưu ở `$LLM_DATA_ROOT/03_derived/models/giapha_lora_adapter/` (đổi bằng `--out`).

4. Tải adapter về **trước khi tắt máy** (máy không có volume sẽ mất dữ liệu khi destroy):

   ```bash
   scp -P PORT -r root@IP:/workspace/data/03_derived/models/giapha_lora_adapter data/03_derived/models/
   ```

## 3. Thử adapter

```bash
python research/llm_extraction/test.py
python research/llm_extraction/test.py --text "Cụ tổ đời thứ nhất là ông ... "
```

Script nạp model gốc 4-bit + adapter, sinh câu trả lời (greedy), in output thô và JSON đã parse.
Cần GPU; chạy ngay trên máy Vast.ai sau khi train là tiện nhất.

## Tham số train

| Tham số | Giá trị |
|---|---|
| Model gốc | `Qwen/Qwen2.5-7B-Instruct`, `load_in_4bit=True`, `max_seq_length=2048` |
| LoRA | `r=16`, `lora_alpha=32`, `lora_dropout=0`, target: q/k/v/o/gate/up/down_proj |
| Train | batch 2, grad accum 4, 3 epoch, lr 2e-4, `adamw_8bit`, warmup 5, linear |

Loss được tính trên toàn bộ chuỗi (cả phần Instruction và Input), mỗi mẫu được nối thêm EOS.
