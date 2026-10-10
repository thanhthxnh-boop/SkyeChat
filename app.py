import os
import random
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

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


# ==============================
# Nhận diện thương hiệu SkyeChat
# ==============================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Nunito:wght@500;600;700;800;900&display=swap');

    :root {
      --primary-color: #4f9b6b;
      --sky-ink: #24443a;
      --sky-muted: #71877b;
      --sky-blue: #438d68;
      --sky-lilac: #83bd98;
      --sky-mint: #d9f1e1;
      --sky-peach: #f6e7cf;
      --sky-paper: #f5faf6;
    }
    input[type="radio"] { accent-color: #4f9b6b; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp {
      color: var(--sky-ink);
      background:
        radial-gradient(ellipse at 8% 0%, rgba(194,232,204,.55), transparent 32%),
        radial-gradient(ellipse at 96% 12%, rgba(217,241,225,.62), transparent 30%),
        #f7faf6;
    }
    [data-testid="stHeader"] { background: rgba(247,250,246,.82); }
    [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #edf7ef 0%, #f2f8ef 58%, #edf8f3 100%);
      border-right: 1px solid rgba(101,151,117,.16);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #526b5d; }
    h1, h2, h3 { font-family: 'Nunito', sans-serif !important; color: var(--sky-ink); }
    h1 { letter-spacing: -1.2px; }
    .hero {
      position: relative; overflow: hidden;
      padding: 1.65rem 2rem 1.55rem;
      border: 1px solid rgba(255,255,255,.9);
      border-radius: 26px;
      background: linear-gradient(115deg, rgba(220,241,222,.98), rgba(232,244,220,.96) 58%, rgba(218,243,232,.94));
      box-shadow: 0 16px 45px rgba(62,112,78,.10);
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
    .hero-eyebrow { color: #4e8061; font-size: .78rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
    .hero-title { color: #29483a; font: 900 2.25rem/1.12 'Nunito', sans-serif; margin: .25rem 0 .45rem; }
    .hero-copy { color: #5d7666; max-width: 660px; font-size: 1rem; margin: 0; }
    .welcome-card {
      border: 1px solid rgba(133,177,143,.22); border-radius: 22px;
      padding: 1.25rem 1.4rem; margin: .8rem 0 1.25rem;
      background: rgba(255,255,255,.82); box-shadow: 0 10px 30px rgba(62,112,78,.07);
      animation: hero-arrive .75s .08s ease-out both;
    }
    .welcome-card strong { color: #43805d; }
    .soft-note { color: #71877b; font-size: .88rem; }
    .diary-intro {
      border: 1px solid rgba(139,192,151,.32); border-radius: 20px;
      padding: 1rem 1.2rem; margin: .7rem 0 1rem;
      background: linear-gradient(115deg, rgba(255,255,255,.9), rgba(226,245,228,.84));
      color: #536c5b;
    }
    .sidebar-brand {
      padding: 1rem; margin: .25rem 0 1.2rem; border-radius: 20px;
      background: linear-gradient(135deg, #dcefdc, #e8f2d9 65%, #d9f0e4);
      text-align: center; color: #486450;
    }
    .sidebar-brand .cloud { font-size: 2.2rem; }
    .sidebar-brand strong { display: block; font: 900 1.25rem 'Nunito', sans-serif; color: #29483a; }
    .sidebar-brand span { font-size: .82rem; }
    div[data-testid="stChatMessage"] {
      border: 1px solid rgba(128,163,137,.2); border-radius: 20px;
      padding: .85rem 1rem; background: rgba(255,255,255,.75);
      box-shadow: 0 8px 24px rgba(56,99,66,.055); margin-bottom: .85rem;
      transition: box-shadow .2s ease, transform .2s ease;
    }
    div[data-testid="stChatMessage"]:hover { box-shadow: 0 11px 28px rgba(56,99,66,.09); transform: translateY(-1px); }
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
      background: linear-gradient(115deg, rgba(224,242,222,.98), rgba(235,244,218,.94));
      border-color: rgba(132,176,125,.28);
    }
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
      background: linear-gradient(115deg, rgba(255,255,255,.97), rgba(230,246,235,.95));
      border-color: rgba(145,193,156,.3);
    }
    [data-testid="stChatInput"] textarea {
      border-radius: 18px !important; border: 1px solid #d3e5d5 !important;
      background: rgba(255,255,255,.92) !important;
      box-shadow: 0 8px 24px rgba(62,112,78,.07);
      transition: border-color .2s ease, box-shadow .2s ease;
    }
    [data-testid="stChatInput"] textarea:focus { border-color: #80b48c !important; box-shadow: 0 0 0 3px rgba(75,143,94,.14) !important; }
    .stButton button {
      border-radius: 13px; border: 1px solid #d3e5d5; color: #426b50;
      background: rgba(255,255,255,.76); font-weight: 700;
      transition: all .18s ease;
    }
    .stButton button:hover { border-color: #91bd99; color: #315d41; background: #f0f8ef; transform: translateY(-1px); box-shadow: 0 7px 16px rgba(67,119,76,.14); }
    [data-testid="stChatInput"] button {
      border: 0 !important; border-radius: 13px !important; color: white !important;
      background: linear-gradient(135deg, #4f9b6b, #83bd8c) !important;
      box-shadow: 0 5px 14px rgba(70,143,88,.28);
      transition: transform .18s ease, box-shadow .18s ease;
    }
    [data-testid="stChatInput"] button:hover { transform: translateY(-1px); box-shadow: 0 8px 18px rgba(70,143,88,.36); }
    div[data-testid="stAlert"] { border-radius: 15px; }
    .footer { color: #7d9181; text-align: center; font-size: .82rem; padding: 1.2rem 0 .3rem; }
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
if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []


def api_error_message(response):
    try:
        data = response.json()
    except ValueError:
        return response.text[:500] or "Không đọc được phản hồi từ máy chủ."
    return data.get("error", {}).get("message", "Lỗi không xác định từ Gemini API.")


def generate_reply(history, system_prompt):
    """Call Gemini with bounded exponential backoff and one overload fallback."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "Chưa cấu hình GEMINI_API_KEY. Hãy thêm khóa vào .streamlit/secrets.toml để dùng tính năng trò chuyện."
        )

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
    page_mode = st.radio(
        "Mục bạn muốn mở" if is_vi else "Choose a space",
        ["💬 Trò chuyện", "📔 Nhật ký"] if is_vi else ["💬 Chat", "📔 Journal"],
        key="page_mode",
    )
    is_diary = "Nhật ký" in page_mode or "Journal" in page_mode
    if not GEMINI_API_KEY and not is_diary:
        st.info("Thêm `GEMINI_API_KEY` vào `.streamlit/secrets.toml` để bật trò chuyện với AI.")

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


if is_diary:
    st.markdown(
        """
        <style>
        [data-testid="stForm"] {
          background: linear-gradient(145deg, #f3faf2, #e8f5e9);
          border: 1px solid #cfe5d0;
          border-radius: 22px;
          padding: 1.1rem 1.2rem 1.2rem;
          box-shadow: 0 12px 28px rgba(57, 111, 69, .07);
        }
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
          background: #fbfefb !important;
          border: 1px solid #c9dfcb !important;
          border-radius: 13px !important;
        }
        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {
          border-color: #72a97c !important;
          box-shadow: 0 0 0 3px rgba(79, 155, 107, .13) !important;
        }
        [data-testid="stSelectSlider"] [role="slider"] {
          background: #438d5c !important;
          border-color: #438d5c !important;
        }
        [data-testid="stDownloadButton"] button,
        [data-testid="stFormSubmitButton"] button {
          color: #fff !important;
          border: 1px solid #3f8052 !important;
          border-radius: 13px !important;
          background: linear-gradient(135deg, #438d5c, #72ad78) !important;
          box-shadow: 0 6px 15px rgba(63, 128, 82, .18);
          transition: transform .18s ease, box-shadow .18s ease;
        }
        [data-testid="stDownloadButton"] button:hover,
        [data-testid="stFormSubmitButton"] button:hover {
          color: #fff !important;
          border-color: #2f7045 !important;
          background: linear-gradient(135deg, #367c50, #5b9b66) !important;
          transform: translateY(-1px);
          box-shadow: 0 9px 20px rgba(63, 128, 82, .24);
        }
        [data-testid="stExpander"] {
          border: 1px solid #d4e7d4 !important;
          border-radius: 16px !important;
          background: rgba(247, 252, 246, .92) !important;
        }
        [data-testid="stExpander"] summary:hover { background: #edf6eb !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==============================
# Header và hội thoại
# ==============================
if is_diary:
    if is_vi:
        st.markdown(
            """
            <section class="hero">
              <div class="hero-eyebrow">Một khoảng lặng dành cho bạn</div>
              <div class="hero-title">Nhật ký của bạn 📔</div>
              <p class="hero-copy">Ghi lại cảm xúc và những điều bạn muốn nhớ, theo cách của riêng mình.</p>
            </section>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="diary-intro">Không cần viết hay hoặc viết dài. Một vài dòng thật lòng cũng đủ để bắt đầu.</div>',
            unsafe_allow_html=True,
        )
        title_label, entry_label, mood_label = "Tiêu đề (không bắt buộc)", "Hôm nay bạn muốn ghi lại điều gì?", "Tâm trạng hôm nay"
        title_placeholder, entry_placeholder = "Ví dụ: Một ngày nhiều suy nghĩ", "Bạn có thể viết về điều đã xảy ra, cảm xúc của mình, hoặc điều bạn mong muốn..."
        save_label, empty_error = "Lưu trang nhật ký", "Hãy viết vài dòng trước khi lưu nhé."
        history_label, download_label, delete_label = "Những trang đã viết", "⬇️ Tải nhật ký về máy", "Xóa trang này"
        empty_label, privacy_label = "Bạn chưa viết trang nhật ký nào. Khi sẵn sàng, hãy bắt đầu bằng vài dòng về hôm nay.", "Nhật ký chỉ được giữ trong phiên trình duyệt hiện tại. Hãy tải bản sao về máy nếu muốn giữ lại sau khi đóng hoặc tải lại trang."
        mood_options = ["😟 Rất tệ", "🙁 Không ổn", "😐 Bình thường", "🙂 Ổn", "😊 Tốt"]
    else:
        st.markdown(
            """
            <section class="hero">
              <div class="hero-eyebrow">A quiet moment for you</div>
              <div class="hero-title">Your journal 📔</div>
              <p class="hero-copy">Write down your feelings and the moments you want to remember, in your own way.</p>
            </section>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="diary-intro">You do not need to write something polished or long. A few honest lines are enough.</div>',
            unsafe_allow_html=True,
        )
        title_label, entry_label, mood_label = "Title (optional)", "What would you like to write about today?", "How are you feeling today?"
        title_placeholder, entry_placeholder = "Example: A day with a lot on my mind", "Write about what happened, how you feel, or what you hope for..."
        save_label, empty_error = "Save journal entry", "Write a few lines before saving."
        history_label, download_label, delete_label = "Your entries", "⬇️ Download journal", "Delete this entry"
        empty_label, privacy_label = "You have not written any entries yet. Start with a few lines about today whenever you feel ready.", "Entries are kept only for the current browser session. Download a copy if you want to keep them after closing or refreshing the page."
        mood_options = ["😟 Very low", "🙁 Not great", "😐 Okay", "🙂 Good", "😊 Great"]

    with st.form("diary_entry_form", clear_on_submit=True):
        diary_title = st.text_input(title_label, placeholder=title_placeholder, max_chars=80)
        diary_mood = st.select_slider(mood_label, options=mood_options, value=mood_options[2])
        diary_text = st.text_area(entry_label, placeholder=entry_placeholder, height=180, max_chars=5000)
        save_entry = st.form_submit_button(save_label, type="primary", use_container_width=True)

    if save_entry:
        if diary_text.strip():
            st.session_state.diary_entries.append(
                {
                    "id": uuid4().hex,
                    "title": diary_title.strip(),
                    "mood": diary_mood,
                    "content": diary_text.strip(),
                    "created_at": datetime.now().astimezone().strftime("%d/%m/%Y %H:%M"),
                }
            )
            st.success("Đã lưu nhật ký." if is_vi else "Journal entry saved.")
        else:
            st.warning(empty_error)

    st.divider()
    st.subheader(history_label)
    entries = st.session_state.diary_entries
    if entries:
        export_lines = ["# Nhật ký SkyeChat" if is_vi else "# SkyeChat Journal", ""]
        for entry in reversed(entries):
            export_lines.extend(
                [
                    f"## {entry['title'] or ('Trang nhật ký' if is_vi else 'Journal entry')}",
                    f"{entry['created_at']} · {entry['mood']}",
                    "",
                    entry["content"],
                    "",
                    "---",
                    "",
                ]
            )
        st.download_button(
            download_label,
            data="\n".join(export_lines),
            file_name=f"skyechat_journal_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        for entry in reversed(entries):
            label = entry["title"] or ("Trang nhật ký" if is_vi else "Journal entry")
            with st.expander(f"{entry['mood']} · {label} · {entry['created_at']}"):
                st.write(entry["content"])
                if st.button(delete_label, key=f"delete_diary_{entry['id']}"):
                    st.session_state.diary_entries = [
                        item for item in st.session_state.diary_entries if item["id"] != entry["id"]
                    ]
                    st.rerun()
    else:
        st.info(empty_label)
    st.caption(privacy_label)

else:
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
    '<div class="footer">SkyeChat · Lắng nghe bằng sự tử tế · By ThanhAI</div>',
    unsafe_allow_html=True,
)
