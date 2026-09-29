"""Do DOM that cua Gemini web de xac minh / cap nhat cac selector trong tool_gemini_api.py.

Script chi DOC DOM: mo gemini.google.com, dem xem selector nao match, go thu 1 chuoi
vao o nhap de nut Send hien ra roi liet ke cac nut, chup anh man hinh, roi dong browser.
KHONG bam gui, nen khong tao request nao len Gemini va khong sua gi tren tai khoan.

Chay:
    python3 probe_dom.py

Output: in ra selector nao match (theo tung vai tro) + anh gemini_probe.png cung thu muc.
"""
import json
import os
import sys
import time

from tool_gemini_api import (
    ToolGeminiAPI,
    PROMPT_BOX_SELECTORS,
    SEND_BUTTON_SELECTORS,
    RESPONSE_SELECTORS,
    STOP_BUTTON_SELECTORS,
    NEW_CHAT_SELECTORS,
    UPLOAD_MENU_SELECTORS,
    UPLOAD_FILE_ITEM_SELECTORS,
    FILE_INPUT_SELECTORS,
)

HERE = os.path.dirname(os.path.abspath(__file__))

GROUPS = {
    "prompt_box": PROMPT_BOX_SELECTORS,
    "send_button": SEND_BUTTON_SELECTORS,
    "response": RESPONSE_SELECTORS,
    "stop_button": STOP_BUTTON_SELECTORS,
    "new_chat": NEW_CHAT_SELECTORS,
    "upload_menu": UPLOAD_MENU_SELECTORS,
    "upload_file_item": UPLOAD_FILE_ITEM_SELECTORS,
    "file_input": FILE_INPUT_SELECTORS,
}

DUMP_BUTTONS_JS = """
    const vis = arguments[0];
    return [...document.querySelectorAll('button, a[role="button"], [role="button"]')]
      .filter(b => vis ? b.offsetParent !== null : true)
      .map(b => ({
        tag: b.tagName.toLowerCase(),
        aria: b.getAttribute('aria-label'),
        testid: b.getAttribute('data-test-id') || b.getAttribute('data-testid'),
        cls: (b.className || '').toString().slice(0, 120),
        text: (b.innerText || '').trim().slice(0, 40),
        visible: b.offsetParent !== null,
      }));
"""

DUMP_INPUT_AREA_JS = """
    const box = document.querySelector('rich-textarea')
        || document.querySelector('div.ql-editor');
    const area = document.querySelector('input-area')
        || document.querySelector('.input-area')
        || document.querySelector('bard-mode-switcher')?.parentElement;
    return {
      boxTag: box ? box.tagName : null,
      boxHtml: box ? box.outerHTML.slice(0, 1500) : null,
      editorText: (document.querySelector('div.ql-editor') || {}).innerText || null,
      nearbyButtons: [...document.querySelectorAll('input-container button, .input-area button, rich-textarea ~ * button, [class*="input-area"] button')]
        .map(b => ({
          aria: b.getAttribute('aria-label'),
          testid: b.getAttribute('data-test-id'),
          text: (b.innerText || '').trim().slice(0, 30),
          html: b.outerHTML.slice(0, 400),
        })),
    };
"""

DUMP_CUSTOM_JS = """
    const names = new Set();
    [...document.querySelectorAll('*')].forEach(el => {
      if (el.tagName.includes('-')) names.add(el.tagName.toLowerCase());
    });
    return [...names].sort();
"""


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tool = ToolGeminiAPI.__new__(ToolGeminiAPI)
    tool.log_level = ToolGeminiAPI.LOG_LEVEL_MAP['debug']
    tool.user_data_dir = os.path.join(os.environ.get("TEMP", "/tmp"), "gemini_api_chrome")
    tool.profile_directory = "Default"
    tool.driver_path = ""
    tool.binary_path = ""
    tool.headless_mode = False
    tool.cookies_path = ""
    tool.url = "https://gemini.google.com/app"
    tool.wait_time = 20
    tool.is_context_created = False

    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={tool.user_data_dir}")
    options.add_argument(f"--profile-directory={tool.profile_directory}")
    major = tool._chrome_major_version()
    tool.driver = uc.Chrome(options=options, version_main=major) if major else uc.Chrome(options=options)

    try:
        tool.driver.get(tool.url)
        time.sleep(8)

        print("URL   =", tool.driver.current_url)
        print("TITLE =", tool.driver.title)
        print("is_login() =", tool.is_login())

        def match_report(label):
            result = {}
            for role, selectors in GROUPS.items():
                hits = {}
                for selector in selectors:
                    count = len(tool.driver.find_elements("css selector", selector))
                    if count:
                        hits[selector] = count
                result[role] = hits
            print(f"\n=== selector match ({label}) ===")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result

        def dump_buttons(label, visible_only=True):
            buttons = tool.driver.execute_script(DUMP_BUTTONS_JS, visible_only)
            print(f"\n=== nut {'dang hien' if visible_only else 'tat ca'} ({label}) ===")
            print(json.dumps(buttons, ensure_ascii=False, indent=2))
            return buttons

        match_report("o nhap con trong")
        dump_buttons("o nhap con trong", visible_only=True)
        dump_buttons("o nhap con trong", visible_only=False)

        print("\n=== custom elements ===")
        print(json.dumps(tool.driver.execute_script(DUMP_CUSTOM_JS), ensure_ascii=False, indent=2))

        print("\n=== input area truoc khi go ===")
        print(json.dumps(tool.driver.execute_script(DUMP_INPUT_AREA_JS), ensure_ascii=False, indent=2))

        box = tool.driver.find_element("css selector", PROMPT_BOX_SELECTORS[0])
        box.click()
        time.sleep(0.5)
        box.send_keys("test")
        time.sleep(2)
        editor_after_send_keys = tool.driver.execute_script(
            "return (document.querySelector('div.ql-editor') || {}).innerText || '';"
        )
        print("\n=== editor.innerText sau send_keys ===")
        print(repr(editor_after_send_keys))

        if not (editor_after_send_keys or "").strip() or editor_after_send_keys.strip() in ("", "\n"):
            print("send_keys khong do chu; thu execCommand insertText")
            tool.driver.execute_script(
                """
                const el = arguments[0];
                el.focus();
                document.execCommand('insertText', false, 'test');
                el.dispatchEvent(new InputEvent('input', {bubbles: true, data: 'test'}));
                """,
                box,
            )
            time.sleep(2)
            print("editor.innerText sau insertText =", repr(
                tool.driver.execute_script(
                    "return (document.querySelector('div.ql-editor') || {}).innerText || '';"
                )
            ))

        match_report("sau khi go chu")
        dump_buttons("sau khi go chu", visible_only=True)

        print("\n=== input area sau khi go ===")
        print(json.dumps(tool.driver.execute_script(DUMP_INPUT_AREA_JS), ensure_ascii=False, indent=2))

        shot = os.path.join(HERE, "gemini_probe.png")
        tool.driver.get_screenshot_as_file(shot)
        print("\nscreenshot:", shot)
    finally:
        tool.driver.quit()


if __name__ == "__main__":
    main()
