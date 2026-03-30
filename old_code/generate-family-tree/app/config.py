import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

MODEL_NAME = "models/gemini-2.5-flash"

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY chưa được thiết lập.")