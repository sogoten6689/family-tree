from google import genai
from app.config import GOOGLE_API_KEY, MODEL_NAME
import json


class NaturalLanguageExtractor:
    def __init__(self):
        self.client = genai.Client(api_key=GOOGLE_API_KEY)

    def extract_person(self, text: str) -> dict:
        prompt = f"""
Bạn là hệ thống trích xuất dữ liệu gia phả.

Chuyển đoạn văn sau thành JSON với cấu trúc:

{{
  "full_name": "",
  "gender": "",
  "birth_year": 0,
  "death_year": 0,
  "birth_place": "",
  "occupation": "",
  "father": "",
  "mother": "",
  "spouse": [],
  "children": []
}}

Chỉ trả về JSON. Không giải thích.

Văn bản:
{text}
"""

        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        raw = response.text.strip()

        # loại bỏ ```json nếu có
        raw = raw.replace("```json", "").replace("```", "").strip()

        return json.loads(raw)