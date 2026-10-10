import os
import random
import time
from pathlib import Path

import requests
import streamlit as st


# ==============================
# SkyeChat — cấu hình
# ==============================
APP_DIR = Path(__file__).resolve().parent
logo_file = next(
    (APP_DIR / name for name in ("logo.png", "logo.jpg", "Logo.png", "Logo.jpg") if (APP_DIR / name).is_file()),
    None,
)
st.set_page_config(
    page_title="SkyeChat | Góc nhỏ để sẻ chia",
    page_icon=str(logo_file) if logo_file else "☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-3.6-flash"
MAX_HISTORY_MESSAGES = 24
MAX_RETRIES = 3


def get_secret(name, default=None):
    """Read a Streamlit secret first, then an environment variable."""
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, default)


GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
PRIMARY_MODEL = get_secret("GEMINI_MODEL", DEFAULT_MODEL)

if not GEMINI_API_KEY:
    st.error(
        "Chưa tìm thấy `GEMINI_API_KEY`. Hãy thêm khóa vào Streamlit Secrets "
        "hoặc biến môi trường trước khi chạy SkyeChat."
    )
    st.stop()


# ==============================
# Nhận diện thương hiệu SkyeChat
# ==============================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Nunito:wght@500;600;700;800;900&display=swap');

    :root {
      --sky-ink: #263251;
      --sky-muted: #74809a;
      --sky-blue: #6b8df2;
      --sky-lilac: #a58af6;
      --sky-mint: #c9f2e7;
      --sky-peach: #ffe2cc;
      --sky-paper: #f7f8ff;
    }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp {
      color: var(--sky-ink);
      background:
        radial-gradient(ellipse at 8% 0%, rgba(202,220,255,.52), transparent 32%),
        radial-gradient(ellipse at 96% 12%, rgba(232,216,255,.48), transparent 30%),
        #f8f9ff;
    }
    [data-testid="stHeader"] { background: rgba(248,249,255,.78); }
    [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #f0f4ff 0%, #f7f2ff 58%, #f4fbfa 100%);
      border-right: 1px solid rgba(121,142,203,.14);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #56617d; }
    h1, h2, h3 { font-family: 'Nunito', sans-serif !important; color: var(--sky-ink); }
    h1 { letter-spacing: -1.2px; }
    .hero {
      position: relative; overflow: hidden;
      padding: 1.65rem 2rem 1.55rem;
      border: 1px solid rgba(255,255,255,.9);
      border-radius: 26px;
      background: linear-gradient(115deg, rgba(224,235,255,.96), rgba(242,231,255,.94) 58%, rgba(224,248,241,.9));
      box-shadow: 0 16px 45px rgba(77,91,145,.09);
      margin: .35rem 0 1.2rem;
      animation: hero-arrive .65s ease-out both;
    }
    .hero:after {
      content: '☁'; position: absolute; right: 7%; top: -33px;
      color: rgba(255,255,255,.58); font-size: 150px; line-height: 1;
      transform: rotate(-9deg); pointer-events: none;
      filter: drop-shadow(0 10px 18px rgba(255,255,255,.28));
      animation: cloud-drift 7s ease-in-out infinite;
    }
    .hero:before {
      content: ''; position: absolute; width: 210px; height: 210px; right: 4%; top: -118px;
      border-radius: 50%; background: rgba(255,255,255,.24); filter: blur(2px);
      pointer-events: none;
    }
    @keyframes hero-arrive { from { opacity: 0; transform: translateY(9px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes cloud-drift { 0%, 100% { translate: 0 0; } 50% { translate: 0 8px; } }
    .hero-eyebrow { color: #6679b1; font-size: .78rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
    .hero-title { color: #293658; font: 900 2.25rem/1.12 'Nunito', sans-serif; margin: .25rem 0 .45rem; }
    .hero-copy { color: #626e8c; max-width: 660px; font-size: 1rem; margin: 0; }
    .welcome-card {
      border: 1px solid rgba(151,167,220,.18); border-radius: 22px;
      padding: 1.25rem 1.4rem; margin: .8rem 0 1.25rem;
      background: rgba(255,255,255,.78); box-shadow: 0 10px 30px rgba(66,82,133,.055);
      animation: hero-arrive .75s .08s ease-out both;
    }
    .welcome-card strong { color: #536fc5; }
    .soft-note { color: #7b86a0; font-size: .88rem; }
    .sidebar-brand {
      padding: 1rem; margin: .25rem 0 1.2rem; border-radius: 20px;
      background: linear-gradient(135deg, #dfeaff, #efe4ff 65%, #ddf6ed);
      text-align: center; color: #46577e;
    }
    .sidebar-brand .cloud { font-size: 2.2rem; }
    .sidebar-brand strong { display: block; font: 900 1.25rem 'Nunito', sans-serif; color: #2e3b61; }
    .sidebar-brand span { font-size: .82rem; }
    div[data-testid="stChatMessage"] {
      border: 1px solid rgba(147,161,207,.13); border-radius: 20px;
      padding: .85rem 1rem; background: rgba(255,255,255,.75);
      box-shadow: 0 8px 24px rgba(54,72,126,.045); margin-bottom: .85rem;
      transition: box-shadow .2s ease, transform .2s ease;
    }
    div[data-testid="stChatMessage"]:hover { box-shadow: 0 11px 28px rgba(54,72,126,.075); transform: translateY(-1px); }
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
      background: linear-gradient(115deg, rgba(224,235,255,.96), rgba(242,231,255,.92));
      border-color: rgba(144,164,231,.2);
    }
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
      background: linear-gradient(115deg, rgba(255,255,255,.96), rgba(239,251,247,.94));
      border-color: rgba(160,213,197,.25);
    }
    [data-testid="stChatInput"] textarea {
      border-radius: 18px !important; border: 1px solid #dce3f7 !important;
      background: rgba(255,255,255,.92) !important;
      box-shadow: 0 8px 24px rgba(69,88,145,.055);
      transition: border-color .2s ease, box-shadow .2s ease;
    }
    [data-testid="stChatInput"] textarea:focus { border-color: #92aaf5 !important; box-shadow: 0 0 0 3px rgba(107,141,242,.13) !important; }
    .stButton button {
      border-radius: 13px; border: 1px solid #d8def2; color: #5369aa;
      background: rgba(255,255,255,.76); font-weight: 700;
      transition: all .18s ease;
    }
    .stButton button:hover { border-color: #aab9f2; color: #405aa7; background: #f3f5ff; transform: translateY(-1px); box-shadow: 0 7px 16px rgba(80,102,174,.12); }
    [data-testid="stChatInput"] button {
      border: 0 !important; border-radius: 13px !important; color: white !important;
      background: linear-gradient(135deg, #7897f5, #a58af6) !important;
      box-shadow: 0 5px 14px rgba(107,141,242,.26);
      transition: transform .18s ease, box-shadow .18s ease;
    }
    [data-testid="stChatInput"] button:hover { transform: translateY(-1px); box-shadow: 0 8px 18px rgba(107,141,242,.34); }
    div[data-testid="stAlert"] { border-radius: 15px; }
    .footer { color: #8b94aa; text-align: center; font-size: .82rem; padding: 1.2rem 0 .3rem; }
    @media (prefers-reduced-motion: reduce) {
      *, *:before, *:after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; transition-duration: .01ms !important; }
    }
    @media (max-width: 700px) {
      .hero { padding: 1.3rem; border-radius: 20px; }
      .hero-title { font-size: 1.9rem; }
      .hero:after { right: -5%; font-size: 110px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================
# System prompt
# ==============================
SYSTEM_PROMPT_VI = """
Bạn là SkyeChat, một trợ lý AI thân thiện, cởi mở và không phán xét, chuyên
lắng nghe và hỗ trợ sơ cứu tâm lý học đường cho học sinh, sinh viên.
Hãy phản hồi bằng tiếng Việt ấm áp, ngắn gọn, chu đáo; hỏi từng câu nhẹ nhàng
và không chẩn đoán bệnh hay thay thế chuyên gia. Nếu người dùng có nguy cơ bị
tổn thương ngay lúc này, hãy khuyến khích họ đến bên một người lớn đáng tin,
người thân hoặc dịch vụ khẩn cấp tại địa phương. Với trẻ em ở Việt Nam, có thể
liên hệ Tổng đài Quốc gia Bảo vệ Trẻ em 111.
""".strip()

SYSTEM_PROMPT_EN = """
You are SkyeChat, a friendly, open, non-judgmental assistant for school
psychological first aid. Listen with warmth, respond concisely, ask gentle
questions one at a time, and do not diagnose or replace a professional. If
someone may be in immediate danger, encourage them to reach a trusted adult,
family member, or local emergency service now.
""".strip()


# ==============================
# Session state
# ==============================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "nickname" not in st.session_state:
    st.session_state.nickname = "Bạn"


def api_error_message(response):
    try:
        data = response.json()
    except ValueError:
        return response.text[:500] or "Không đọc được phản hồi từ máy chủ."
    return data.get("error", {}).get("message", "Lỗi không xác định từ Gemini API.")


def generate_reply(history, system_prompt):
    """Call Gemini with bounded exponential backoff and one overload fallback."""
    contents = []
    for msg in history[-MAX_HISTORY_MESSAGES:]:
        contents.append(
            {
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["content"]}],
            }
        )

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }
    models = [PRIMARY_MODEL]
    if FALLBACK_MODEL != PRIMARY_MODEL:
        models.append(FALLBACK_MODEL)

    last_response = None
    last_exception = None
    for model_index, model in enumerate(models):
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    f"{API_BASE}/{model}:generateContent",
                    json=payload,
                    headers=headers,
                    timeout=(10, 60),
                )
                last_response = response
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ValueError("Gemini không trả về nội dung. Hãy thử gửi lại tin nhắn.")
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "\n".join(part.get("text", "") for part in parts if part.get("text"))
                    if not text.strip():
                        raise ValueError("Gemini chưa tạo được câu trả lời. Bạn thử diễn đạt lại nhé.")
                    return text.strip()

                if response.status_code not in (408, 429, 500, 502, 503, 504):
                    raise RuntimeError(f"API ({response.status_code}): {api_error_message(response)}")

                if attempt < MAX_RETRIES - 1:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = min(float(retry_after), 12.0) if retry_after else min(1.5 * (2**attempt), 8.0)
                    except ValueError:
                        delay = min(1.5 * (2**attempt), 8.0)
                    time.sleep(delay + random.uniform(0, 0.6))

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exception = exc
                if attempt < MAX_RETRIES - 1:
                    time.sleep(min(1.5 * (2**attempt), 8.0) + random.uniform(0, 0.6))
            except (ValueError, RuntimeError):
                raise

        # If the primary model stayed overloaded, give the stable fallback a turn.
        if model_index == 0 and len(models) > 1:
            continue

    if last_response is not None:
        status = last_response.status_code
        message = api_error_message(last_response)
        if status in (429, 503, 504):
            raise RuntimeError(
                "Các model Gemini đang quá tải hoặc giới hạn lượt gọi đã chạm ngưỡng "
                f"(HTTP {status}). Mình đã thử lại và chuyển model dự phòng nhưng chưa thành công. "
                "Bạn đợi một chút rồi gửi lại nhé."
            )
        raise RuntimeError(f"Gemini API ({status}): {message}")
    raise RuntimeError(f"Không kết nối được Gemini API: {last_exception or 'lỗi mạng không xác định'}")


# ==============================
# Sidebar
# ==============================
with st.sidebar:
    if logo_file:
        st.image(str(logo_file), width=132)
    st.markdown(
        """
        <div class="sidebar-brand">
          <div class="cloud">☁️</div>
          <strong>SkyeChat</strong>
          <span>Một góc nhỏ để sẻ chia</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("Cài đặt của bạn")

    nickname_input = st.text_input("Biệt danh", value=st.session_state.nickname, max_chars=32)
    if nickname_input.strip():
        st.session_state.nickname = nickname_input.strip()

    st.success(f"👋 Chào {st.session_state.nickname}!")
    lang = st.radio("Ngôn ngữ / Language", ["Tiếng Việt 🇻🇳", "English 🇬🇧"], label_visibility="visible")
    is_vi = lang.startswith("Tiếng Việt")

    st.divider()
    st.markdown("**Nhà phát triển:** ThanhAI")
    if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.warning(
        "**Lưu ý an toàn**\n\nSkyeChat hỗ trợ lắng nghe và sơ cứu tâm lý ban đầu; không thay thế chuyên gia. "
        "Nếu bạn hoặc ai đó đang gặp nguy hiểm, hãy báo ngay cho người lớn đáng tin. "
        "Trẻ em tại Việt Nam có thể gọi Tổng đài Bảo vệ Trẻ em **111**.",
        icon="🫶",
    )
    st.caption("Cuộc trò chuyện được lưu trong phiên trình duyệt hiện tại.")


# ==============================
# Header và hội thoại
# ==============================
st.markdown(
    """
    <section class="hero">
      <div class="hero-eyebrow">Không gian an toàn để sẻ chia</div>
      <div class="hero-title">Chào bạn, mình là SkyeChat ☁️</div>
      <p class="hero-copy">Bạn có thể bắt đầu từ bất cứ điều gì đang ở trong lòng. Mình sẽ lắng nghe, không phán xét.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    if is_vi:
        st.markdown(
            """
            <div class="welcome-card">
              <strong>Đây là không gian của bạn.</strong><br>
              Bạn không cần phải tìm đúng từ ngữ. Hãy kể một điều nhỏ đang khiến bạn bận tâm,
              hoặc chỉ cần nói hôm nay bạn cảm thấy thế nào.
              <div class="soft-note" style="margin-top:.7rem">Mình ở đây để lắng nghe, từng chút một.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="welcome-card">
              <strong>This is your space.</strong><br>
              You do not need to find the perfect words. Share one small thing on your mind,
              or simply tell me how today feels.
              <div class="soft-note" style="margin-top:.7rem">I’m here to listen, one step at a time.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

placeholder = "Hãy chia sẻ với SkyeChat..." if is_vi else "Share your thoughts with SkyeChat..."
if prompt := st.chat_input(placeholder, max_chars=8000):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("SkyeChat đang lắng nghe..." if is_vi else "SkyeChat is listening..."):
            try:
                system_prompt = SYSTEM_PROMPT_VI if is_vi else SYSTEM_PROMPT_EN
                bot_reply = generate_reply(st.session_state.messages, system_prompt)
                st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            except Exception as exc:
                st.error(f"Không gửi được tin nhắn: {exc}")

st.markdown(
    '<div class="footer">SkyeChat · Lắng nghe bằng sự tử tế · Phát triển bởi ThanhAI</div>',
    unsafe_allow_html=True,
)
