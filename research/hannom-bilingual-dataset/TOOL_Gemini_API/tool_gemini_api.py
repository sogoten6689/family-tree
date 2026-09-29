# *******************************************************************************
#
# File: tool_gemini_api.py
#
# Description:
#   Provides a Gemini API-like class for users to interact with as if it were a real API.
#   This implementation uses Selenium to run a browser in the background, handling
#   interactions with the Gemini web interface and maintaining context for conversations.
#
#   Clone of TOOL_ChatGPT_API/tool_chatgpt_api.py (Cuong Nguyen / July 2024), retargeted
#   at gemini.google.com. Public API is kept identical (send_request, upload_file, reset,
#   quit, get_user_dir) so the two tools are drop-in interchangeable.
#
# History:
#
# 16.09.2026 / V 0.2
# - Xac minh selector sau login (UI tieng Viet): Gửi tin nhắn, Nội dung tải lên
#   và công cụ, Cuộc trò chuyện mới. send_request go Quill bang insertText.
# 16.09.2026 / V 0.1
# - Clone from tool_chatgpt_api.py, retarget to Gemini
#
# *******************************************************************************
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
import configparser
import undetected_chromedriver as uc
import os
import re
import json
import psutil
import atexit
import subprocess


class LOG_LEVEL:
    INFO = 1
    DEBUG = 2
    ERROR = 3


# -----------------------------------------------------------------------------
# Selector ung vien cho Gemini web UI.
#
# Gemini la Angular app (Material), DOM doi thuong xuyen va khong co data-testid
# on dinh nhu ChatGPT. Vi vay moi vai tro giu 1 DANH SACH ung vien, thu lan luot
# tu cu the den tong quat. Cai nao match se duoc log lai o log_level = debug.
#
# Chay probe_dom.py de do lai DOM that va cap nhat danh sach nay.
# Trang thai xac minh cua tung nhom: xem readme.txt muc "Trang thai selector".
# -----------------------------------------------------------------------------

# DA XAC MINH 16.09.2026 (probe_dom.py): ung vien dau tien match dung 1 element.
PROMPT_BOX_SELECTORS = [
    'rich-textarea div.ql-editor[contenteditable="true"]',
    'div.ql-editor[contenteditable="true"]',
    'div[contenteditable="true"][role="textbox"]',
    'rich-textarea div[contenteditable="true"]',
    'div[contenteditable="true"]',
]

# DA XAC MINH 16.09.2026 (probe sau login, UI tieng Viet): nut Send CHI xuat hien
# sau khi o nhap co chu. Guest EN = "Send message"; login VI = "Gửi tin nhắn".
SEND_BUTTON_SELECTORS = [
    'button[aria-label="Gửi tin nhắn"]',
    'button[aria-label="Send message"]',
    'button[aria-label*="Gửi tin nhắn"]',
    'button[aria-label*="Send message"]',
    'button[aria-label="Submit"]',
    'button.send-button',
]

# Bo sung 16.09.2026: assistant-messages-primary co that tren DOM da login.
# model-response / message-content van de thu vi chi xuat hien sau khi co cau tra loi.
RESPONSE_SELECTORS = [
    'model-response message-content',
    'message-content.model-response-text',
    '.model-response-text',
    'model-response',
    'message-content',
    'chat-window-content message-content',
]

# CHUA XAC MINH: chi hien trong luc Gemini dang tra loi.
STOP_BUTTON_SELECTORS = [
    'button[aria-label="Stop response"]',
    'button[aria-label="Stop generating"]',
    'button[aria-label*="Dừng"]',
    'button[aria-label*="Stop"]',
    'button.stop-button',
]

# DA XAC MINH 16.09.2026: sidebar hien "Cuộc trò chuyện mới" (khong phai button
# aria-label="New chat"). CSS thu truoc, delete_context() fallback click theo text.
NEW_CHAT_SELECTORS = [
    'button[aria-label="Cuộc trò chuyện mới"]',
    'a[aria-label="Cuộc trò chuyện mới"]',
    'button[aria-label="New chat"]',
    'a[aria-label="New chat"]',
    '[aria-label="Cuộc trò chuyện mới"]',
    '[aria-label="New chat"]',
    'expanded-button[data-test-id="new-chat-button"]',
    'side-nav-action-button[data-test-id="new-chat-button"]',
]
NEW_CHAT_LABELS = ["Cuộc trò chuyện mới", "New chat"]

