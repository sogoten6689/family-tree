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
docker compose up --build -d
```

Kiểm tra backend:

```bash
curl http://localhost:8000/health
```

Dừng toàn bộ service:

```bash
docker compose down
```

Xóa luôn dữ liệu MySQL volume:

```bash
docker compose down -v
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

## Lịch sử request

Backend có lưu lịch sử request trong memory của tiến trình API.

- `GET /api/family-tree/history?limit=20`
	- Trả về danh sách request gần nhất (mặc định 20, tối đa 100)
- `DELETE /api/family-tree/history`
	- Xóa toàn bộ lịch sử request đang lưu trong memory

Lưu ý: history memory sẽ mất khi restart server.

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


