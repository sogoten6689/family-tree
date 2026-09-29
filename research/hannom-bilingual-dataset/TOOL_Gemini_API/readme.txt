=====================================================
          ToolGeminiAPI Documentation
=====================================================

Clone cua TOOL_ChatGPT_API, doi dich sang Gemini web (gemini.google.com/app).
Public API giu nguyen y het ban ChatGPT nen 2 tool thay the nhau duoc:

    tool_api = ToolGeminiAPI()          # thay cho ToolChatGPTAPI()
    resp     = tool_api.send_request("...")
    ok       = tool_api.upload_file("/duong/dan/file.txt")
    tool_api.reset() / tool_api.quit() / tool_api.get_user_dir()

Support OS: macOS / Windows (da chay thu tren macOS 24.6, Chrome 152)

Python version:
-----------------------------------
Da chay voi Python 3.10.0

Installation:
-----------------------------------
    pip install -r requirements.txt

Configuration Explanation (tool_gemini_api.ini):
-----------------------------------

[options]
user-data-dir    = [User Data Folder Path] (mac dinh /tmp/gemini_api_chrome)
profile-directory= [Profile Folder] (mac dinh Default)
manual_login     = True/False (dang nhap tay lan dau)
headless_mode    = True/False (chay an)
log_level        = none/info/debug/error (debug se in ra selector nao match)

[driver]
driver_path      = [Chrome driver path] (de trong = tu tai driver khop Chrome)
cookies_path     = [Cookies file path] (vd cookies.pkl)
binary_path      = [Chrome binary path] (de trong = mac dinh)

[site]
url              = https://gemini.google.com/app

[context]
wait_time        = 20  (thoi gian cho 1 element, giay)
timeout          = 120 (thoi gian toi da cho 1 cau tra loi, giay)
cleanup_context  = True/False (ket thuc thi mo chat moi de xoa ngu canh)
context_content  = [context string] — dung "@" de ngat dong

Huong dan su dung:
-----------------------------------
1. Lan dau set manual_login = True va headless_mode = False.
2. Dang nhap Google trong cua so Chrome vua mo, xong quay lai terminal nhan Enter.
   Cookies se duoc luu ra cookies.pkl.
3. Tu lan sau co the set manual_login = False (tro cookies_path den file da tao).

Khac biet so voi ban ChatGPT:
-----------------------------------
1. Khong co tham so use_chatgpt4o. Gemini chon model bang nut "Open mode picker"
   tren UI; tool khong tu doi model.
2. delete_context() cua Gemini = mo cuoc tro chuyen moi (New chat) hoac reload
   /app, chu khong xoa hoi thoai nhu ChatGPT. Co alias new_chat() cho de doc.
3. Cho cau tra loi bang cach poll text cua cau tra loi cuoi den khi ngung thay doi
   (3 lan poll lien tiep giong nhau), thay vi dua vao rieng selector nut Stop —
   cach nay it phu thuoc DOM hon.
4. upload_file() phai bam nut "Upload & tools" truoc, vi Gemini khong render
   input[type=file] cho den khi menu upload duoc mo.
5. send_request() co fallback: neu khong tim duoc nut Send thi gui bang Enter.

Trang thai selector (quan trong):
-----------------------------------
Selector duoc nhom theo vai tro trong tool_gemini_api.py, moi nhom la 1 danh sach
ung vien thu lan luot. Trang thai xac minh tinh den 16.09.2026, do bang probe_dom.py
SAU KHI dang nhap (UI tieng Viet). Guest EN van giu lam fallback.

  [DA XAC MINH] PROMPT_BOX_SELECTORS
        'rich-textarea div.ql-editor[contenteditable="true"]' -> match 1 element.

  [DA XAC MINH] SEND_BUTTON_SELECTORS
        'button[aria-label="Gửi tin nhắn"]' (VI, sau login)
        'button[aria-label="Send message"]' (EN, guest)
        Chi xuat hien SAU khi o nhap co chu. send_request() go bang
        document.execCommand('insertText') vi Selenium send_keys khong do chu vao Quill.
        Luu y: 'button.send-button' KHONG match.

  [DA XAC MINH] UPLOAD_MENU_SELECTORS + FILE_INPUT_SELECTORS
        'button[aria-label="Nội dung tải lên và công cụ"]' (VI)
        'button[aria-label="Upload & tools"]' (EN)
        Sau JS click, input[type=file] xuat hien. Anh (.png) va file text deu
        send_keys duoc. Gemini hien thumbnail blob: chu khong luon hien ten file
        -> upload_file() cho preview (blob/data img) hoac chip ten file.

  [DA XAC MINH] NEW_CHAT_SELECTORS
        'a[aria-label="Cuộc trò chuyện mới"]' (VI, sau login)
        delete_context() van fallback click theo text / reload /app.

  [DA XAC MINH MOT PHAN] RESPONSE_SELECTORS
        Gui that "Reply with the single word PONG." nhan duoc 'PONG'.
        _wait_for_answer() dung CSS + fallback JS (model-response / message-content /
        assistant-messages-primary).

  [CHUA XAC MINH] STOP_BUTTON_SELECTORS
        Chi hien trong luc dang generate; chua bat duoc tren DOM on dinh.

probe_dom.py:
-----------------------------------
Script chan doan, chi doc DOM: mo Gemini, dem selector nao match, go thu 1 chuoi
vao o nhap de nut Send hien ra, liet ke cac nut dang hien, chup gemini_probe.png.
KHONG bam gui nen khong tao request nao len Gemini.

    python3 probe_dom.py
