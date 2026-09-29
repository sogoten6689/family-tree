import os
from tool_gemini_api import ToolGeminiAPI

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_FILE = os.path.join(HERE, "test.txt")

tool_api = ToolGeminiAPI()
uploaded = tool_api.upload_file(TEST_FILE)
print("upload_file:", uploaded)
resp = tool_api.send_request("test")
print(resp)