# DA XAC MINH 16.09.2026 (probe sau login): guest EN = "Upload & tools";
# login VI = "Nội dung tải lên và công cụ". Khong co input[type=file] cho den
# khi bam nut nay (va co the phai chon muc "Tải tệp lên" trong menu).
UPLOAD_MENU_SELECTORS = [
    'button[aria-label="Nội dung tải lên và công cụ"]',
    'button[aria-label="Upload & tools"]',
    'button[aria-label*="tải lên và công cụ"]',
    'button[aria-label*="Upload & tools"]',
    'button[aria-label="Open upload menu"]',
    'button[aria-label="Add files"]',
]

UPLOAD_FILE_ITEM_SELECTORS = [
    '[aria-label="Tải tệp lên"]',
    '[aria-label="Upload files"]',
    '[aria-label="Upload file"]',
    '[aria-label*="Tải tệp"]',
    '[aria-label*="Upload file"]',
    'button[data-test-id="local-images-files-uploader"]',
    'toolbox-drawer button[aria-label*="Tệp"]',
    'toolbox-drawer button[aria-label*="File"]',
]
UPLOAD_FILE_ITEM_LABELS = [
    "Tải tệp lên",
    "Upload files",
    "Upload file",
    "Tệp và hình ảnh",
    "Files and images",
    "Máy tính",
    "Computer",
    "Tệp",
    "Files",
]

FILE_INPUT_SELECTORS = [
    'input[type="file"]',
]

# Dau hieu CHUA dang nhap: Gemini redirect sang accounts.google.com hoac hien nut Sign in.
LOGGED_OUT_SELECTORS = [
    'a[href*="accounts.google.com/ServiceLogin"]',
    'a[href*="accounts.google.com/signin"]',
]
LOGGED_OUT_URL_MARKERS = ['accounts.google.com', '/signin', 'ServiceLogin']


