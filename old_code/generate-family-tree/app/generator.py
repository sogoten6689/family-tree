from app.prompt_builder import build_prompt
from app.gemini_client import GeminiClient
from app.models import Person


class FamilyTreeGenerator:
    def __init__(self):
        self.ai = GeminiClient()

    def generate_biography(self, person: Person) -> str:
        prompt = build_prompt(person)
        return self.ai.generate(prompt)