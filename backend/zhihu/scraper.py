"""Cào kết quả tìm kiếm Zhihu bằng Playwright (persistent context).

Chỉ đọc nội dung đang hiển thị trên trang với tài khoản của chính người dùng.
Không vượt paywall, không gọi API ẩn.

Lưu ý: Playwright sync API phải được tạo và dùng trong CÙNG một thread.
Mỗi job mở một ZhihuSession trong thread worker của nó rồi đóng lại.
"""
from __future__ import annotations

import asyncio
import random
import re
import sys
import threading
import time
from urllib.parse import quote

from . import config

# Chỉ một trình duyệt được dùng thư mục profile tại một thời điểm
_BROWSER_LOCK = threading.Lock()
_LOGIN_FLAG = config.PROFILE_DIR / "logged_in.flag"


class ScraperError(RuntimeError):
    """Lỗi khi cào, message bằng tiếng Việt."""


class NotLoggedInError(ScraperError):
    pass


class CaptchaError(ScraperError):
    pass


class NoResultsError(ScraperError):
    pass


class BrowserBusyError(ScraperError):
    pass


class JobCancelled(Exception):
    pass


def login_known() -> bool:
    """Lần gần nhất có xác nhận đã đăng nhập hay chưa (không mở trình duyệt)."""
    return _LOGIN_FLAG.exists()


def parse_votes(text: str) -> int:
    m = re.search(r"([\d.,]+)\s*([万kK]?)", text or "")
    if not m:
        return 0
    try:
        num = float(m.group(1).replace(",", ""))
    except ValueError:
        return 0
    if m.group(2) == "万":
        num *= 10000
    elif m.group(2).lower() == "k":
        num *= 1000
    return int(num)