class ToolGeminiAPI:
    """
A Gemini API-like class for simulating API interactions with Gemini.

This class uses Selenium to control a web browser, allowing users to interact with the Gemini
web interface programmatically. It maintains the context of conversations and performs actions
on behalf of the user, providing a seamless API-like experience.

Methods of this class enable users to send messages, receive responses, and manage conversation
context, mimicking the behavior of a real API while leveraging the Gemini web interface
through Selenium.
    """

    SCRIPT_DIR: str = os.path.dirname(os.path.abspath(__file__))
    INI_FILE_PATH: str = os.path.join(SCRIPT_DIR, 'tool_gemini_api.ini')
    _instances = []
    LOG_LEVEL_MAP = {
        'none': 0,
        'info': 1,
        'debug': 2,
        'error': 3
    }

    def __init__(self, config_path=""):
        """
Constructor for the ToolGeminiAPI class.

**Arguments:**

* ``config_path``

  / *Condition*: optional / *Type*: str / *Default*: "" /

  The path to the configuration file.

**Returns:**

(*no returns*)
        """
        # Read configuration from tool_gemini_api.ini
        config = configparser.ConfigParser()
        if not config_path:
            config_path = ToolGeminiAPI.INI_FILE_PATH
        with open(config_path, 'r', encoding='utf-8') as configfile:
            config.read_file(configfile)

        # Extract configuration values
        self.user_data_dir = config.get('options', 'user-data-dir')
        self.profile_directory = config.get('options', 'profile-directory')
        self.log_level = ToolGeminiAPI.LOG_LEVEL_MAP[config.get('options', 'log_level')]
        self.driver_path: str = config.get('driver', 'driver_path')
        self.url: str = config.get('site', 'url')
        self.wait_time: int = config.getint('context', 'wait_time')
        self.timeout: int = config.getint('context', 'timeout')
        self.cleanup_context = config.getboolean('context', 'cleanup_context')
        self.require_manual_login = config.getboolean('options', 'manual_login')
        self.context_content = config.get('context', 'context_content')
        self.headless_mode = config.getboolean('options', 'headless_mode', fallback=False)
        self.cookies_path = config.get('driver', 'cookies_path', fallback="")
        self.binary_path = config.get('driver', 'binary_path', fallback="")

        self.initialize()
        ToolGeminiAPI._instances.append(self)

    def log_infor(self, log_msg, level=LOG_LEVEL.INFO):
        if level <= self.log_level:
            print(log_msg)

    @classmethod
    def cleanup_all(cls):
        print("Cleaning up all...")
        for instance in cls._instances:
            instance.quit()

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _windows_exe_major_version(path):
        """Doc major version tu PE resource. chrome.exe --version tren Windows
        thuong mo cua so moi thay vi in stdout, nen khong dung duoc."""
        import ctypes
        from ctypes import wintypes

        size = ctypes.windll.version.GetFileVersionInfoSizeW(path, None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        if not ctypes.windll.version.GetFileVersionInfoW(path, 0, size, buf):
            return None

        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD),
                ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD),
                ("dwFileVersionLS", wintypes.DWORD),
            ]

        block = ctypes.c_void_p()
        length = wintypes.UINT()
        if not ctypes.windll.version.VerQueryValueW(
            buf, "\\", ctypes.byref(block), ctypes.byref(length)
        ):
            return None
        info = ctypes.cast(block, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
        if info.dwSignature != 0xFEEF04BD:
            return None
        return info.dwFileVersionMS >> 16

    def _chrome_major_version(self):
        """Doc major version cua Chrome that de undetected_chromedriver tai driver khop."""
        candidates = []
        if self.binary_path:
            candidates.append(self.binary_path)
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidates.extend([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(local_app, r"Google\Chrome\Application\chrome.exe") if local_app else "",
        ])
        for binary in candidates:
            if not binary or not os.path.exists(binary):
                continue
            if os.name == "nt":
                try:
                    major = self._windows_exe_major_version(binary)
                    if major:
                        return major
                except Exception:
                    pass
            try:
                out = subprocess.check_output(
                    [binary, "--version"], stderr=subprocess.STDOUT, text=True, timeout=5
                )
                match = re.search(r"(\d+)\.", out)
                if match:
                    return int(match.group(1))
            except Exception:
                pass
        return None

    def _find_first(self, selectors, timeout=None, visible=False):
        """Thu lan luot cac selector, tra ve element dau tien tim duoc (kem selector da match).

        Tra ve (element, selector) hoac (None, None) neu khong co cai nao match.
        """
        timeout = self.wait_time if timeout is None else timeout
        condition = EC.visibility_of_element_located if visible else EC.presence_of_element_located
        deadline = time.time() + timeout
        while True:
            for selector in selectors:
                try:
                    element = WebDriverWait(self.driver, 0.5).until(
                        condition((By.CSS_SELECTOR, selector))
                    )
                    self.log_infor(f"Matched selector: {selector}", LOG_LEVEL.DEBUG)
                    return element, selector
                except TimeoutException:
                    continue
            if time.time() >= deadline:
                self.log_infor(f"Khong selector nao match trong {selectors}", LOG_LEVEL.DEBUG)
                return None, None

    def _find_all_first(self, selectors):
        """Tra ve list element cua selector dau tien co ket qua."""
        for selector in selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return elements, selector
        return [], None

    def _click_by_visible_text(self, texts, contains=False):
        """Click phan tu dang hien co innerText khop mot trong cac chuoi (EN/VI)."""
        try:
            matched = self.driver.execute_script(
                """
                const texts = arguments[0];
                const contains = arguments[1];
                const els = [...document.querySelectorAll(
                    'a, button, [role="button"], gem-nav-list-item, span'
                )];
                for (const t of texts) {
                    const el = els.find(e => {
                        const label = (e.innerText || '').replace(/\\s+/g, ' ').trim();
                        if (!label || e.offsetParent === null) return false;
                        return contains ? label.includes(t) : label === t;
                    });
                    if (el) {
                        (el.closest('a, button, [role="button"], gem-nav-list-item') || el).click();
                        return t;
                    }
                }
                return null;
                """,
                list(texts),
                contains,
            )
            if matched:
                self.log_infor(f"Clicked by visible text: {matched}", LOG_LEVEL.DEBUG)
                return True
        except Exception as e:
            self.log_infor(f"Click by text that bai: {e}", LOG_LEVEL.DEBUG)
        return False

    def _js_click(self, element):
        self.driver.execute_script("arguments[0].click();", element)

    def _fill_prompt(self, request: str) -> bool:
        """Go prompt vao Quill. send_keys thuong khong do chu; dung insertText."""
        self.prompt_text_area, _ = self._find_first(PROMPT_BOX_SELECTORS)
        if self.prompt_text_area is None:
            self.log_infor("Khong tim thay o nhap prompt.")
            return False
        self.driver.execute_script(
            """
            const el = arguments[0];
            const text = arguments[1];
            el.focus();
            el.click();
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, text);
            el.dispatchEvent(new InputEvent('input', {
                bubbles: true, inputType: 'insertText', data: text
            }));
            """,
            self.prompt_text_area,
            request,
        )
        time.sleep(0.5)
        current = (self.driver.execute_script(
            "return (document.querySelector('div.ql-editor') || {}).innerText || '';"
        ) or "").strip()
        if request.strip() and request.strip() not in current.replace("\n", " "):
            self.log_infor("insertText khong do chu, fallback send_keys.", LOG_LEVEL.DEBUG)
            self.prompt_text_area.click()
            time.sleep(0.3)
            self.prompt_text_area.send_keys(request)
            time.sleep(0.5)
        return True

    def _response_texts_js(self):
        """Fallback khi CSS selector chua khop: lay text cac khoi tra loi qua tag Angular."""
        try:
            return self.driver.execute_script(
                """
                const nodes = [
                  ...document.querySelectorAll(
                    'model-response, message-content, assistant-messages-primary, .model-response-text'
                  )
                ];
                return nodes.map(n => (n.innerText || '').trim()).filter(Boolean);
                """
            ) or []
        except Exception:
            return []

    # ------------------------------------------------------------- lifecycle

    def initialize(self):
        self.is_context_created: bool = False
        options = uc.ChromeOptions()
        if self.headless_mode:
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-infobars')
            options.add_argument('--window-size=1920x1080')
            options.add_argument('--start-maximized')
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-accelerated-2d-canvas")

        options.add_argument(f"--user-data-dir={self.user_data_dir}")
        options.add_argument(f"--profile-directory={self.profile_directory}")

        if self.binary_path:
            options.binary_location = self.binary_path

        caps = DesiredCapabilities().CHROME
        caps["pageLoadStrategy"] = "eager"
        chrome_major = self._chrome_major_version()
        chrome_kwargs = {"options": options}
        if chrome_major:
            chrome_kwargs["version_main"] = chrome_major
            self.log_infor(f"Using ChromeDriver for Chrome {chrome_major}")
        if self.driver_path:
            chrome_kwargs["driver_executable_path"] = self.driver_path
        else:
            chrome_kwargs["desired_capabilities"] = caps
        self.driver: uc.Chrome = uc.Chrome(**chrome_kwargs)
        self.driver.get(self.url)

        if self.cookies_path:
            if self.log_level >= LOG_LEVEL.DEBUG:
                self.driver.get_screenshot_as_file("gemini_started.png")
            with open(self.cookies_path, 'r') as file_path:
                cookies_list = json.loads(file_path.read())
            for cookie in cookies_list:
                cookie.pop('domain', None)
                self.driver.add_cookie(cookie)

        if not self.is_login():
            self.log_infor("Chua dang nhap Gemini.")
            if self.require_manual_login:
                self.manual_login()

        self.prompt_text_area, _ = self._find_first(PROMPT_BOX_SELECTORS)
        if self.prompt_text_area is None:
            raise RuntimeError(
                "Khong tim thay o nhap prompt cua Gemini. Thuong do chua dang nhap "
                "(set manual_login = True trong tool_gemini_api.ini de dang nhap tay), "
                "hoac DOM Gemini da doi -> cap nhat PROMPT_BOX_SELECTORS."
            )

        if self.context_content:
            self.send_request('\n'.join(self.context_content.split("@")))

        self.is_context_created = True

    @classmethod
    def normalize_path(cls, path):
        return os.path.normpath(path)

    def kill_chrome_processes(self):
        self.log_infor("Kill backend process", LOG_LEVEL.DEBUG)
        user_data_dir = ToolGeminiAPI.normalize_path(self.user_data_dir)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] in ('chrome', 'chrome.exe', 'Google Chrome'):
                cmdline = [ToolGeminiAPI.normalize_path(cmd) for cmd in (proc.info['cmdline'] or [])]
                if any(user_data_dir in cmd for cmd in cmdline):
                    try:
                        proc.terminate()
                        self.log_infor(
                            f"Killed process {proc.info['pid']} with --user-data-dir={user_data_dir}",
                            LOG_LEVEL.DEBUG)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                        self.log_infor(f"Could not kill process {proc.info['pid']}: {e}", LOG_LEVEL.DEBUG)

    def get_user_dir(self):
        return self.user_data_dir

    def reset(self):
        self.quit()
        self.kill_chrome_processes()
        time.sleep(2)
        self.initialize()

    def quit(self):
        self.log_infor("Quitting...", LOG_LEVEL.DEBUG)
        if self.is_context_created and self.cleanup_context:
            self.log_infor("Deleting context...", LOG_LEVEL.DEBUG)
            self.delete_context()
        try:
            self.log_infor("Quitting driver...", LOG_LEVEL.DEBUG)
            time.sleep(2)
            self.driver.quit()
        except Exception:
            pass

    def __del__(self):
        """
Destructor for the ToolGeminiAPI class.

This method is called when an instance of the ToolGeminiAPI class is about to be destroyed.
It ensures that any necessary cleanup is performed, such as closing the Selenium browser.

**Returns:**

(*no returns*)
        """
        self.log_infor("Quitting from destructor...", LOG_LEVEL.DEBUG)
        self.quit()

    # ------------------------------------------------------------------- auth

    def is_login(self) -> bool:
        """
Check if the user is logged in to the Gemini web interface.

**Returns:**

  / *Type*: bool /

  True if the user is logged in, otherwise False.
        """
        current_url = (self.driver.current_url or "")
        if any(marker in current_url for marker in LOGGED_OUT_URL_MARKERS):
            return False
        for selector in LOGGED_OUT_SELECTORS:
            try:
                self.driver.find_element(By.CSS_SELECTOR, selector)
                return False
            except NoSuchElementException:
                continue
        return True

    def manual_login(self):
        """
Perform a manual login to the Gemini web interface.

This method initiates the manual login process, allowing the user to enter their credentials
and complete any required authentication steps.

**Returns:**

(*no returns*)
        """
        input("Please log in manually and press Enter to continue...")
        cookies_list = self.driver.get_cookies()
        cookies_out = self.cookies_path or os.path.join(self.SCRIPT_DIR, "cookies.pkl")
        with open(cookies_out, 'w') as file_path:
            json.dump(cookies_list, file_path, indent=2, sort_keys=True)
        self.log_infor(f"Cookies saved to {cookies_out}")

    # ---------------------------------------------------------------- context

    def delete_context(self):
        """
Delete the current conversation context.

Gemini khong co "delete chat" don gian nhu ChatGPT trong luong tu dong; cach an toan
va it phu thuoc DOM nhat la mo mot cuoc tro chuyen moi (New chat), hoac reload /app.

**Returns:**

(*no returns*)
        """
        self.log_infor("Reset context (new chat)", LOG_LEVEL.DEBUG)
        button, _ = self._find_first(NEW_CHAT_SELECTORS, timeout=3)
        if button is not None:
            try:
                button.click()
                self.is_context_created = False
                return
            except Exception as e:
                self.log_infor(f"Click New chat that bai: {e}", LOG_LEVEL.DEBUG)
        if self._click_by_visible_text(NEW_CHAT_LABELS):
            self.is_context_created = False
            return
        try:
            self.driver.get(self.url)
        except Exception as e:
            self.log_infor(f"Reload {self.url} that bai: {e}", LOG_LEVEL.DEBUG)
        self.is_context_created = False

    def new_chat(self):
        """Alias de doc cho de hieu: mo cuoc tro chuyen moi."""
        self.delete_context()

    def refresh(self):
        try:
            self.driver.refresh()
        except Exception:
            pass
        self.prompt_text_area, _ = self._find_first(PROMPT_BOX_SELECTORS)

    # ------------------------------------------------------------------- I/O

    def upload_file(self, file_paths):
        """
Upload one or more files to the current Gemini conversation.

**Arguments:**

* ``file_paths``

  / *Condition*: required / *Type*: str | list /

  Path (or list of paths) of the file(s) to upload.

**Returns:**

  / *Type*: bool /

  True if the file input accepted the path(s), otherwise False.
        """
        self.refresh()
        time.sleep(2)
        self.log_infor("Refreshed before upload file")

        # Gemini khong render input[type=file] cho den khi menu upload duoc mo.
        file_input, _ = self._find_first(FILE_INPUT_SELECTORS, timeout=2)
        if file_input is None:
            upload_button, _ = self._find_first(UPLOAD_MENU_SELECTORS, timeout=5, visible=True)
            if upload_button is None:
                self.log_infor(
                    "Khong tim thay nut mo menu upload cua Gemini "
                    "-> cap nhat UPLOAD_MENU_SELECTORS.")
                return False
            self._js_click(upload_button)
            deadline = time.time() + 8
            while time.time() < deadline:
                file_input, _ = self._find_first(FILE_INPUT_SELECTORS, timeout=0.4)
                if file_input is not None:
                    break
                file_item, _ = self._find_first(UPLOAD_FILE_ITEM_SELECTORS, timeout=0.4)
                if file_item is not None:
                    self._js_click(file_item)
                    continue
                if self._click_by_visible_text(UPLOAD_FILE_ITEM_LABELS, contains=True):
                    continue
                time.sleep(0.4)

        if file_input is None:
            try:
                menu = self.driver.execute_script(
                    """
                    return [...document.querySelectorAll('[role="menu"] *, [role="menuitem"], button, a')]
                      .filter(b => b.offsetParent !== null)
                      .map(b => ({
                        aria: b.getAttribute('aria-label'),
                        testid: b.getAttribute('data-test-id'),
                        text: (b.innerText || '').trim().slice(0, 60),
                      }))
                      .filter(x => (x.aria || x.text));
                    """
                )
                self.log_infor(f"DOM sau khi mo upload: {menu}", LOG_LEVEL.DEBUG)
            except Exception:
                pass
            self.log_infor(
                "Da mo menu upload nhung khong thay input[type=file] "
                "-> cap nhat FILE_INPUT_SELECTORS.")
            return False
        try:
            paths = file_paths if isinstance(file_paths, list) else [file_paths]
            paths = [os.path.abspath(p) for p in paths]
            before_previews = self._composer_preview_count()
            file_input.send_keys('\n'.join(paths))
        except Exception as ex:
            self.log_infor(f"Upload file failed. Exception: {ex}")
            return False
        names = [os.path.basename(p) for p in paths]
        if not self._wait_for_attachment(names, before_previews, timeout=20):
            self.log_infor(
                f"Da send_keys nhung khong thay preview tep {names} tren UI.")
            return False
        return True

    def _composer_preview_count(self):
        """So thumbnail blob/data trong composer. Gemini khong luon hien ten file."""
        try:
            return int(self.driver.execute_script(
                """
                return [...document.querySelectorAll('img')].filter(img => {
                    const src = img.src || '';
                    return (src.startsWith('blob:') || src.startsWith('data:'))
                        && img.offsetParent !== null;
                }).length;
                """
            ) or 0)
        except Exception:
            return 0

    def _wait_for_attachment(self, names, before_previews=0, timeout=20):
        """Cho Gemini hien chip/preview sau khi chon file (dac biet anh)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if self._composer_preview_count() > before_previews:
                    self.log_infor("Attachment: them thumbnail trong o nhap.", LOG_LEVEL.DEBUG)
                    return True
                found = self.driver.execute_script(
                    """
                    const names = arguments[0];
                    const hay = (s) => (s || '').toString();
                    const nodes = [...document.querySelectorAll(
                        'img, [aria-label], [alt], span, button, a, [class*="chip"], [class*="attachment"], [class*="preview"]'
                    )];
                    return names.filter(name => {
                        const stem = name.replace(/\\.[^.]+$/, '');
                        return nodes.some(el => {
                            const blob = [
                              hay(el.innerText), hay(el.getAttribute('aria-label')),
                              hay(el.getAttribute('alt')), hay(el.getAttribute('src')),
                              hay(el.getAttribute('title'))
                            ].join(' ');
                            return blob.includes(name) || (stem && blob.includes(stem));
                        });
                    });
                    """,
                    names,
                ) or []
                if len(found) >= len(names):
                    self.log_infor(f"Attachment hien tren UI: {found}", LOG_LEVEL.DEBUG)
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def _current_answer_count(self) -> int:
        elements, _ = self._find_all_first(RESPONSE_SELECTORS)
        return len(elements)

    def _is_generating(self) -> bool:
        for selector in STOP_BUTTON_SELECTORS:
            try:
                if self.driver.find_element(By.CSS_SELECTOR, selector).is_displayed():
                    return True
            except NoSuchElementException:
                continue
        return False

    def _wait_for_answer(self, previous_count: int) -> str:
        """Cho cau tra loi moi xuat hien va on dinh (text khong doi nua).

        Khong dua vao rieng nut Stop vi selector do de doi; moc chinh la text
        cua cau tra loi cuoi ngung thay doi trong vai lan poll lien tiep.
        """
        deadline = time.time() + self.timeout
        stable_text = None
        stable_hits = 0
        previous_js = self._response_texts_js()

        while time.time() < deadline:
            text = None
            elements, _ = self._find_all_first(RESPONSE_SELECTORS)
            if len(elements) > previous_count:
                try:
                    text = (elements[-1].text or "").strip() or None
                except Exception:
                    text = None
            if not text:
                js_texts = self._response_texts_js()
                if js_texts and (len(js_texts) > len(previous_js) or js_texts != previous_js):
                    text = js_texts[-1]

            if not text:
                time.sleep(1)
                continue

            if text == stable_text and not self._is_generating():
                stable_hits += 1
                if stable_hits >= 3:
                    return text
            else:
                stable_hits = 0
                stable_text = text
            time.sleep(1)

        self.log_infor(f"Het {self.timeout}s cho cau tra loi Gemini.", LOG_LEVEL.DEBUG)
        try:
            tags = self.driver.execute_script(
                """
                return [...new Set([...document.querySelectorAll('*')]
                  .filter(el => el.tagName.includes('-'))
                  .map(el => el.tagName.toLowerCase()))].sort();
                """
            )
            self.log_infor(f"Custom elements luc timeout: {tags}", LOG_LEVEL.DEBUG)
        except Exception:
            pass
        return stable_text

    def send_request(self, request: str) -> str:
        """
