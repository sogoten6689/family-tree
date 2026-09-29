# *******************************************************************************
#
# File: tool_chatgpt_api.py
#
# Initially created by Cuong Nguyen / July 2024
#
# Description:
#   Provides a ChatGPT API-like class for users to interact with as if it were a real API.
#   This implementation uses Selenium to run a browser in the background, handling interactions
#   with the ChatGPT web interface and maintaining context for conversations.

#   Users can utilize this class to simulate API calls to ChatGPT, while the underlying
#   mechanism uses Selenium to manage the browser and perform the necessary actions to
#   communicate with ChatGPT..
#
# History:
#
# 01.07.2024 / V 0.1 / Cuong Nguyen
# - Initialize
#
# *******************************************************************************
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from signal import *
import pickle
import time
import configparser
import undetected_chromedriver as uc
import os
import re
import json
import psutil
import atexit


class LOG_LEVEL:
    INFO = 1
    DEBUG = 2
    ERROR = 3

class ToolChatGPTAPI:
    """
A ChatGPT API-like class for simulating API interactions with ChatGPT.

This class uses Selenium to control a web browser, allowing users to interact with the ChatGPT
web interface programmatically. It maintains the context of conversations and performs actions
on behalf of the user, providing a seamless API-like experience.

Methods of this class enable users to send messages, receive responses, and manage conversation
context, mimicking the behavior of a real API while leveraging the ChatGPT web interface
through Selenium.
    """

    SCRIPT_DIR:str = os.path.dirname(os.path.abspath(__file__))
    INI_FILE_PATH:str = os.path.join(SCRIPT_DIR, 'tool_chatgpt_api.ini')
    _instances = []
    LOG_LEVEL_MAP = {
        'none': 0,
        'info': 1,
        'debug': 2,        
        'error': 3
    }

    def __init__(self, config_path=""):
        """
Constructor for the ToolChatGPTAPI class.

**Arguments:**

* ``config_path``

  / *Condition*: optional / *Type*: str / *Default*: "" /

  The path to the configuration file.

**Returns:**

(*no returns*)
        """
        # Read configuration from tool_chatgpt_api.ini
        config = configparser.ConfigParser()
        if not config_path:
            config_path = ToolChatGPTAPI.INI_FILE_PATH
        with open(config_path, 'r', encoding='utf-8') as configfile:
            config.read_file(configfile)       

        # Extract configuration values
        self.user_data_dir = config.get('options', 'user-data-dir')
        self.profile_directory = config.get('options', 'profile-directory')
        self.log_level = ToolChatGPTAPI.LOG_LEVEL_MAP[config.get('options', 'log_level')]
        self.driver_path: str = config.get('driver', 'driver_path')
        self.url: str = config.get('site', 'url')
        self.wait_time: int = config.getint('context', 'wait_time')
        self.use_chatgpt4o = config.getboolean('site', 'use_chatgpt4o')
        self.cleanup_context = config.getboolean('context', 'cleanup_context')
        self.require_manual_login = config.getboolean('options', 'manual_login')
        self.context_content = config.get('context', 'context_content')
        self.headless_mode = config.getboolean('options', 'headless_mode', fallback=False)
        self.cookies_path = config.get('driver', 'cookies_path', fallback="")
        self.binary_path = config.get('driver', 'binary_path', fallback="")
        
        self.initialize()
        ToolChatGPTAPI._instances.append(self)
    
    def log_infor(self, log_msg, level=LOG_LEVEL.INFO):
        if level <= self.log_level:
            print(log_msg)

    @classmethod
    def cleanup_all(cls):
        print("Cleaning up all...")
        for instance in cls._instances:
            instance.quit()

    def _chrome_major_version(self):
        candidates = []
        if self.binary_path:
            candidates.append(self.binary_path)
        candidates.extend([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ])
        for binary in candidates:
            if os.path.exists(binary):
                try:
                    import subprocess
                    out = subprocess.check_output(
                        [binary, "--version"], stderr=subprocess.STDOUT, text=True
                    )
                    match = re.search(r"(\d+)\.", out)
                    if match:
                        return int(match.group(1))
                except Exception:
                    pass
        return None

    def initialize(self):
        self.is_context_created: bool = False
        options = uc.ChromeOptions()
        if self.headless_mode:
            options.add_argument('--headless=new')  # Enable headless mode
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-infobars')
            options.add_argument('--window-size=1920x1080')
            options.add_argument('--start-maximized')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

            # Additional options to make headless mode more stealthy
            options.add_argument("--disable-extensions")
            # options.add_argument("--proxy-server='direct://'")
            # options.add_argument("--proxy-bypass-list=*")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-accelerated-2d-canvas")
            options.add_argument("--disable-accelerated-jpeg-decoding")
            options.add_argument("--disable-accelerated-mjpeg-decoding")
            options.add_argument("--disable-accelerated-video-decode")
            options.add_argument("--disable-accelerated-video-encode")
            
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
        print(os.environ.get('https_proxy'))
        self.driver.get(self.url)

        if self.cookies_path:
            if self.log_level >= LOG_LEVEL.DEBUG:
                self.driver.get_screenshot_as_file("chatGPT_started.png")

            with open(self.cookies_path, 'r') as file_path:
                cookies_list = json.loads(file_path.read())

            # Once on that domain, start adding cookies into the browser
            for cookie in cookies_list:
                # If domain is left in, then in the browser domain gets transformed to f'.{domain}'
                cookie.pop('domain', None)
                self.driver.add_cookie(cookie)

        if not self.is_login() and self.require_manual_login:
            self.manual_login()
        
        self.use_4o = False
        if self.use_chatgpt4o and self.check_chatgpt4o():
            # check_pass = self.check_chatgpt4o()
            self.use_4o = True

        self.prompt_text_area: WebElement = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.ID, "prompt-textarea"))
            )
            
        if self.context_content:
            self.send_request('\n'.join(self.context_content.split("@")))

        self.is_context_created = True
    
    @classmethod
    def normalize_path(cls, path):
        return os.path.normpath(path)

    @classmethod
    def kill_chrome(cls, user_data_dir):
        print("Kill backend process")
        user_data_dir = ToolChatGPTAPI.normalize_path(user_data_dir)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] == 'chrome' or proc.info['name'] == 'chrome.exe':
                cmdline = [ToolChatGPTAPI.normalize_path(cmd) for cmd in proc.info['cmdline']]
                if any(user_data_dir in cmd for cmd in cmdline):
                    try:
                        proc.terminate()  # Or proc.kill() to force kill
                        print(f"Killed process {proc.info['pid']} with --user-data-dir={user_data_dir}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                        print(f"Could not kill process {proc.info['pid']}: {e}")

    def kill_chrome_processes(self):
        self.log_infor(
        print("Kill backend process"), LOG_LEVEL.DEBUG)
        user_data_dir = ToolChatGPTAPI.normalize_path(self.user_data_dir)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] == 'chrome' or proc.info['name'] == 'chrome.exe':
                cmdline = [ToolChatGPTAPI.normalize_path(cmd) for cmd in proc.info['cmdline']]
                if any(user_data_dir in cmd for cmd in cmdline):
                    try:
                        proc.terminate()  # Or proc.kill() to force kill
                        self.log_infor(f"Killed process {proc.info['pid']} with --user-data-dir={user_data_dir}", LOG_LEVEL.DEBUG)
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
        self.log_infor("Quitting...",LOG_LEVEL.DEBUG)
        if self.is_context_created and self.cleanup_context:
            self.log_infor("Deleting context...", LOG_LEVEL.DEBUG)
            self.delete_context()
        try:
            self.log_infor("Quitting driver...", LOG_LEVEL.DEBUG)
            time.sleep(2)
            self.driver.quit()
        except:
            pass

    def __del__(self):
        """
Destructor for the ToolChatGPTAPI class.

This method is called when an instance of the ToolChatGPTAPI class is about to be destroyed.
It ensures that any necessary cleanup is performed, such as closing the Selenium browser.

**Returns:**

(*no returns*)
        """
        # if self.is_context_created:
        #     self.delete_context()
        # self.driver.quit()
        self.log_infor("Quitting from destructor...", LOG_LEVEL.DEBUG)
        self.quit()

    def is_login(self) -> bool:
        """
Check if the user is logged in to the ChatGPT web interface.

**Returns:**

  / *Type*: bool /

  True if the user is logged in, otherwise False.
        """
        # Trang ChatGPT khi chưa đăng nhập chỉ render "lightweight composer" (không có
        # #prompt-textarea) kèm các nút Log in / Sign up. Chỉ dựa vào
        # button[data-testid="login-button"] là không đủ vì testid này đã bị đổi.
        selectors = [
            'button[data-testid="login-button"]',
            'button[data-testid="signup-button"]',
            'a[href^="/auth/login"]',
            '#mobile-composer-prompt',
        ]
        for selector in selectors:
            try:
                self.driver.find_element(By.CSS_SELECTOR, selector)
                return False
            except NoSuchElementException:
                continue
        return True
    
    def manual_login(self):
        """
Perform a manual login to the ChatGPT web interface.

This method initiates the manual login process, allowing the user to enter their credentials
and complete any required authentication steps.

**Returns:**

(*no returns*)
        """
        input("Please log in manually and press Enter to continue...")
        # pickle.dump(self.driver.get_cookies(), open("cookies.pkl", "wb"))
        # Write out the cookies while you are logged in
        cookies_list = self.driver.get_cookies()
        with open("cookies.pkl", 'w') as file_path:
            json.dump(cookies_list, file_path, indent=2, sort_keys=True)

    def delete_context(self):
        """
Delete the current conversation context.

This method clears the conversation history, allowing for a fresh start without any previous
context affecting the new interactions.

**Returns:**

(*no returns*)
        """
        # Wait for the button element to appear and click on it if found
        self.log_infor("Delete current context", LOG_LEVEL.DEBUG)
        try:
            xpath = ("//div[contains(@class, 'absolute') and contains(@class, 'bottom-0') and contains(@class, 'top-0') and "
            "contains(@class, 'items-center') and contains(@class, 'gap-1.5') and contains(@class, 'pr-2') and "
            "(contains(@class, 'ltr:right-0') or contains(@class, 'rtl:left-0')) and contains(@class, 'flex') and "
            "not(contains(@class, 'hidden')) and not(contains(@class, 'can-hover:group-hover:flex'))]"
            "//button[starts-with(@id, 'radix-:')]")

            self.log_infor("Find option button", LOG_LEVEL.DEBUG)
            # Find the button element with the specified criteria
            button = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            button.click()
            
            self.log_infor("Delete context", LOG_LEVEL.DEBUG)
            # Wait for the "Delete" menu item to appear and click on it
            delete_menu_item = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.XPATH, '//div[@role="menuitem" and contains(@class, "text-token-text-error") and contains(text(), "Delete")]'))
            )
            delete_menu_item.click()
            
            # Wait for the popup to appear and click the "Delete" button within the popup
            delete_button_popup = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.XPATH, '//button[@class="btn relative btn-danger" and @as="button"]//div[contains(text(), "Delete")]'))
            )
            delete_button_popup.click()
            
            self.log_infor("Clicked on the 'Delete' button in the popup.",LOG_LEVEL.DEBUG)
        except Exception as e:
            self.log_infor(f"An error occurred: {e}", LOG_LEVEL.DEBUG)
            
        self.is_context_created = False
    
    def check_chatgpt4o(self):
        """
Check if ChatGPT-4.0 is available.

This method verifies the availability of ChatGPT-4.0 for use.

**Returns:**

  / *Type*: bool /

  True if ChatGPT-4.0 is available, otherwise False.
        """
        # Wait for the element containing "3.5" and click on it if found
        chatgpt_version = None
        try:
            chatgpt_version = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "ChatGPT") and span[contains(text(), "4o")]]'))
            )
        except Exception as ex:
            pass
        else:
            self.log_infor("Already using chatGPT 4o.")
            return True

        try:
            chatgpt_version = WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "ChatGPT") and span[contains(text(), "3.5")]]'))
            )
        except Exception as ex:
            pass

        if chatgpt_version:
            chatgpt_version.click()
            # Wait for the element containing "GPT-4o" and click on it
            try:
                gpt_4o = WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "GPT-4o") and div[contains(text(), "Newest and most advanced model")]]'))
                )
            except Exception as ex:
                self.log_infor("GPT-4o not found. Use ChatGPT verion 3.5")
                return False
            else:
                gpt_4o.click()
                return True
        else:
            self.log_infor("ChatGPT version not found. Use default.")
            return False

    def refresh(self):
        # self.driver.refresh()
        try:
            # self.driver.get(self.url)
            self.driver.refresh()
        except:
            pass
        self.prompt_text_area: WebElement = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.ID, "prompt-textarea"))
            )
        
        self.voice_button = WebDriverWait(self.driver, self.wait_time).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//button[@aria-label='Start voice mode' and @data-testid='composer-speech-button']")
            )
        )

    def upload_file(self, file_paths):
        if not self.use_4o:
            self.log_infor("This function only work with ChatGPT4o")
            return False
        
        self.refresh()
        
        self.log_infor("Refreshed before upload file")
        try:
            file_upload = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@type='file' and @multiple and @tabindex='-1' and @class='hidden' and @style='display: none;']"))
                    )
            # file_upload.clear()
            if isinstance(file_paths, list):
                file_upload.send_keys('\n'.join(file_paths))
            else:
                file_upload.send_keys(file_paths)

            # WebDriverWait(self.driver, 30).until(
                # EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'absolute inset-0 flex items-center justify-center bg-black/5 text-white')]"))
            # )
            self.send_button = WebDriverWait(self.driver, self.wait_time).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//button[@aria-label='Send prompt' and @data-testid='send-button']")
                )
            )
            # Wait for the button to become enabled
            WebDriverWait(self.driver, 30).until(
                lambda driver: not self.send_button.get_attribute("disabled")
            )
        except Exception as ex:
            self.log_infor(f"Upload file failed. Exception: {ex}")
            return False
        else:
            return True

    def check_conditions(self, present_css, absent_xpath, retries=4):
        """
        Check if one element is present and another is absent. Retry the check up to 4 times if the condition is not met.
        
        :param driver: The Selenium WebDriver instance.
        :param present_xpath: XPath of the element that should be present.
        :param absent_xpath: XPath of the element that should be absent.
        :param retries: Number of retries if the condition is not met.
        :return: True if the condition is met within the given retries, False otherwise.
        """
        for attempt in range(retries):
            try:
                # Check if the present element is present
                send_button = WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.XPATH, present_css))
                )
                self.log_infor(f"Attempt {attempt + 1}: The element with css '{present_css}' is present.", LOG_LEVEL.DEBUG)
                
                # Check if the absent element is absent
                try:
                    contgenerate_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, absent_xpath))
                    )
                    self.log_infor(f"Attempt {attempt + 1}: The element with xpath '{absent_xpath}' is present.", LOG_LEVEL.DEBUG)
                    contgenerate_button.click()
                    time.sleep(1)
                    self.log_infor("Continue generate...", LOG_LEVEL.DEBUG)
                    # If the absent element is found, retry
                    continue
                except TimeoutException:
                    # The absent element is not found
                    self.log_infor(f"Attempt {attempt + 1}: The element with xpath '{absent_xpath}' is absent.", LOG_LEVEL.DEBUG)
                    return send_button
            except TimeoutException:
                self.log_infor(f"Attempt {attempt + 1}: The element with css '{present_css}' is not present.", LOG_LEVEL.DEBUG)
                continue
            
            self.log_infor(f"Attempt {attempt + 1}: Condition not met, retrying...", LOG_LEVEL.DEBUG)
        
        return None
        
    def send_request(self, request: str) -> str:
        """
Send a request to the ChatGPT web interface and receive a response.

**Arguments:**

* ``request``

  / *Condition*: required / *Type*: str /

  The request string to be sent to ChatGPT.

**Returns:**

  / *Type*: str /

  The response from ChatGPT.
        """
        self.prompt_text_area: WebElement = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.ID, "prompt-textarea"))
            )
        if self.prompt_text_area:
            lines = request.split('\n')
            for line in lines:
                self.prompt_text_area.send_keys(line)
                self.prompt_text_area.send_keys(Keys.SHIFT, Keys.RETURN)  # Send SHIFT + RETURN for newline
            

            # self.send_button = WebDriverWait(self.driver, self.wait_time).until(
                # EC.presence_of_element_located((By.XPATH, "//*[name()='svg'][@class='icon-2xl']"))
            # )
            self.send_button = WebDriverWait(self.driver, self.wait_time).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//button[@aria-label='Send prompt' and @data-testid='send-button']")
                )
            )
            # self.prompt_text_area.send_keys(request)
            if self.send_button.is_enabled():
                self.send_button.click()
            else:
                self.log_infor("Send button is disabled.", LOG_LEVEL.DEBUG)

            max_try = 3
            while max_try > 0: 
            # Wait for the send button element to appear
                try:
                    try:
                        stop_button = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, "//*[name()='svg'][@class='icon-lg']"))
                        )
                    except:
                        pass
                    else: 
                        self.log_infor("Found Stop button.", LOG_LEVEL.DEBUG)
                    
                    send_button = self.check_conditions("//button[@aria-label='Start voice mode']", '//button[contains(@class, "btn relative btn-secondary") and contains(., "Continue generating")]')

                    last_answer = WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]'))
                    )
                    last_answer = last_answer[-1]

                    # self.send_button = send_button
                except Exception as ex:
                    print(ex)
                    self.click_regen()
                    max_try -= 1
                else:
                    return last_answer.text
        return None
    
    def click_regen(self):
        """
Click the 'Regenerate Response' button on the ChatGPT web interface.

This method simulates a click on the 'Regenerate Response' button to request a new response
for the current context.

**Returns:**

(*no returns*)
        """
        # Wait for the button with class 'btn relative btn-primary m-auto' and click on it if found
        try:
            regenerate_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//button[contains(@class, "btn relative btn-primary m-auto") and contains(., "Regenerate")]'))
            )
            regenerate_button.click()
            self.log_infor("Regenerate button clicked.", LOG_LEVEL.DEBUG)
        except:
            self.log_infor("Regenerate button not found.", LOG_LEVEL.DEBUG)

