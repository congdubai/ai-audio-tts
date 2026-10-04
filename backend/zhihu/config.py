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
    "card": ".SearchResult-Card, .List-item, .ContentItem, [class*='SearchResult-Card']",
    "title": "h2 a, .ContentItem-title a, a[data-za-detail-view-element_name='Title']",
    "body": ".RichContent-inner, .RichText, .RichContent",
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
      title: a ? a.innerText.trim() : (c.querySelector('h2') ? c.querySelector('h2').innerText.trim() : ''),
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
    # --- Ngôn tình & Tình cảm ---
    "ngôn tình": "言情",
    "tình cảm": "情感",
    "tổng tài": "霸道总裁",
    "tổng tài cô gái bình thường": "总裁平民女",
    "cưới trước yêu sau": "先婚后爱",
    "hợp đồng hôn nhân": "契约婚姻",
    "yêu thầm": "暗恋",
    "ngược tình": "虐恋",
    "ngược luyến": "虐恋",
    "chữa lành": "治愈",
    "he": "甜文",
    "be": "虐文",

    # --- Gia đình & Hối hận (Audiobook drama) ---
    "gia đình hối hận": "全家后悔",
    "sau khi nữ chính rời đi cả nhà mới hối hận": "离开后全家后悔",
    "con gái thật con gái nuôi": "真假千金",
    "thiên kim thật giả": "真假千金",
    "nhận nhầm con": "认错孩子",
    "trọng nam khinh nữ": "重男轻女",
    "cả nhà thiên vị em gái": "全家偏心",
    "đuổi con ruột": "赶走亲女儿",
    "đuổi con ruột sau đó tìm cách níu kéo": "赶走亲生女儿后挽回",

    # --- Trọng sinh / Sống lại ---
    "trọng sinh": "重生",
    "sống lại": "重生",
    "chết rồi quay về quá khứ": "重生过去",
    "trọng sinh trả thù": "重生复仇",
    "trọng sinh thay đổi cuộc đời": "重生逆袭",
    "trọng sinh sau khi bị gia đình phản bội": "重生背叛",
    "biết trước tương lai và thay đổi số phận": "预知未来逆风翻盘",

    # --- Xuyên sách & Xuyên không ---
    "xuyên sách": "穿书",
    "xuyên không": "穿越",
    "xuyên thành nữ phụ": "穿成女配",
    "xuyên thành nhân vật phản diện": "穿成反派",
    "xuyên thành người bị cả nhà ghét": "穿成全网黑",
    "xuyên vào thế giới cổ đại": "穿越古代",

    # --- Cổ đại & Cung đấu ---
    "cổ đại": "古代",
    "cung đấu": "宫斗",
    "trạch đấu": "宅斗",
    "cung đình": "宫廷",
    "hoàng đế hoàng hậu": "帝后",
    "tranh sủng": "争宠",
    "hậu cung": "后宫",
    "nữ chính báo thù": "女主复仇",
    "nữ cường": "大女主",
    "làm hoàng hậu phi tần": "当后宫主子",

    # --- Hào môn & Gia tộc ---
    "hào môn": "豪门",
    "gia tộc": "世家",
    "con nhà giàu bị thất lạc": "豪门流落千金",
    "gia tộc quyền thế": "权贵世家",
    "tranh đoạt tài sản": "争夺财产",
    "hôn ước": "婚约",
    "anh em trong gia đình đấu đá": "豪门内斗",
    "đại gia ẩn danh": "马甲文",

    # --- Sảng văn & Trả thù ---
    "sảng văn": "爽文",
    "vả mặt": "打脸",
    "vả mặt liên tục": "疯狂打脸",
    "nữ chính bị coi thường": "女主被看不起",
    "lật ngược tình thế": "逆袭",
    "bị phản bội quay lại trả thù": "背叛复仇",
    "giả yếu để phản công": "扮猪吃老虎",
    "người từng coi thường nữ chính phải hối hận": "打脸前任与仇人",

    # --- Đô thị & Hiện đại ---
    "đô thị": "都市",
    "khởi nghiệp": "创业",
    "làm giàu": "致富",
    "thương chiến": "商战",
    "nhân vật chính từ nghèo khó trở thành thành đạt": "穷小子逆袭",

    # --- Huyền huyễn & Tu tiên ---
    "tu tiên": "修仙",
    "huyền huyễn": "玄幻",
    "tiên hiệp": "仙侠",
    "kiếm hiệp": "武侠",
    "phế vật cường giả": "废柴逆袭",
    "tông môn": "宗门",
    "phiêu lưu": "冒险",

    # --- Hệ thống ---
    "hệ thống": "系统",
    "hệ thống làm giàu": "致富系统",
    "hệ thống nhiệm vụ": "任务系统",
    "hệ thống phản diện": "反派系统",
    "hệ thống điểm danh": "签到系统",
    "hệ thống giúp thay đổi số phận": "系统改变命运",

    # --- Kinh dị, Linh dị & Trinh thám ---
    "kinh dị": "恐怖",
    "linh dị": "灵异",
    "đô thị linh dị": "都市灵异",
    "ma quỷ": "鬼怪",
    "nhà hoang": "废弃凶宅",
    "trường học": "校园怪谈",
    "điều tra vụ án kỳ bí": "悬疑侦探",
    "trinh thám": "推理",
    "phá án": "破案",
    "án mạng": "命案",
    "thám tử": "侦探",
    "bí mật gia đình": "家族秘密",

    # --- Mạt thế ---
    "mạt thế": "末世",
    "tận thế": "末日",
    "zombie": "丧尸",
    "sinh tồn": "生存",
    "tích trữ vật tư": "囤物资",
    "không gian tùy thân": "随身空间",
    "trọng sinh trước ngày tận thế": "末世重生",

    # --- Điền văn & Chữa lành ---
    "điền văn": "种田文",
    "làm ruộng": "种田",
    "cuộc sống bình dị": "慢生活",
    "xây dựng gia đình": "家常理短",
    "làm giàu từ từ": "白手起家",
    "tình cảm nhẹ nhàng": "甜宠",
    "đam mỹ": "耽美",
    "quân sự": "军事",
    "lịch sử": "历史",
    "vô hạn lưu": "无限流",
    "hài hước": "搞笑",
}
