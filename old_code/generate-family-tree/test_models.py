import os
from dotenv import load_dotenv
from google import genai

def main():
     # Load biến môi trường từ .env
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Chưa thiết lập GOOGLE_API_KEY")

    client = genai.Client(api_key=api_key)

    # Liệt kê model khả dụng
    for m in client.models.list():
        print(m.name)

if __name__ == "__main__":
    main()