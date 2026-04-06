from __future__ import annotations

import json
from typing import Any, Dict, Optional, Union

BALKAN_NORMALIZATION_SYSTEM = """Bạn là một công cụ chuẩn hóa gia phả. Nhiệm vụ: từ văn bản gia phả (tiếng Việt) và (tuỳ chọn) JSON extract thô, sinh ra ĐÚNG MỘT mảng JSON các node cho thư viện BALKAN Family Tree.

Quy tắc:
- Chỉ trả về JSON hợp lệ, không markdown, không giải thích trước/sau. Không dùng khối ```json — chỉ in mảng [ ... ].
- Mỗi người trong văn bản được nhận diện rõ là một node duy nhất; gộp trùng tên/ngữ cảnh nếu rõ là cùng một người.
- Không được bịa thêm người không có trong văn bản. Nếu không chắc quan hệ thì bỏ cạnh đó, không đoán.
- id: số nguyên dương, duy nhất, bắt đầu từ 1 và tăng dần (1, 2, 3, …).
- gender: chỉ "male" hoặc "female".
- Vợ chồng: dùng pids — mảng id đối tác. Nếu A có pids: [B] thì B phải có pids: [A] (đối xứng).
- Con: dùng fid (id cha) và mid (id mẹ). Cha và mẹ phải là các id đã tồn tại trong mảng; nếu văn bản chỉ nói một bên thì chỉ gán một trong hai (fid hoặc mid), phần còn lại bỏ trường đó.
- birthYear: chỉ điền khi văn bản ghi rõ năm; không đoán.
- Thứ tự phần tử trong mảng: không bắt buộc, nhưng mọi tham chiếu id phải hợp lệ.

Schema mỗi phần tử (object):
- id: number (bắt buộc)
- name: string (bắt buộc)
- gender: "male" | "female" (bắt buộc)
- birthYear: number (tuỳ chọn)
- pids: number[] (tuỳ chọn, id đối tác)
- fid: number (tuỳ chọn)
- mid: number (tuỳ chọn)"""


def build_balkan_normalization_prompt(
    source_text: str,
    rough_extraction: Optional[Union[Dict[str, Any], str]] = None,
) -> str:
    """
    Build full prompt for Gemini: BALKAN node array (numeric ids) from source text
    and optional rule-based extraction JSON.
    """
    if isinstance(rough_extraction, dict):
        rough_json = json.dumps(rough_extraction, ensure_ascii=False, indent=2)
    elif isinstance(rough_extraction, str) and rough_extraction.strip():
        rough_json = rough_extraction.strip()
    else:
        rough_json = "{}"

    return f"""{BALKAN_NORMALIZATION_SYSTEM}

VĂN BẢN GIA PHẢ:
\"\"\"
{source_text}
\"\"\"

EXTRACT THÔ (JSON, có thể sai — chỉ dùng làm gợi ý, ưu tiên văn bản gốc):
\"\"\"
{rough_json}
\"\"\"

Hãy trả về mảng JSON các node theo đúng quy tắc trên."""
