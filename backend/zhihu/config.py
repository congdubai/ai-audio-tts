"""Cấu hình tập trung cho chức năng tìm truyện Zhihu.

Zhihu đổi giao diện khá thường xuyên. Khi tìm kiếm trả về 0 kết quả dù trang
vẫn hiển thị bình thường, hãy mở DevTools trên zhihu.com và sửa các selector
trong mục "SELECTOR ZHIHU" bên dưới. Không cần sửa file nào khác.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ==================== Ollama ====================
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"
OLLAMA_DEFAULT_MODEL = "qwen2.5:7b"
OLLAMA_TIMEOUT = 300  # giây
OLLAMA_TEMPERATURE = 0.2
MAX_TRANSLATE_CHARS = 1500

# ==================== Trình duyệt / phiên đăng nhập ====================
PROFILE_DIR = BASE_DIR / "zhihu_profile"      # lưu cookie đăng nhập (đã gitignore)
OUTPUTS_DIR = BASE_DIR / "zhihu_outputs"      # file CSV/JSON xuất ra
LOGIN_COOKIE_NAME = "z_c0"                   # cookie Zhihu đặt khi đã đăng nhập
LOGIN_TIMEOUT_SEC = 300                      # thời gian chờ bạn đăng nhập
CAPTCHA_WAIT_SEC = 120                       # thời gian chờ bạn tự giải captcha (nếu bật)
# Thứ tự trình duyệt thử dùng: None = Chromium của Playwright,
# "msedge"/"chrome" = trình duyệt đã cài sẵn trên máy (dùng khi chưa tải được Chromium)
BROWSER_CHANNELS = (None, "msedge", "chrome")

ZHIHU_HOME_URL = "https://www.zhihu.com"
ZHIHU_SIGNIN_URL = "https://www.zhihu.com/signin"
ZHIHU_SEARCH_URL = "https://www.zhihu.com/search?type=content&q={query}"
SEARCH_SUFFIX = " 小说推荐"                    # nối vào từ khoá tiếng Trung

# ==================== Tốc độ (giữ chậm để tránh bị chặn) ====================
PAGE_LOAD_WAIT_MS = 3000
SCROLL_PIXELS = 4000
SCROLL_DELAY_RANGE = (2.5, 5.0)     # giây, ngẫu nhiên giữa mỗi lần cuộn
GENRE_DELAY_RANGE = (4.0, 8.0)      # giây, nghỉ giữa các thể loại
MAX_SCROLLS = 30

# ==================== SELECTOR ZHIHU (sửa tại đây khi Zhihu đổi giao diện) ====================
SELECTORS = {
    "card": ".SearchResult-Card, .List-item",
    "title": "h2 a, .ContentItem-title a",
    "body": ".RichContent-inner, .RichText",
    "vote": ".VoteButton, [class*='Vote']",
}

# Dấu hiệu bị captcha / kiểm tra bảo mật
CAPTCHA_URL_MARKERS = ("unhuman", "captcha")
CAPTCHA_TEXT_MARKERS = ("安全验证", "验证码", "请完成验证")
# Dấu hiệu bị đẩy về trang đăng nhập
SIGNIN_URL_MARKERS = ("/signin", "/signup")

EXTRACT_JS = """
(sel) => {
  const cards = document.querySelectorAll(sel.card);
  return Array.from(cards).map(c => {
    const a = c.querySelector(sel.title);
    const body = c.querySelector(sel.body);
    const vote = c.querySelector(sel.vote);
    return {
      title: a ? a.innerText.trim() : '',
      link: a ? a.href : '',
      excerpt: body ? body.innerText.trim() : '',
      votes_raw: vote ? vote.innerText.trim() : ''
    };
  }).filter(x => x.title || x.excerpt);
}
"""

# ==================== Bảng ánh xạ thể loại Việt -> Trung ====================
# Viết có dấu bình thường (dùng làm gợi ý trên giao diện). Khi tra cứu, cả khoá
# và từ người dùng nhập đều được bỏ dấu + chữ thường nên "Tien Hiep" vẫn khớp.
GENRE_MAP = {
    "tiên hiệp": "仙侠",
    "huyền huyễn": "玄幻",
    "xuyên không": "穿越",
    "trọng sinh": "重生",
    "ngược luyến": "虐恋",
    "ngôn tình": "言情",
    "đô thị": "都市",
    "kiếm hiệp": "武侠",
    "khoa huyễn": "科幻",
    "huyền nghi": "悬疑",
    "trinh thám": "推理",
    "hệ thống": "系统",
    "cung đấu": "宫斗",
    "đam mỹ": "耽美",
    "quân sự": "军事",
    "lịch sử": "历史",
    "vô hạn lưu": "无限流",
    "mạt thế": "末世",
    "sảng văn": "爽文",
    "hài hước": "搞笑",
}