def extract_json(text:str) -> dict:
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
    # Regular expression to match the JSON string
    json_regex = re.compile(r'{\s*"cn":.*?}', re.DOTALL)

    # Find the JSON string in the text
    match = json_regex.search(text)
    json_data = None

    if match:
        json_str = match.group()
        # print("Extracted JSON string:")
        # print(json_str)
        
        # Optionally, you can parse the JSON string into a Python dictionary
        json_data = json.loads(json_str)
    else:
        print("No suitable answer responsed.")
    return json_data

def signal_handler(sig, frame, obj):
   """
Handle signals from the operating system.

**Arguments:**

* ``sig``

  / *Condition*: required / *Type*: int /

  The signal number received from the OS.

* ``frame``

  / *Condition*: required / *Type*: frame object /

  The current stack frame.

* ``obj``

  / *Condition*: required / *Type*: object /

  The object that is handling the signal.

**Returns:**

(*no returns*)
   """
   # This function will be called when a SIGINT signal (Ctrl+C) is received
   print("\nCtrl+C pressed - Cleaning up...")
   # Perform any necessary cleanup here
   # For example, call the cleanup method of the object
   del obj
   # Exit the program
   exit(0)

atexit.register(ToolChatGPTAPI.cleanup_all)

if __name__ == "__main__":
    tool_api = ToolChatGPTAPI()

    # for sign in (SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    #   signal(sign, lambda sig, frame: signal_handler(sig, frame, tool_api))

    # tool_api.reset()
    print("test")
    resp = tool_api.send_request("Dịch giúp mình: 乾坤天意愛維新")
    print(resp)
    del tool_api

    # try:
    #     while True:
    #         cn_input = input("Nhập câu đối Hán tự:")
    #         answer = tool_api.send_request(cn_input)
    #         json_answer = extract_json(answer)
    #         print("\n")
    #         print(f"--> Dịch âm: {json_answer['sv']}\n")
    #         print(f"--> Dịch nghĩa: {json_answer['vi']}\n")
    # except KeyboardInterrupt:
    #     del tool_api
    #     print('interrupted!')