def _ensure_proactor_loop_policy() -> None:
    # uvicorn --reload trên Windows có thể đặt SelectorEventLoop, loại loop này
    # không tạo được subprocess -> Playwright báo NotImplementedError.
    if sys.platform == "win32":
        policy = asyncio.get_event_loop_policy()
        if not isinstance(policy, asyncio.WindowsProactorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def _friendly_playwright_error(e: Exception) -> ScraperError:
    msg = str(e)
    if "Executable doesn't exist" in msg or "playwright install" in msg:
        return ScraperError("Chưa cài trình duyệt cho Playwright. Chạy: playwright install chromium")
    if "Target page, context or browser has been closed" in msg or "Target closed" in msg:
        return ScraperError("Cửa sổ trình duyệt đã bị đóng giữa chừng.")
    if "ProcessSingleton" in msg or "user data directory is already in use" in msg.lower():
        return BrowserBusyError("Thư mục zhihu_profile đang được một trình duyệt khác dùng. Hãy đóng cửa sổ Chromium cũ.")
    if "net::ERR" in msg:
        return ScraperError(f"Không truy cập được Zhihu (lỗi mạng): {msg.splitlines()[0]}")
    return ScraperError(f"Lỗi trình duyệt: {msg.splitlines()[0] if msg else type(e).__name__}")


class ZhihuSession:
    """Dùng với `with ZhihuSession(...) as s:` bên trong thread worker."""

    def __init__(self, headless: bool = False, log=None, cancel_event: threading.Event | None = None):
        self.headless = headless
        self.log = log or (lambda msg, level="info": None)
        self.cancel_event = cancel_event or threading.Event()
        self._pw = None
        self.ctx = None
        self.page = None

    # ---------- vòng đời ----------
    def __enter__(self):
        if not _BROWSER_LOCK.acquire(blocking=False):
            raise BrowserBusyError("Đang có một phiên Zhihu khác chạy (đăng nhập hoặc tìm kiếm). Hãy đợi hoặc huỷ phiên đó.")
        try:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                raise ScraperError("Chưa cài Playwright. Chạy: pip install playwright && playwright install chromium")
            _ensure_proactor_loop_policy()
            config.PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            try:
                self._pw = sync_playwright().start()
                self.ctx = self._launch()
            except ScraperError:
                raise
            except Exception as e:
                raise _friendly_playwright_error(e)
            self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
            try:
                self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
            return self
        except BaseException:
            self._close()
            _BROWSER_LOCK.release()
            raise

    def _launch(self):
        """Thử lần lượt các trình duyệt trong config.BROWSER_CHANNELS."""
        last_error = None
        for channel in config.BROWSER_CHANNELS:
            try:
                ctx = self._pw.chromium.launch_persistent_context(
                    str(config.PROFILE_DIR),
                    channel=channel,
                    headless=self.headless,
                    locale="zh-CN",
                    viewport={"width": 1280, "height": 900},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    args=["--disable-blink-features=AutomationControlled"],
                )
                if channel:
                    self.log(f"Dùng trình duyệt có sẵn trên máy: {channel}")
                return ctx
            except Exception as e:
                msg = str(e)
                # Chỉ thử kênh tiếp theo khi trình duyệt chưa được cài
                if "Executable doesn't exist" in msg or "is not found" in msg or "not installed" in msg.lower():
                    last_error = e
                    continue
                raise
        raise ScraperError(
            "Không tìm thấy trình duyệt nào. Chạy: playwright install chromium "
            f"(hoặc cài Microsoft Edge / Google Chrome). Chi tiết: {str(last_error).splitlines()[0] if last_error else ''}"
        )

    def __exit__(self, exc_type, exc, tb):
        self._close()
        _BROWSER_LOCK.release()
        return False

    def _close(self):
        for obj in (self.ctx, self._pw):
            if obj is None:
                continue
            try:
                obj.close() if obj is self.ctx else obj.stop()
            except Exception:
                pass
        self.ctx = self._pw = self.page = None

    # ---------- tiện ích ----------
    def _check_cancel(self):
        if self.cancel_event.is_set():
            raise JobCancelled()

    def _sleep(self, seconds: float):
        """Ngủ nhưng vẫn phản hồi nút Huỷ."""
        end = time.monotonic() + seconds
        while True:
            self._check_cancel()
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.25, remaining))

    def is_logged_in(self) -> bool:
        try:
            cookies = self.ctx.cookies(config.ZHIHU_HOME_URL)
        except Exception:
            return False
        ok = any(c.get("name") == config.LOGIN_COOKIE_NAME and c.get("value") for c in cookies)
        if ok:
            _LOGIN_FLAG.write_text("ok", encoding="utf-8")
        elif _LOGIN_FLAG.exists():
            _LOGIN_FLAG.unlink(missing_ok=True)
        return ok

    def _page_text(self) -> str:
        try:
            return self.page.evaluate("() => document.body ? document.body.innerText.slice(0, 4000) : ''")
        except Exception:
            return ""

    def _is_captcha(self) -> bool:
        url = (self.page.url or "").lower()
        if any(m in url for m in config.CAPTCHA_URL_MARKERS):
            return True
        text = self._page_text()
        return any(m in text for m in config.CAPTCHA_TEXT_MARKERS)

    def _is_signin_page(self) -> bool:
        url = (self.page.url or "").lower()
        return any(m in url for m in config.SIGNIN_URL_MARKERS)

    # ---------- đăng nhập ----------
    def wait_for_login(self, timeout_sec: int = config.LOGIN_TIMEOUT_SEC) -> bool:
        try:
            if self.is_logged_in():
                self.log("Phiên đăng nhập Zhihu vẫn còn hiệu lực.", "success")
                return True
            self.page.goto(config.ZHIHU_SIGNIN_URL, wait_until="domcontentloaded")
            self.log(f"Hãy đăng nhập Zhihu trên cửa sổ trình duyệt vừa mở (tối đa {timeout_sec // 60} phút)...")
            end = time.monotonic() + timeout_sec
            while time.monotonic() < end:
                self._sleep(2)
                if self.is_logged_in():
                    self.log("Đăng nhập thành công, đã lưu phiên vào zhihu_profile.", "success")
                    return True
        except (JobCancelled, ScraperError):
            raise
        except Exception as e:
            raise _friendly_playwright_error(e)
        raise NotLoggedInError("Hết thời gian chờ đăng nhập Zhihu. Hãy bấm Đăng nhập Zhihu và thử lại.")

    # ---------- captcha ----------
    def _handle_captcha(self, wait_captcha: bool):
        if not self._is_captcha():
            return
        if not wait_captcha:
            raise CaptchaError(
                "Zhihu yêu cầu xác minh (captcha). Hãy giảm số lần cuộn, đợi một lúc rồi thử lại, "
                "hoặc bật tuỳ chọn 'Chờ tôi giải captcha' để giải trên cửa sổ trình duyệt."
            )
        if self.headless:
            raise CaptchaError("Gặp captcha nhưng trình duyệt đang chạy ẩn nên không giải được. Hãy tắt chế độ chạy ẩn.")
        self.log(f"Gặp captcha! Hãy giải trên cửa sổ trình duyệt (chờ tối đa {config.CAPTCHA_WAIT_SEC}s)...", "warning")
        end = time.monotonic() + config.CAPTCHA_WAIT_SEC
        while time.monotonic() < end:
            self._sleep(2)
            if not self._is_captcha():
                self.log("Đã qua captcha, tiếp tục.", "success")
                return
        raise CaptchaError("Hết thời gian chờ giải captcha.")

    # ---------- tìm kiếm ----------
    def search(self, keyword_cn: str, scrolls: int, wait_captcha: bool = False,
               on_scroll=None) -> list[dict]:
        url = config.ZHIHU_SEARCH_URL.format(query=quote(keyword_cn + config.SEARCH_SUFFIX))
        try:
            self._check_cancel()
            self.page.goto(url, wait_until="domcontentloaded")
            self.page.wait_for_timeout(config.PAGE_LOAD_WAIT_MS)

            if self._is_signin_page():
                _LOGIN_FLAG.unlink(missing_ok=True)
                raise NotLoggedInError("Zhihu yêu cầu đăng nhập. Hãy bấm 'Đăng nhập Zhihu' trước khi tìm.")
            self._handle_captcha(wait_captcha)

            for i in range(scrolls):
                self._check_cancel()
                self.page.mouse.wheel(0, config.SCROLL_PIXELS)
                self._sleep(random.uniform(*config.SCROLL_DELAY_RANGE))
                self._handle_captcha(wait_captcha)
                if on_scroll:
                    on_scroll(i + 1, scrolls)

            items = self.page.evaluate(config.EXTRACT_JS, config.SELECTORS)
        except (JobCancelled, ScraperError):
            raise
        except Exception as e:
            raise _friendly_playwright_error(e)

        seen, out = set(), []
        for it in items:
            key = it.get("link") or it.get("title")
            if key in seen:
                continue
            seen.add(key)
            it["votes"] = parse_votes(it.pop("votes_raw", ""))
            out.append(it)

        if not out:
            raise NoResultsError(
                f"Không lấy được kết quả nào cho '{keyword_cn}'. Có thể Zhihu đã đổi giao diện, "
                "hãy kiểm tra SELECTORS trong backend/zhihu/config.py."
            )
        return out

    # ---------- lấy nội dung chi tiết bài viết ----------
    def fetch_content(self, target_url: str, wait_captcha: bool = False) -> dict:
        """Tải trang bài viết hoặc câu trả lời Zhihu và trích xuất nội dung đầy đủ."""
        try:
            self._check_cancel()
            self.page.goto(target_url, wait_until="domcontentloaded")
            self.page.wait_for_timeout(config.PAGE_LOAD_WAIT_MS)

            if self._is_signin_page():
                _LOGIN_FLAG.unlink(missing_ok=True)
                raise NotLoggedInError("Zhihu yêu cầu đăng nhập. Hãy bấm 'Đăng nhập Zhihu' trước.")
            self._handle_captcha(wait_captcha)

            try:
                self.page.wait_for_selector(".RichText, .Post-RichText, .QuestionAnswer-content", timeout=6000)
            except Exception:
                pass

            # Bấm nút 'Mở rộng' nếu bài viết bị thu gọn
            try:
                self.page.evaluate("""() => {
                    document.querySelectorAll('.Button.ContentItem-expandButton, .QuestionRich-expandButton').forEach(btn => btn.click());
                }""")
                self.page.wait_for_timeout(1000)
            except Exception:
                pass

            data = self.page.evaluate("""() => {
                const titleEl = document.querySelector('h1.QuestionHeader-title, h1.Post-Title, h1, .ContentItem-title');
                const title = titleEl ? titleEl.innerText.trim() : '';

                const container = document.querySelector('.QuestionAnswer-content .RichText, .Post-RichText, .RichContent-inner, .RichText');
                if (!container) return { title, text: '' };

                const ps = Array.from(container.querySelectorAll('p, div.RichText-paragraph, blockquote'));
                let text = '';
                if (ps.length > 0) {
                    text = ps.map(p => p.innerText.trim()).filter(Boolean).join('\\n\\n');
                } else {
                    text = container.innerText.trim();
                }

                return { title, text };
            }""")

            title = data.get("title", "")
            text = data.get("text", "")
            if not text:
                text = self._page_text()

            if "您当前请求存在异常" in text or "40362" in text or "安全验证" in text:
                raise CaptchaError("Zhihu tạm thời hạn chế truy cập bài viết này. Hãy mở lại trình duyệt đăng nhập hoặc thử lại sau ít phút.")

            return {
                "title": title,
                "content": text,
                "url": target_url,
                "word_count": len(text)
            }
        except (JobCancelled, ScraperError):
            raise
        except Exception as e:
            raise _friendly_playwright_error(e)

