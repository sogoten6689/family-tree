from google import genai
from app.config import GOOGLE_API_KEY, MODEL_NAME


class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=GOOGLE_API_KEY)

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        return response.text