Send a request to the Gemini web interface and receive a response.

**Arguments:**

* ``request``

  / *Condition*: required / *Type*: str /

  The request string to be sent to Gemini.

**Returns:**

  / *Type*: str /

  The response from Gemini, or None on failure.
        """
        self.prompt_text_area, _ = self._find_first(PROMPT_BOX_SELECTORS)
        if self.prompt_text_area is None:
            self.log_infor("Khong tim thay o nhap prompt.")
            return None

        previous_count = self._current_answer_count()
        if not self._fill_prompt(request):
            return None

        send_button, _ = self._find_first(SEND_BUTTON_SELECTORS, timeout=5, visible=True)
        if send_button is not None and send_button.is_enabled():
            self._js_click(send_button)
        else:
            self.log_infor("Khong dung duoc nut Send, gui bang Enter.", LOG_LEVEL.DEBUG)
            self.prompt_text_area.send_keys(Keys.RETURN)

        return self._wait_for_answer(previous_count)


def extract_json(text: str) -> dict:
    """
Extract JSON data from a given text string.

**Arguments:**

* ``text``

  / *Condition*: required / *Type*: str /

  The text string containing JSON data.

**Returns:**

  / *Type*: dict /

  A dictionary representation of the extracted JSON data.
    """
    json_regex = re.compile(r'{\s*"cn":.*?}', re.DOTALL)
    match = json_regex.search(text)
    json_data = None
    if match:
        json_data = json.loads(match.group())
    else:
        print("No suitable answer responsed.")
    return json_data


atexit.register(ToolGeminiAPI.cleanup_all)

if __name__ == "__main__":
    tool_api = ToolGeminiAPI()
    print("test")
    resp = tool_api.send_request("Dịch giúp mình: 乾坤天意愛維新")
    print(resp)
    del tool_api
