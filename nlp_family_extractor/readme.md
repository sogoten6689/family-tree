Hướng phát triển:
1Similarity-Rule-Based-Detection ->Statistical learning

Rule-base: Một rule như vậy gồm pattern + action. Pattern thường là regular expression định nghĩa trên tập feature của token. Khi pattern này match thì action sẽ được kích hoạt

Chốt được input:
Chốt được output:

## Backend API cho Frontend

### Cài dependencies

```bash
pip install -r requirements.txt
```

### Chạy server

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

## Chạy bằng Docker Compose (backend + MySQL)

Từ thư mục gốc dự án `family-tree`:

```bash
./infra/scripts/compose.sh up --build -d
```

Kiểm tra backend:

```bash
curl http://localhost:8000/health
```

Dừng toàn bộ service:

```bash
./infra/scripts/compose.sh down
```

Xóa luôn dữ liệu MySQL volume:

```bash
./infra/scripts/compose.sh down -v
```

### Endpoint phân tích

- `POST /api/family-tree/analyze`

Request body:

```json
{
	"text": "Ông Nguyễn Văn A sinh năm 1940, là cha của Nguyễn Văn B...",
	"source": "document-reader",
	"metadata": {
		"fileName": "gia-pha.docx",
		"language": "vi"
	}
}
```

Response chính:

- `extraction`: danh sách `people` + `relationships`
- `tree_architecture`: cấu trúc cây theo `roots`, `children_map`, `nodes`
- `tree`: cây lồng nhau để frontend render nhanh

Ngoài ra response `analyze` có thêm:

- `request_id`: mã request duy nhất
- `created_at`: thời điểm xử lý (UTC ISO)

## Đối chiếu dóng hàng của sinh viên

Trang web `/nghien-cuu/doi-chieu` (không cần đăng nhập) đọc API chỉ-đọc `/api/public/doi-chieu`.
Dữ liệu không nằm trong git: đặt ở `data/doi_chieu/` (thư mục `data/` của backend, đã mount vào container)
hoặc trỏ biến môi trường `DOI_CHIEU_DIR`. Chưa có thư mục thì trang báo "Chưa có bài nộp nào".

```
doi_chieu/danh_muc.json                        {"<ma-cuon>": {"ten": "Tên cuốn", "link": "https://drive…"}}
doi_chieu/<sinh-vien>/meta.json                {"ten": "Họ tên"}   (tuỳ chọn)
doi_chieu/<sinh-vien>/<ma-cuon>/*_parallel.tsv bài nộp: <Hán>\t<Việt>
doi_chieu/<sinh-vien>/<ma-cuon>/cap_cau.csv    bản máy, chép từ gói lab soat/<ma-cuon>/
doi_chieu/<sinh-vien>/<ma-cuon>/anh/           ảnh trang (tuỳ chọn; cuốn chưa có bản máy vẫn xem được ảnh)
doi_chieu/<sinh-vien>/<ma-cuon>/soat_nhap.json nháp của thẻ Soát (admin), không tính vào số liệu
doi_chieu/<sinh-vien>/<ma-cuon>/lich_su/       các bản TSV cũ, giữ lại mỗi lần nộp từ thẻ Soát
```

Mọi thứ trong thư mục này ai có link cũng xem được, trừ nháp của thẻ Soát. Nhãn chấm mẫu chỉ lưu trong trình duyệt người chấm.

Thẻ **Soát** chỉ hiện với admin đã đăng nhập, gọi API `/api/doi-chieu/<sinh-vien>/<ma-cuon>/soat` (đọc và lưu nháp) và `.../soat/nop` (nộp).
Khi nộp, chỉ dòng thuộc trang đã xác nhận mới vào `<ma-cuon>_parallel.tsv`. Backend cần quyền ghi vào thư mục này.

## Lịch sử request

Backend hỗ trợ 2 tầng lưu lịch sử request:

- MySQL (ưu tiên, bền vững qua restart container)
- Memory fallback (khi chưa cấu hình được MySQL)

Khi chạy bằng `docker compose`, API tự động dùng MySQL theo biến môi trường `MYSQL_*`.

- `GET /api/family-tree/history?limit=20`
	- Trả về danh sách request gần nhất (mặc định 20, tối đa 100)
- `DELETE /api/family-tree/history`
	- Xóa toàn bộ lịch sử request

`GET /health` trả thêm:

- `history_storage`: `mysql` hoặc `memory`

Nếu đang ở `memory`, dữ liệu sẽ mất khi restart API.

## Cách viết tài liệu để sinh quan hệ tốt

API rule-based hoạt động tốt nhất khi văn bản có các mẫu câu rõ ràng:

- Vợ/chồng:
	- `Nguyễn Văn A kết hôn với Trần Thị B.`
	- `Nguyễn Văn A cưới Trần Thị B.`
- Cha/mẹ - con:
	- `Nguyễn Văn A và Trần Thị B có con là Nguyễn Văn C.`
	- `Nguyễn Văn C là con của Nguyễn Văn A và Trần Thị B.`
	- `Nguyễn Văn C, cha là Nguyễn Văn A, mẹ là Trần Thị B.`
- Anh/chị/em:
	- `Nguyễn Văn C và Nguyễn Thị D là anh em trong gia đình.`

Bạn có thể dùng file mẫu:

- `data/sample_relationship_document.txt`


