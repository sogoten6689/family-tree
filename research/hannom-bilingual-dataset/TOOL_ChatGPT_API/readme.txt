=====================================================
          ToolChatGPTAPI Documentation
=====================================================

Support OS: Windows
-----------------------------------

Python version:
-----------------------------------
Python 3.9.16 (main, Dec 21 2022, 04:16:27) [MSC v.1929 64 bit (AMD64)]

Installation:
-----------------------------------
Chạy lệnh sau để cài đặt các thư viện cần thiết:
    pip install -r requirements.txt

Configuration Explanation:
-----------------------------------

[options]
user-data-dir    = [User Data Folder Path]
profile-directory= [Profile Folder] (mặc định để Default)
manual_login     = True/False (Login manual)
headless_mode    = True/False (chạy in background)

[driver]
driver_path      = [Chrome driver path]
cookies_path     = [Cookies file path] (e.g. cookies.pkl)

[site]
url              = [Web url] (e.g. https://chatgpt.com/)
use_chatgpt4o    = True/False (dùng chat GPT4o ?)

[context]
wait_time        = 20 (WAIT TIME IN SECOND)
timeout          = 30 (TIMEOUT theo đơn vị giây)
context_content  = [context string]

Hướng dẫn sử dụng:
-----------------------------------
1. Lần đầu tiên nên set manual_login=True và headless_mode=False.
2. Đăng nhập để tạo file cookie, đăng nhập xong thì nhấn enter để chạy tiếp.
3. Từ lần sau có thể set manual_login=False và headless_mode=True (nhớ set đường dẫn đến file cookies tạo ra trong lần đầu - thường trong Working Directory).

Ví dụ sử dụng class ToolChatGPTAPI:
-----------------------------------
from tool_chatgpt_api import ToolChatGPTAPI

tool_api = ToolChatGPTAPI()
resp = tool_api.send_request("test")
print(resp)

Lưu ý:
-----------------------------------
ToolChatGPTAPI có 1 input param là config_path trỏ đến file config.ini, nếu không provide sẽ dùng file mặc định là tool_chatgpt_api.ini cùng cấp.
