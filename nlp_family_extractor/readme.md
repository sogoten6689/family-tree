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

