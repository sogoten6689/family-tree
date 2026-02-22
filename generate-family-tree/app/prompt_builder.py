import json
from app.models import Person


def build_prompt(person: Person) -> str:
    data = json.dumps(person.__dict__, ensure_ascii=False, indent=2)

    return f"""
Bạn là hệ thống biên soạn gia phả hiện đại.

YÊU CẦU:
- Chỉ sử dụng dữ liệu được cung cấp.
- Không suy đoán.
- Không thêm thông tin ngoài dữ liệu.
- Văn phong trang trọng.
- Độ dài khoảng 150-200 chữ.

DỮ LIỆU:
{data}

Viết đoạn gia phả cho nhân vật trên.
"""