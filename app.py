import os
import json
import logging
import random
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
import streamlit as st
from supabase import create_client


# ==============================
# SkyeChat — cấu hình
# ==============================
APP_DIR = Path(__file__).resolve().parent
logo_file = next(
    (APP_DIR / name for name in ("logo.png", "logo.jpg", "Logo.png", "Logo.jpg") if (APP_DIR / name).is_file()),
    None,
)
st.set_page_config(
    page_title="SkyeChat - Trợ lý AI hỗ trợ tâm lý học đường | ThanhAI",
    page_icon=str(logo_file) if logo_file else "☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-3.6-flash"
MAX_HISTORY_MESSAGES = 16
MAX_STORED_MESSAGES = 64
MAX_RETRIES = 2

def get_http_session():
    """Reuse pooled HTTP connections within this user session."""
    if "_http_session" not in st.session_state:
        st.session_state["_http_session"] = requests.Session()
    return st.session_state["_http_session"]

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
AI_PROVIDER = str(get_secret("AI_PROVIDER", "gemini") or "gemini").strip().lower()
if AI_PROVIDER in ("hf", "huggingface", "hugging_face"):
    AI_PROVIDER = "huggingface"
HF_ENDPOINT_URL = str(get_secret("HF_ENDPOINT_URL", "") or "").strip()
HF_ENDPOINT_NAME = str(get_secret("HF_ENDPOINT_NAME", "") or "").strip()
HF_TOKEN = str(get_secret("HF_TOKEN", "") or "").strip()
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_PUBLISHABLE_KEY") or get_secret("SUPABASE_ANON_KEY")
APP_TIMEZONE = get_secret("APP_TIMEZONE", "Asia/Ho_Chi_Minh")
LOGGER = logging.getLogger("skyechat")


def ai_is_configured():
    if AI_PROVIDER == "huggingface":
        return bool(HF_ENDPOINT_URL and HF_ENDPOINT_NAME and HF_TOKEN)
    if AI_PROVIDER == "gemini":
        return bool(GEMINI_API_KEY)
    return False


# ==============================
# Nhận diện thương hiệu SkyeChat
# ==============================
st.markdown(
    """
    <style>

    :root {
      --primary-color: #729b87;
      --sky-ink: #354b45;
      --sky-muted: #788b84;
      --sky-blue: #82aeb3;
      --sky-lilac: #aaaec5;
      --sky-mint: #e5f0e9;
      --sky-peach: #f6eee2;
      --sky-paper: #f7f8f5;
    }
    input[type="radio"] { accent-color: #729b87; }
    html, body, [class*="css"] { font-family: "Segoe UI", Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; font-size: 16px; }
    [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"], textarea, input, button { letter-spacing: .01em; }
    .stApp {
      color: var(--sky-ink);
      background: #eaf2f0;
    }
    [data-testid="stHeader"] { background: #eaf2f0; }
    [data-testid="stMainBlockContainer"] { max-width: 1120px; padding-top: 1.4rem; }
    [data-testid="stSidebar"] {
      background: #e2eeeb;
      border-right: 1px solid rgba(112,151,139,.18);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #586d66; }
    h1, h2, h3 { font-family: Inter, ui-sans-serif, system-ui, sans-serif !important; color: var(--sky-ink); }
    h1 { letter-spacing: -1.2px; }
    .hero {
      position: relative; overflow: hidden;
      padding: 1.65rem 2rem 1.55rem;
      border: 1px solid rgba(255,255,255,.9);
      border-radius: 26px;
      background: #dcebe8;
      box-shadow: 0 16px 45px rgba(74,111,101,.11);
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
    .hero-eyebrow { color: #668c79; font-size: .78rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
    .hero-title { color: #354b45; font: 900 2.25rem/1.22 Inter, ui-sans-serif, system-ui, sans-serif; margin: .25rem 0 .45rem; }
    .hero-tagline {
      display: inline-block; vertical-align: .22em; margin-left: .4rem;
      padding: .33rem .72rem; border: 1px solid rgba(112,151,139,.22);
      border-radius: 999px; background: rgba(255,255,255,.62);
      color: #628274; font: 700 .82rem/1.25 Inter, ui-sans-serif, system-ui, sans-serif;
      letter-spacing: .01em; white-space: normal;
    }
    .hero-copy { color: #60766e; max-width: 660px; font-size: 1rem; margin: 0; }
    .welcome-card {
      border: 1px solid rgba(137,172,157,.24); border-radius: 22px;
      padding: 1.25rem 1.4rem; margin: .8rem 0 1.25rem;
      background: #f8fbfa; box-shadow: 0 10px 30px rgba(75,111,101,.07);
      animation: hero-arrive .75s .08s ease-out both;
    }
    .welcome-card strong { color: #638875; }
    .soft-note { color: #788b84; font-size: .88rem; }
    .diary-intro {
      border: 1px solid rgba(139,174,168,.32); border-radius: 20px;
      padding: 1rem 1.2rem; margin: .7rem 0 1rem;
      background: #e4efed;
      color: #586f68;
    }
    .sidebar-brand {
      padding: 1rem; margin: .25rem 0 1.2rem; border-radius: 20px;
      background: #d7e7e3;
      text-align: center; color: #536d63;
    }
    .sidebar-brand .cloud { font-size: 2.2rem; }
    .sidebar-brand strong { display: block; font: 900 1.25rem Inter, ui-sans-serif, system-ui, sans-serif; color: #354b45; }
    .sidebar-brand span { font-size: .82rem; }
    div[data-testid="stChatMessage"] {
      border: 1px solid rgba(133,164,157,.23); border-radius: 20px;
      padding: .85rem 1rem; background: #f8fbfa;
      box-shadow: 0 8px 24px rgba(56,99,66,.055); margin-bottom: .85rem;
      transition: box-shadow .2s ease, transform .2s ease;
    }
    div[data-testid="stChatMessage"]:hover { box-shadow: 0 11px 28px rgba(56,99,66,.09); transform: translateY(-1px); }
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
      background: #e5efeb;
      border-color: rgba(143,174,147,.30);
    }
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
      background: #f7fbfa;
      border-color: rgba(145,178,171,.30);
    }
    [data-testid="stChatInput"] textarea {
      border-radius: 18px !important; border: 1px solid #d4e1dc !important;
      background: #fbfdfc !important;
      box-shadow: 0 8px 24px rgba(62,112,78,.07);
      transition: border-color .2s ease, box-shadow .2s ease;
    }
    [data-testid="stChatInput"] textarea:focus { border-color: #8caf9f !important; box-shadow: 0 0 0 3px rgba(112,151,139,.16) !important; }
    .stButton button {
      border-radius: 13px; border: 1px solid #d4e1dc; color: #536f63;
      background: rgba(255,255,255,.76); font-weight: 700;
      transition: all .18s ease;
    }
    .stButton button:hover { border-color: #98b8a8; color: #3d6255; background: #edf4ef; transform: translateY(-1px); box-shadow: 0 7px 16px rgba(77,119,103,.14); }
    .stButton button:focus-visible, [data-testid="stChatInput"] button:focus-visible { outline: 3px solid rgba(91,145,118,.58); outline-offset: 2px; }
    [data-testid="stChatInput"] button {
      border: 0 !important; border-radius: 13px !important; color: white !important;
      background: #638f86 !important;
      box-shadow: 0 5px 14px rgba(83,133,111,.26);
      transition: transform .18s ease, box-shadow .18s ease;
    }
    [data-testid="stChatInput"] button:hover { transform: translateY(-1px); box-shadow: 0 8px 18px rgba(83,133,111,.34); }
    div[data-testid="stAlert"] { border-radius: 15px; }
    .footer { color: #7d9181; text-align: center; font-size: .82rem; padding: 1.2rem 0 .3rem; }
    .teru-bozu {
      position: fixed; top: .1rem; right: 5.1rem; z-index: 1001;
      width: 72px; height: 132px; pointer-events: none;
      transform-origin: 50% 0; animation: teru-sway 4.8s ease-in-out infinite;
      filter: drop-shadow(0 8px 9px rgba(38, 75, 72, .25));
    }
    .teru-bozu svg { display: block; width: 100%; height: 100%; overflow: visible; }
    @keyframes teru-sway { 0%, 100% { transform: rotate(-5deg) translateY(0); } 50% { transform: rotate(5deg) translateY(3px); } }
    .stButton button:active, [data-testid="stChatInput"] button:active,
    [data-testid="stFormSubmitButton"] button:active, [data-testid="stDownloadButton"] button:active {
      transform: scale(.96) !important; box-shadow: inset 0 2px 5px rgba(34,74,70,.2) !important;
    }
    [data-testid="stRadio"] label, [data-testid="stToggle"] label,
    [data-testid="stExpander"] summary { transition: background-color .2s ease, color .2s ease, transform .2s ease; }
    [data-testid="stRadio"] label:active, [data-testid="stToggle"] label:active,
    [data-testid="stExpander"] summary:active { transform: scale(.985); }
    [data-testid="stExpander"] { transition: box-shadow .2s ease, border-color .2s ease; }
    [data-testid="stExpander"]:hover { box-shadow: 0 7px 18px rgba(49,93,87,.08); }
    .teru-head { filter: url(#doll-shadow); }
    .rain-drop { animation: rain-fall 2.2s ease-in infinite; transform-box: fill-box; transform-origin: center; }
    .rain-drop:nth-of-type(2) { animation-delay: .7s; }
    .rain-drop:nth-of-type(3) { animation-delay: 1.3s; }
    @keyframes rain-fall { 0% { opacity: 0; transform: translateY(-3px); } 35% { opacity: .9; } 100% { opacity: 0; transform: translateY(13px); } }
    @media (prefers-reduced-motion: reduce) {
      *, *:before, *:after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; transition-duration: .01ms !important; }
      .teru-bozu { animation: none !important; }
    }
    @media (max-width: 700px) {
      .hero { padding: 1.3rem; border-radius: 20px; }
      .hero-title { font-size: 1.9rem; }
      .hero-tagline { margin-left: .1rem; font-size: .72rem; padding: .3rem .58rem; }
      .hero:after { right: -5%; font-size: 110px; }
      .teru-bozu { right: 4.2rem; width: 48px; height: 96px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="teru-bozu" aria-hidden="true">
      <svg viewBox="0 0 64 128" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="doll-shadow" x="-30%" y="-20%" width="160%" height="160%"><feDropShadow dx="1" dy="3" stdDeviation="2" flood-color="#416a66" flood-opacity=".24"/></filter>
        </defs>
        <path d="M32 0v27" stroke="#527d79" stroke-width="2.4" stroke-linecap="round"/>
        <g class="teru-head">
          <circle cx="32" cy="46" r="19" fill="#e5efec" stroke="#b8ceca" stroke-width="1.5"/>
          <path d="M24 33q7-5 13-1" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".8"/>
          <path d="M18 58c-1 12-7 20-9 36-2 12 4 19 9 16 5-2 8-7 12-3 3 4 7 8 11 4 4-3 7-8 11-4 5 3 10 6 14 0 5-8-1-20-6-31-3-6-5-11-6-18-5 5-10 7-16 7s-12-2-16-7z" fill="#d5e5e1" stroke="#b8ceca" stroke-width="1.5" stroke-linejoin="round"/>
          <path d="M24 65q8 3 16 0" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".8"/>
          <path d="M24 46h.2M40 46h.2" stroke="#405a5a" stroke-width="3.5" stroke-linecap="round"/>
          <path d="M29 53q3 3 6 0" fill="none" stroke="#7c9d9a" stroke-width="1.8" stroke-linecap="round"/>
          <ellipse cx="22" cy="51" rx="3" ry="1.5" fill="#d89896" opacity=".42"/><ellipse cx="42" cy="51" rx="3" ry="1.5" fill="#d89896" opacity=".42"/>
          <path d="M27 63q5 4 10 0" fill="none" stroke="#82a9a4" stroke-width="2" stroke-linecap="round"/>
        </g>
        <path class="rain-drop" d="M10 72l-2 7M54 83l-2 7M13 105l-2 7" stroke="#79aeb3" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </div>
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
# Kiến thức và cách hỗ trợ riêng của SkyeChat
# Bạn có thể chỉnh sửa phần này để định hình cách SkyeChat trả lời.
# ==============================
SKYECHAT_GUIDE_VI = """
Hướng dẫn trò chuyện riêng của SkyeChat:
- Lắng nghe trước, phản hồi cảm xúc bằng giọng ấm áp và không phán xét.
- Hỏi từng câu ngắn, không gây áp lực để người dùng phải kể thêm.
- Khi học sinh lo lắng về bài kiểm tra, có thể hỏi điều gì làm bạn ấy lo nhất
  và cùng chọn một bước nhỏ, thực tế để bắt đầu.
- Không chẩn đoán bệnh, không hứa giữ bí mật tuyệt đối, không thay thế chuyên gia.
- Không tự bịa thông tin về trường học, dịch vụ hỗ trợ hoặc số điện thoại.
- Nếu người dùng có thể đang gặp nguy hiểm ngay lúc này, khuyến khích họ đến bên
  một người lớn đáng tin, người thân hoặc dịch vụ khẩn cấp tại địa phương.
  Trẻ em ở Việt Nam có thể liên hệ Tổng đài Quốc gia Bảo vệ Trẻ em 111.
""".strip()

SKYECHAT_GUIDE_EN = """
SkyeChat conversation guide:
- Listen first and respond to feelings with warmth and without judgment.
- Ask one brief question at a time; do not pressure the user to share more.
- If a student is worried about a test, you may ask what worries them most
  and help them choose one small, practical next step.
- Do not diagnose, promise absolute secrecy, or replace a qualified professional.
- Do not ask the user for passwords, home addresses, school/class names, or sensitive identifying information.
- Remind the user not to share sensitive identifying details when discussing private experiences.
- Do not invent school, support-service, or phone-number information.
- If someone may be in immediate danger, encourage them to reach a trusted adult,
  family member, or local emergency service now.
""".strip()


def build_system_prompt(is_vi):
    """Combine SkyeChat's role with its editable conversation guide."""
    base_prompt = SYSTEM_PROMPT_VI if is_vi else SYSTEM_PROMPT_EN
    guide = SKYECHAT_GUIDE_VI if is_vi else SKYECHAT_GUIDE_EN
    guide_title = "HƯỚNG DẪN RIÊNG" if is_vi else "CUSTOM GUIDE"
    return f"{base_prompt}\n\n{guide_title}:\n{guide}"


# ==============================
# Session state
# ==============================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "nickname" not in st.session_state:
    st.session_state.nickname = "Bạn"
if "nickname_is_custom" not in st.session_state:
    st.session_state.nickname_is_custom = False
if "auth_access_token" not in st.session_state:
    st.session_state.auth_access_token = None
if "auth_refresh_token" not in st.session_state:
    st.session_state.auth_refresh_token = None
if "auth_user_id" not in st.session_state:
    st.session_state.auth_user_id = None
if "auth_email" not in st.session_state:
    st.session_state.auth_email = ""
if "guest_mode" not in st.session_state:
    st.session_state.guest_mode = False
if "recovery_otp_sent" not in st.session_state:
    st.session_state.recovery_otp_sent = False
if "recovery_target" not in st.session_state:
    st.session_state.recovery_target = ""
if "recovery_type" not in st.session_state:
    st.session_state.recovery_type = ""
if "password_reset_pending" not in st.session_state:
    st.session_state.password_reset_pending = False
if "confirm_delete_diary_id" not in st.session_state:
    st.session_state.confirm_delete_diary_id = None
if "confirm_clear_chat" not in st.session_state:
    st.session_state.confirm_clear_chat = False
if "clear_diary_form" not in st.session_state:
    st.session_state.clear_diary_form = False
if "dark_mode" not in st.session_state:
    try:
        st.session_state.dark_mode = st.context.theme.type == "dark"
    except Exception:
        st.session_state.dark_mode = False


def save_auth_state(auth_response):
    """Keep the signed-in user's tokens in this browser session."""
    auth_session = getattr(auth_response, "session", None)
    auth_user = getattr(auth_response, "user", None)
    if not auth_session:
        return False

    st.session_state.auth_access_token = auth_session.access_token
    st.session_state.auth_refresh_token = auth_session.refresh_token
    if auth_user:
        st.session_state.auth_user_id = auth_user.id
        st.session_state.auth_email = auth_user.email or ""
        metadata = getattr(auth_user, "user_metadata", {}) or {}
        if not st.session_state.nickname_is_custom:
            st.session_state.nickname = metadata.get("nickname") or auth_user.email or "Bạn"
    elif getattr(auth_session, "user", None):
        auth_user = auth_session.user
        st.session_state.auth_user_id = auth_user.id
        st.session_state.auth_email = auth_user.email or ""
        metadata = getattr(auth_user, "user_metadata", {}) or {}
        if not st.session_state.nickname_is_custom:
            st.session_state.nickname = metadata.get("nickname") or auth_user.email or "Bạn"
    return bool(st.session_state.auth_user_id)


def clear_auth_state():
    st.session_state.auth_access_token = None
    st.session_state.auth_refresh_token = None
    st.session_state.auth_user_id = None
    st.session_state.auth_email = ""
    st.session_state.nickname = "Bạn"
    st.session_state.nickname_is_custom = False
    st.session_state.messages = []
    st.session_state.recovery_otp_sent = False
    st.session_state.recovery_target = ""
    st.session_state.recovery_type = ""
    st.session_state.password_reset_pending = False
    st.session_state.confirm_delete_diary_id = None
    st.session_state.confirm_clear_chat = False
    st.session_state.clear_diary_form = False
    st.session_state.guest_mode = False
    st.session_state.pop("journal_saved_recently", None)
    st.session_state.pop("diary_title_input", None)
    st.session_state.pop("diary_mood_input", None)
    st.session_state.pop("diary_text_input", None)
    st.session_state.page_mode = "chat"


def restore_auth_state(client):
    """Restore and refresh this user's Supabase session after a Streamlit rerun."""
    access_token = st.session_state.auth_access_token
    refresh_token = st.session_state.auth_refresh_token
    if not access_token or not refresh_token:
        if access_token or refresh_token or st.session_state.auth_user_id:
            clear_auth_state()
        return False
    try:
        auth_response = client.auth.set_session(access_token, refresh_token)
        if not save_auth_state(auth_response):
            user_response = client.auth.get_user()
            auth_user = getattr(user_response, "user", None)
            if auth_user:
                st.session_state.auth_user_id = auth_user.id
                st.session_state.auth_email = auth_user.email or ""
                metadata = getattr(auth_user, "user_metadata", {}) or {}
                if not st.session_state.nickname_is_custom:
                    st.session_state.nickname = metadata.get("nickname") or auth_user.email or "Bạn"
        return bool(st.session_state.auth_user_id)
    except Exception:
        try:
            client.auth.sign_out()
        except Exception:
            pass
        clear_auth_state()
        return False


def load_diary_entries(client, user_id):
    """Load only the signed-in user's entries; Supabase RLS enforces ownership."""
    if not user_id:
        return []
    result = (
        client.table("diary_entries")
        .select("id, user_id, title, mood, content, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return result.data or []


def get_app_timezone():
    """Return configured display timezone, falling back safely to UTC."""
    try:
        return ZoneInfo(str(APP_TIMEZONE))
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return ZoneInfo("UTC")


def format_created_at(value):
    """Format Supabase timestamps consistently, including UTC and bad values."""
    raw_value = str(value or "")
    if not raw_value:
        return ""
    try:
        timestamp = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=ZoneInfo("UTC"))
        return timestamp.astimezone(get_app_timezone()).strftime("%d/%m/%Y %H:%M")
    except (ValueError, OverflowError, OSError):
        return raw_value


supabase_client = None
supabase_init_error = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        # Keep this stateful auth client private to this browser session.
        if "_supabase_client" not in st.session_state:
            st.session_state["_supabase_client"] = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase_client = st.session_state["_supabase_client"]
    except Exception as exc:
        supabase_init_error = exc
        LOGGER.warning("Supabase client initialization failed: %s", type(exc).__name__)

is_authenticated = bool(supabase_client and restore_auth_state(supabase_client))
if is_authenticated and st.session_state.password_reset_pending:
    st.markdown(
        """
        <section class="hero">
          <div class="hero-eyebrow">Kh\u00f4i ph\u1ee5c t\u00e0i kho\u1ea3n</div>
          <div class="hero-title">\u0110\u1eb7t m\u1eadt kh\u1ea9u m\u1edbi</div>
          <p class="hero-copy">T\u1ea1o m\u1eadt kh\u1ea9u m\u1edbi \u0111\u1ec3 ho\u00e0n t\u1ea5t kh\u00f4i ph\u1ee5c t\u00e0i kho\u1ea3n.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    with st.form("skyechat_set_new_password_form"):
        new_password = st.text_input("M\u1eadt kh\u1ea9u m\u1edbi", type="password")
        confirm_new_password = st.text_input("Nh\u1eadp l\u1ea1i m\u1eadt kh\u1ea9u", type="password")
        password_submitted = st.form_submit_button(
            "L\u01b0u m\u1eadt kh\u1ea9u m\u1edbi", type="primary", use_container_width=True
        )
    if password_submitted:
        if len(new_password) < 8:
            st.warning("M\u1eadt kh\u1ea9u c\u1ea7n c\u00f3 ít nh\u1ea5t 8 k\u00fd t\u1ef1.")
        elif new_password != confirm_new_password:
            st.warning("Hai m\u1eadt kh\u1ea9u ch\u01b0a kh\u1edbp.")
        else:
            try:
                supabase_client.auth.update_user({"password": new_password})
                st.session_state.password_reset_pending = False
                st.session_state.recovery_target = ""
                st.session_state.recovery_type = ""
                st.session_state.password_change_success = True
                st.success("\u0110\u00e3 \u0111\u1ed5i m\u1eadt kh\u1ea9u. B\u1ea1n c\u00f3 th\u1ec3 ti\u1ebfp t\u1ee5c.")
                st.rerun()
            except Exception as exc:
                LOGGER.warning("Password update failed: %s", type(exc).__name__)
                st.error("Ch\u01b0a \u0111\u1ed5i \u0111\u01b0\u1ee3c m\u1eadt kh\u1ea9u. H\u00e3y x\u00e1c minh l\u1ea1i r\u1ed3i th\u1eed l\u1ea1i.")
    st.stop()
if is_authenticated and st.session_state.pop("password_change_success", False):
    st.success("Đã đổi mật khẩu thành công.")
if not is_authenticated and not st.session_state.guest_mode:
    _, guest_button_col = st.columns([4, 1.7])
    with guest_button_col:
        if st.button("👤 Dùng thử với tư cách khách", key="enter_guest_mode", use_container_width=True):
            st.session_state.guest_mode = True
            st.session_state.page_mode = "chat"
            st.rerun()
    st.markdown(
        """
        <section class="hero">
          <div class="hero-eyebrow">Chào mừng đến với SkyeChat</div>
          <div class="hero-title">Đăng nhập để tiếp tục ☁️</div>
          <p class="hero-copy">Tạo tài khoản để dùng không gian trò chuyện và lưu nhật ký riêng của bạn.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if supabase_client is None:
        if supabase_init_error:
            st.error("Chưa kết nối được Supabase. Kiểm tra Project URL và key trong Secrets để dùng tài khoản.")
        else:
            st.info("Đăng nhập và nhật ký cần cấu hình Supabase. Bạn vẫn có thể dùng nút khách ở phía trên để trò chuyện.")
        st.markdown('<div class="footer">SkyeChat · By ThanhAI · since august 2026</div>', unsafe_allow_html=True)
        st.stop()
    st.markdown(
        """
        <style>
        [data-testid="stForm"] { background: rgba(255,255,255,.78); border: 1px solid #dce8e1; border-radius: 20px; padding: 1.1rem; }
        [data-testid="stTextInput"] input { border-radius: 12px; }
        [data-testid="stFormSubmitButton"] button { min-height: 2.8rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    login_tab, signup_tab, recovery_tab = st.tabs(["Đăng nhập", "Tạo tài khoản", "Quên mật khẩu"])

    def is_valid_email(value):
        return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))

    def show_auth_error(exc, action):
        """Translate common Supabase Auth errors into actionable, safe guidance."""
        message = str(exc).lower()
        code = str(getattr(exc, "code", "") or "").lower()
        details = f"{code} {message}"
        LOGGER.warning(
            "Supabase auth action failed (%s, type=%s, code=%s)",
            action,
            type(exc).__name__,
            code or "unavailable",
        )
        if any(value in details for value in ("signup_disabled", "email_provider_disabled", "signups not allowed")):
            st.error("Đăng ký email đang bị tắt trong Supabase. Hãy bật Email provider và quyền cho phép tạo tài khoản mới trong Authentication settings.")
        elif any(value in details for value in ("rate limit", "too many", "over_email_send_rate_limit", "over_request_rate_limit")):
            st.warning("Bạn thử quá nhiều lần. Hãy đợi một chút rồi thử lại.")
        elif "already registered" in details or "user already exists" in details or "email_exists" in details:
            st.warning("Email này đã có tài khoản. Hãy đăng nhập hoặc dùng chức năng quên mật khẩu.")
        elif "email_address_not_authorized" in details:
            st.error("Máy chủ email mặc định của Supabase không gửi đến địa chỉ này. Hãy cấu hình SMTP riêng trong Supabase để gửi email xác nhận cho người dùng.")
        elif "invalid login credentials" in details or "invalid credentials" in details:
            st.error("Email hoặc mật khẩu chưa chính xác. Nếu chưa xác nhận email, hãy kiểm tra hộp thư.")
        elif "weak_password" in details or ("password" in details and any(value in details for value in ("weak", "short", "least", "characters"))):
            st.warning("Mật khẩu chưa đáp ứng chính sách bảo mật của dự án Supabase. Hãy thử mật khẩu dài hơn, gồm chữ và số.")
        elif "email" in details and any(value in details for value in ("smtp", "send", "delivery", "confirmation")):
            st.error("Chưa gửi được email xác nhận. Hãy kiểm tra cấu hình SMTP và giới hạn gửi email trong Supabase.")
        elif "captcha" in details:
            st.error("Xác minh chống spam chưa hoàn tất. Hãy kiểm tra cấu hình CAPTCHA trong Supabase.")
        else:
            error_id = code or "không được Supabase cung cấp"
            diagnostic = str(getattr(exc, "message", "") or str(exc)).strip()
            diagnostic = re.sub(
                r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
                "[email đã ẩn]",
                diagnostic,
                flags=re.IGNORECASE,
            )
            diagnostic = re.sub(
                r"(?i)(access[_ -]?token|refresh[_ -]?token|api[_ -]?key)\s*[:=]\s*\S+",
                r"\1=[đã ẩn]",
                diagnostic,
            )[:240]
            detail_text = f" Chi tiết: {diagnostic}" if diagnostic else ""
            st.error(f"{action} chưa thành công (mã lỗi: {error_id}).{detail_text}")

    with login_tab:
        st.caption("Đăng nhập bằng email hoặc số điện thoại đã xác minh.")
        with st.form("skyechat_login_form"):
            login_identity = st.text_input("Email hoặc số điện thoại", placeholder="ban@example.com hoặc +84901234567")
            login_password = st.text_input("Mật khẩu", type="password", autocomplete="current-password")
            login_submitted = st.form_submit_button("Đăng nhập", type="primary", use_container_width=True)
        if login_submitted:
            identity = login_identity.strip()
            if not identity:
                st.warning("Hãy nhập email hoặc số điện thoại.")
            elif not login_password:
                st.warning("Hãy nhập mật khẩu.")
            elif "@" in identity and not is_valid_email(identity):
                st.warning("Hãy kiểm tra lại địa chỉ email.")
            elif "@" not in identity and (not identity.startswith("+") or not identity[1:].isdigit() or not 8 <= len(identity[1:]) <= 15):
                st.warning("Số điện thoại cần có mã quốc gia, ví dụ +84901234567.")
            else:
                try:
                    auth_credentials = (
                        {"email": identity.lower(), "password": login_password}
                        if "@" in identity
                        else {"phone": identity, "password": login_password}
                    )
                    auth_response = supabase_client.auth.sign_in_with_password(auth_credentials)
                    if save_auth_state(auth_response):
                        st.rerun()
                    st.info("Hãy xác nhận email đăng ký rồi thử đăng nhập lại.")
                except Exception as exc:
                    show_auth_error(exc, "Đăng nhập")

    with signup_tab:
        st.caption("Tạo tài khoản miễn phí để lưu nhật ký và tiếp tục sử dụng trên thiết bị khác.")
        with st.form("skyechat_signup_form"):
            signup_nickname = st.text_input("Tên hiển thị", placeholder="Tên bạn muốn dùng", max_chars=32, autocomplete="nickname")
            signup_email = st.text_input("Email", placeholder="ban@example.com", autocomplete="email")
            signup_password = st.text_input("Tạo mật khẩu", type="password", autocomplete="new-password", help="Dùng ít nhất 8 ký tự.")
            signup_password_confirm = st.text_input("Nhập lại mật khẩu", type="password", autocomplete="new-password")
            signup_submitted = st.form_submit_button("Tạo tài khoản", type="primary", use_container_width=True)
        if signup_submitted:
            normalized_email = signup_email.strip().lower()
            if not signup_nickname.strip():
                st.warning("Hãy nhập tên hiển thị.")
            elif not is_valid_email(normalized_email):
                st.warning("Hãy nhập địa chỉ email hợp lệ.")
            elif len(signup_password) < 8:
                st.warning("Mật khẩu cần có ít nhất 8 ký tự.")
            elif signup_password != signup_password_confirm:
                st.warning("Hai mật khẩu chưa khớp.")
            else:
                try:
                    auth_response = supabase_client.auth.sign_up(
                        {
                            "email": normalized_email,
                            "password": signup_password,
                            "options": {"data": {"nickname": signup_nickname.strip()}},
                        }
                    )
                    if save_auth_state(auth_response):
                        st.rerun()
                    st.success("Đã tạo tài khoản. Hãy mở email để xác nhận, sau đó quay lại đăng nhập.")
                except Exception as exc:
                    show_auth_error(exc, "Tạo tài khoản")
    with recovery_tab:
        st.caption(
            "Khôi phục qua email. Mẫu email khôi phục của Supabase cần hiển thị mã {{ .Token }} "
            "để bạn có thể nhập mã trực tiếp tại đây."
        )
        with st.form("skyechat_recovery_request_form"):
            recovery_target = st.text_input(
                "Email đã đăng ký", placeholder="ban@example.com", autocomplete="email"
            )
            send_code = st.form_submit_button(
                "Gửi mã khôi phục", type="primary", use_container_width=True
            )

        if send_code:
            target = recovery_target.strip().lower()
            if not is_valid_email(target):
                st.warning("Hãy nhập địa chỉ email hợp lệ.")
            else:
                try:
                    supabase_client.auth.reset_password_for_email(target)
                    st.session_state.recovery_target = target
                    st.session_state.recovery_otp_sent = True
                    st.session_state.recovery_type = "recovery"
                    st.success(
                        "Nếu email thuộc một tài khoản, hướng dẫn khôi phục đã được gửi. "
                        "Hãy kiểm tra cả thư mục Spam."
                    )
                except Exception as exc:
                    LOGGER.warning("Supabase password reset request failed: %s", type(exc).__name__)
                    st.error("Chưa gửi được mã. Hãy kiểm tra cấu hình email Supabase rồi thử lại.")

        if st.session_state.recovery_otp_sent:
            st.caption(f"Nhập mã khôi phục đã gửi tới {st.session_state.recovery_target}.")
            with st.form("skyechat_recovery_verify_form"):
                recovery_code = st.text_input(
                    "Mã khôi phục", max_chars=12, autocomplete="one-time-code"
                )
                verify_code = st.form_submit_button(
                    "Xác minh mã", type="primary", use_container_width=True
                )
            if verify_code:
                if not recovery_code.strip():
                    st.warning("Hãy nhập mã trong email.")
                else:
                    try:
                        auth_response = supabase_client.auth.verify_otp(
                            {
                                "email": st.session_state.recovery_target,
                                "token": recovery_code.strip(),
                                "type": "recovery",
                            }
                        )
                        if save_auth_state(auth_response):
                            st.session_state.password_reset_pending = True
                            st.session_state.recovery_otp_sent = False
                            st.rerun()
                        st.error("Mã chưa mở được phiên khôi phục. Hãy gửi mã mới.")
                    except Exception as exc:
                        LOGGER.warning(
                            "Supabase password reset verification failed: %s", type(exc).__name__
                        )
                        st.error("Mã không hợp lệ hoặc đã hết hạn. Hãy gửi mã mới.")
    st.markdown('<div class="footer">SkyeChat · By ThanhAI · since august 2026</div>', unsafe_allow_html=True)
    st.stop()


class GeminiAPIError(RuntimeError):
    """An API failure with a status code safe to classify in the interface."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def api_error_message(response):
    try:
        data = response.json()
    except ValueError:
        return "The server returned an unreadable response."
    error = data.get("error", {}) if isinstance(data, dict) else {}
    message = error.get("message") if isinstance(error, dict) else None
    return str(message or "Unknown Gemini API error.")[:500]


def prepare_gemini_contents(history):
    """Return a bounded Gemini history beginning with a user turn."""
    normalized = []
    for message in history:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = message.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str) or not content.strip():
            continue
        normalized.append({"role": role, "content": content.strip()})

    normalized = normalized[-MAX_HISTORY_MESSAGES:]
    while normalized and normalized[0]["role"] != "user":
        normalized.pop(0)
    if not normalized:
        raise ValueError("A user message is required to start a conversation.")

    return [
        {
            "role": "user" if message["role"] == "user" else "model",
            "parts": [{"text": message["content"]}],
        }
        for message in normalized
    ]


def prepare_openai_messages(history, system_prompt):
    """Build provider-neutral messages for OpenAI-compatible chat endpoints."""
    normalized = []
    for message in history:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = message.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str) or not content.strip():
            continue
        normalized.append({"role": role, "content": content.strip()})

    normalized = normalized[-MAX_HISTORY_MESSAGES:]
    while normalized and normalized[0]["role"] != "user":
        normalized.pop(0)
    if not normalized:
        raise ValueError("A user message is required to start a conversation.")

    return [{"role": "system", "content": system_prompt}, *normalized]


def normalize_hf_endpoint_url():
    """Validate the copied endpoint origin and add the OpenAI-compatible route."""
    parsed = urlsplit(HF_ENDPOINT_URL)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise GeminiAPIError("Invalid Hugging Face endpoint URL.")
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        path = path[:-3]
    if path not in ("", "/"):
        raise GeminiAPIError("Use the Hugging Face endpoint base URL without an API path.")
    return f"https://{parsed.netloc}/v1/"


def generate_huggingface_reply(history, system_prompt):
    """Yield response text from a private Hugging Face Inference Endpoint."""
    if not ai_is_configured():
        raise GeminiAPIError("Hugging Face endpoint is not configured.")
    try:
        from huggingface_hub import InferenceClient
    except ImportError as exc:
        raise GeminiAPIError("Install the huggingface_hub package to use this provider.") from exc

    try:
        client = InferenceClient(
            base_url=normalize_hf_endpoint_url(), token=HF_TOKEN, timeout=45
        )
        completion = client.chat.completions.create(
            model=HF_ENDPOINT_NAME,
            messages=prepare_openai_messages(history, system_prompt),
            max_tokens=512,
            temperature=0.7,
            stream=True,
        )
        emitted = False
        for chunk in completion:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            text = getattr(delta, "content", None) if delta else None
            if isinstance(text, str) and text:
                emitted = True
                yield text
        if not emitted:
            raise GeminiAPIError("Hugging Face returned no text. Please try again.")
    except GeminiAPIError:
        raise
    except Exception as exc:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        raise GeminiAPIError("Hugging Face endpoint request failed.", status) from exc


def generate_reply(history, system_prompt):
    """Yield response text from the configured provider."""
    if AI_PROVIDER == "huggingface":
        yield from generate_huggingface_reply(history, system_prompt)
        return
    if AI_PROVIDER != "gemini":
        raise GeminiAPIError("Unsupported AI_PROVIDER. Choose gemini or huggingface.")
    if not GEMINI_API_KEY:
        raise GeminiAPIError("Gemini is not configured.")

    contents = prepare_gemini_contents(history)
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 512, "temperature": 0.7},
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    models = []
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        model = str(model or "").strip()
        if model and re.fullmatch(r"[A-Za-z0-9._-]+", model) and model not in models:
            models.append(model)
    if not models:
        raise GeminiAPIError("No valid Gemini model is configured.")

    retryable_statuses = {408, 429, 500, 502, 503, 504}
    fallback_statuses = retryable_statuses | {404}
    last_status = None
    last_network_error = None

    for model_index, model in enumerate(models):
        for attempt in range(MAX_RETRIES):
            emitted = False
            try:
                with get_http_session().post(
                    f"{API_BASE}/{model}:streamGenerateContent?alt=sse",
                    json=payload,
                    headers=headers,
                    stream=True,
                    timeout=(5, 45),
                ) as response:
                    last_status = response.status_code
                    if response.status_code != 200:
                        message = api_error_message(response)
                        if response.status_code not in retryable_statuses:
                            if model_index + 1 < len(models) and response.status_code in fallback_statuses:
                                break
                            raise GeminiAPIError(message, response.status_code)
                        if attempt < MAX_RETRIES - 1:
                            retry_after = response.headers.get("Retry-After")
                            try:
                                delay = max(0.2, min(float(retry_after), 2.5)) if retry_after else 0.8 * (2 ** attempt)
                            except (TypeError, ValueError):
                                delay = 0.8 * (2 ** attempt)
                            time.sleep(delay + random.uniform(0, 0.25))
                        continue

                    response.encoding = "utf-8"
                    for line in response.iter_lines(decode_unicode=True):
                        if isinstance(line, bytes):
                            line = line.decode("utf-8", errors="replace")
                        if not line or not line.startswith("data:"):
                            continue
                        raw_data = line[5:].strip()
                        if raw_data == "[DONE]":
                            break
                        try:
                            data = json.loads(raw_data)
                        except ValueError:
                            continue
                        if isinstance(data, dict) and data.get("error"):
                            api_error = data["error"]
                            message = api_error.get("message", "Gemini returned an error.") if isinstance(api_error, dict) else "Gemini returned an error."
                            raise GeminiAPIError(str(message))
                        prompt_feedback = data.get("promptFeedback", {}) if isinstance(data, dict) else {}
                        if isinstance(prompt_feedback, dict) and prompt_feedback.get("blockReason"):
                            raise GeminiAPIError("The request was blocked by Gemini safety filters.")
                        candidates = data.get("candidates", []) if isinstance(data, dict) else []
                        if not candidates or not isinstance(candidates[0], dict):
                            continue
                        candidate = candidates[0]
                        candidate_content = candidate.get("content")
                        if not isinstance(candidate_content, dict):
                            continue
                        parts = candidate_content.get("parts", [])
                        for part in parts:
                            chunk = part.get("text", "") if isinstance(part, dict) else ""
                            if chunk:
                                emitted = True
                                yield chunk
                    if not emitted:
                        raise GeminiAPIError("Gemini returned no text. Please try again.")
                    return
            except requests.RequestException as exc:
                if emitted:
                    raise
                last_network_error = exc
                last_status = None
                if attempt < MAX_RETRIES - 1:
                    time.sleep(min(0.8 * (2 ** attempt), 2.0) + random.uniform(0, 0.25))
            except GeminiAPIError as exc:
                if exc.status_code is not None and model_index + 1 < len(models) and exc.status_code in fallback_statuses:
                    break
                raise

    if last_status is not None:
        raise GeminiAPIError("Gemini is temporarily unavailable.", last_status)
    raise GeminiAPIError("Could not connect to Gemini.") from last_network_error


def friendly_chat_error(exc, is_vi):
    """Keep technical details out of the student-facing error message."""
    status = getattr(exc, "status_code", None)
    if AI_PROVIDER == "huggingface" and isinstance(exc, GeminiAPIError):
        message = str(exc)
        if "Invalid Hugging Face endpoint URL" in message or "without an API path" in message:
            return (
                "URL endpoint Hugging Face chưa đúng. Hãy dán URL gốc, không kèm đường dẫn API ngoài `/v1/`."
                if is_vi
                else "The Hugging Face endpoint URL is malformed. Paste the base URL without an API path; the app adds `/v1/`."
            )
        cause_name = type(exc.__cause__).__name__ if exc.__cause__ else ""
        if "Timeout" in cause_name:
            return "Endpoint phản hồi quá lâu. Hãy kiểm tra endpoint đang ở trạng thái Running rồi thử lại." if is_vi else "The endpoint timed out. Check that it is Running, then try again."
    if not ai_is_configured():
        if AI_PROVIDER == "huggingface":
            return (
                "AI chưa được cấu hình. Hãy thêm `HF_ENDPOINT_URL`, `HF_ENDPOINT_NAME` và `HF_TOKEN` vào Streamlit Secrets."
                if is_vi
                else "AI is not configured. Add `HF_ENDPOINT_URL`, `HF_ENDPOINT_NAME`, and `HF_TOKEN` to Streamlit Secrets."
            )
        return "Trò chuyện AI đang tạm tắt vì chưa cấu hình khóa Gemini." if is_vi else "AI chat is unavailable because the Gemini key is not configured."
    if isinstance(exc, requests.Timeout):
        return "Phản hồi mất quá nhiều thời gian. Hãy thử gửi lại." if is_vi else "The response timed out. Please try again."
    if isinstance(exc, requests.RequestException):
        return "Không kết nối được với dịch vụ AI. Hãy kiểm tra mạng rồi thử lại." if is_vi else "Could not connect to the AI service. Check your connection and try again."
    if status == 429:
        return "SkyeChat đang quá tải. Hãy đợi một chút rồi thử lại." if is_vi else "SkyeChat is busy. Please wait a moment and try again."
    if status == 401:
        if AI_PROVIDER == "huggingface":
            return (
                "Hugging Face từ chối xác thực. Hãy kiểm tra `HF_TOKEN` trong Streamlit Secrets."
                if is_vi
                else "Hugging Face authentication failed. Check `HF_TOKEN` in Streamlit Secrets."
            )
        return (
            "Gemini trả lỗi 401: khóa API bị thiếu, sai hoặc đã hết hạn. Hãy tạo khóa mới trong Google AI Studio và cập nhật `GEMINI_API_KEY` trong Streamlit Secrets."
            if is_vi
            else "Gemini returned 401: the API key is missing, invalid, or expired. Create a new key in Google AI Studio and update `GEMINI_API_KEY` in Streamlit Secrets."
        )
    if status == 403:
        if AI_PROVIDER == "huggingface":
            return (
                "Hugging Face không cho phép truy cập endpoint. Hãy kiểm tra quyền của token và endpoint."
                if is_vi
                else "Hugging Face denied access to the endpoint. Check the token permissions and endpoint access."
            )
        return (
            "Gemini trả lỗi 403: khóa hoặc project chưa được cấp quyền. Kiểm tra quyền Gemini API, trạng thái project và hạn chế của khóa trong Google AI Studio/Cloud."
            if is_vi
            else "Gemini returned 403: the key or project is not authorized. Check Gemini API access, project status, and key restrictions in Google AI Studio/Cloud."
        )
    if status == 404:
        if AI_PROVIDER == "huggingface":
            return (
                "Không tìm thấy endpoint hoặc tên endpoint không đúng. Hãy kiểm tra `HF_ENDPOINT_URL` và `HF_ENDPOINT_NAME`."
                if is_vi
                else "Endpoint not found. Check `HF_ENDPOINT_URL` and `HF_ENDPOINT_NAME`."
            )
        return "Không tìm thấy model Gemini đã cấu hình. Hãy kiểm tra GEMINI_MODEL." if is_vi else "The configured Gemini model was not found. Check GEMINI_MODEL."
    if status and status >= 500:
        return "Dịch vụ AI đang gặp sự cố tạm thời. Hãy thử lại sau." if is_vi else "The AI service is temporarily unavailable. Please try again later."
    return "Chưa thể tạo phản hồi. Hãy thử lại sau ít phút." if is_vi else "I could not generate a reply. Please try again in a few minutes."

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
    st.subheader("Phiên khách" if st.session_state.guest_mode else "Cài đặt của bạn")
    if st.session_state.guest_mode:
        st.caption("Bạn đang trò chuyện với tư cách khách. Nội dung chỉ được giữ trong phiên hiện tại.")
        if st.button("Đăng nhập / tạo tài khoản", use_container_width=True):
            st.session_state.guest_mode = False
            st.session_state.messages = []
            st.session_state.page_mode = "chat"
            st.rerun()
    else:
        st.caption(f"Tài khoản: {st.session_state.auth_email}")
        if st.button("Đăng xuất", use_container_width=True):
            try:
                if supabase_client:
                    supabase_client.auth.sign_out()
            except Exception:
                pass
            clear_auth_state()
            st.rerun()

    nickname_input = st.text_input("Biệt danh", value=st.session_state.nickname, max_chars=32)
    if nickname_input.strip() and nickname_input.strip() != st.session_state.nickname:
        st.session_state.nickname = nickname_input.strip()
        st.session_state.nickname_is_custom = True

    st.success(f"👋 Chào {st.session_state.nickname}!")
    lang = st.radio("Ngôn ngữ / Language", ["Tiếng Việt 🇻🇳", "English 🇬🇧"], label_visibility="visible")
    is_vi = lang.startswith("Tiếng Việt")
    if st.session_state.guest_mode:
        st.session_state.page_mode = "chat"
        page_mode = "chat"
        st.caption("Nhật ký riêng cần tài khoản để lưu an toàn.")
    else:
        if st.session_state.get("page_mode") not in ("chat", "diary"):
            previous_page_mode = str(st.session_state.get("page_mode", ""))
            st.session_state.page_mode = (
                "diary" if "Nhật ký" in previous_page_mode or "Journal" in previous_page_mode else "chat"
            )
        page_mode = st.radio(
            "Mục bạn muốn mở" if is_vi else "Choose a space",
            options=("chat", "diary"),
            format_func=lambda value: (
                ("💬 Trò chuyện" if value == "chat" else "📔 Nhật ký")
                if is_vi
                else ("💬 Chat" if value == "chat" else "📔 Journal")
            ),
            key="page_mode",
        )
    is_diary = page_mode == "diary"
    st.toggle(
        "Giao diện tối" if is_vi else "Dark appearance",
        key="dark_mode",
        help="Bật giao diện xanh lá tối, dễ nhìn khi dùng ban đêm." if is_vi else "Use the dark green appearance.",
    )
    IS_DARK_THEME = st.session_state.dark_mode
    if not ai_is_configured() and not is_diary:
        if AI_PROVIDER == "huggingface":
            st.info(
                "Thêm `HF_ENDPOINT_URL`, `HF_ENDPOINT_NAME` và `HF_TOKEN` vào Streamlit Secrets để bật model Hugging Face."
                if is_vi
                else "Add `HF_ENDPOINT_URL`, `HF_ENDPOINT_NAME`, and `HF_TOKEN` to Streamlit Secrets to enable the Hugging Face model."
            )
        else:
            st.info(
                "Thêm `GEMINI_API_KEY` vào Streamlit Secrets để bật trò chuyện với AI."
                if is_vi
                else "Add `GEMINI_API_KEY` to Streamlit Secrets to enable AI chat."
            )

    st.divider()
    st.markdown("**Nhà phát triển:** ThanhAI")
    if st.button(
        "🗑️ Xóa lịch sử trò chuyện" if is_vi else "🗑️ Clear chat history",
        use_container_width=True,
    ):
        st.session_state.confirm_clear_chat = True
    if st.session_state.confirm_clear_chat:
        st.caption(
            "Bạn muốn xóa toàn bộ hội thoại trong phiên này?" if is_vi
            else "Clear all messages from this session?"
        )
        clear_col, keep_col = st.columns(2)
        if clear_col.button("Xóa" if is_vi else "Clear", key="confirm_clear_chat_button", type="primary"):
            st.session_state.messages = []
            st.session_state.confirm_clear_chat = False
            st.rerun()
        if keep_col.button("Giữ lại" if is_vi else "Keep", key="cancel_clear_chat"):
            st.session_state.confirm_clear_chat = False
            st.rerun()

    st.divider()
    safety_notice = (
        "**Lưu ý an toàn**\n\nSkyeChat hỗ trợ lắng nghe và sơ cứu tâm lý ban đầu; không thay thế chuyên gia. "
        "Nếu bạn hoặc ai đó đang gặp nguy hiểm, hãy báo ngay cho người lớn đáng tin. "
        "Trẻ em tại Việt Nam có thể gọi Tổng đài Bảo vệ Trẻ em **111**."
        if is_vi
        else "**Safety note**\n\nSkyeChat offers supportive listening and initial wellbeing guidance; it does not replace a professional. "
        "If you or someone else is in immediate danger, contact a trusted adult or local emergency services now."
    )
    st.warning(
        safety_notice,
        icon="🫶",
    )
    st.caption(
        "Cuộc trò chuyện chỉ được lưu trong phiên trình duyệt hiện tại."
        if is_vi
        else "Chat history is kept only in the current browser session."
    )


if is_diary:
    st.markdown(
        """
        <style>
        [data-testid="stForm"] {
          background: #e8f1ee;
          border: 1px solid #cddfda;
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
          background: #477c71 !important;
          box-shadow: 0 6px 15px rgba(63, 128, 82, .18);
          transition: transform .18s ease, box-shadow .18s ease;
        }
        [data-testid="stDownloadButton"] button:hover,
        [data-testid="stFormSubmitButton"] button:hover {
          color: #fff !important;
          border-color: #2f7045 !important;
          background: #376a61 !important;
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

if IS_DARK_THEME:
    st.markdown(
        """
        <style>
        :root {
          --sky-ink: #e5efe5;
          --sky-muted: #b0c1b1;
          --sky-paper: #141d17;
        }
        .stApp {
          color: #e4eee4 !important;
      background: #172321 !important;
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"] { background-color: #171d1b !important; }
        [data-testid="stHeader"] { background: rgba(23, 29, 27, .92) !important; }
        [data-testid="stSidebar"] {
          background: #202d2b !important;
          border-right: 1px solid rgba(137, 179, 139, .18) !important;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #c1d0c2 !important; }
        h1, h2, h3,
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stMain"] label { color: #e4eee4 !important; }
        [data-testid="stCaptionContainer"] { color: #afc0b0 !important; }
        .hero {
          background: #263b3a !important;
          border-color: rgba(171, 205, 166, .18) !important;
          box-shadow: 0 16px 45px rgba(0, 0, 0, .22) !important;
        }
        .hero-eyebrow { color: #acd4a8 !important; }
        .hero-title { color: #eff7ed !important; }
        .hero-tagline { color: #cfdfd6 !important; background: rgba(35, 52, 47, .82) !important; border-color: rgba(166, 193, 181, .25) !important; }
        .hero-copy { color: #c5d4c5 !important; }
        .welcome-card {
          background: #202e2c !important;
          border-color: #394d3c !important;
          box-shadow: 0 10px 30px rgba(0, 0, 0, .18) !important;
          color: #dce8dc !important;
        }
        .welcome-card strong { color: #a9d5ae !important; }
        .soft-note { color: #afc2b0 !important; }
        .diary-intro {
          background: #203331 !important;
          border-color: #405b44 !important;
          color: #cfe0d0 !important;
        }
        .sidebar-brand {
          background: #263b36 !important;
          color: #c9d9ca !important;
        }
        .sidebar-brand strong { color: #f0f6ed !important; }
        div[data-testid="stChatMessage"] {
          background: #202a22 !important;
          border-color: #39483b !important;
          box-shadow: 0 8px 24px rgba(0, 0, 0, .16) !important;
          color: #e4eee4 !important;
        }
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
          background: #2b403c !important;
          border-color: #4a6046 !important;
        }
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
          background: #213532 !important;
          border-color: #3b5544 !important;
        }
        [data-testid="stChatInput"] textarea,
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
          background: #202a22 !important;
          color: #edf5ed !important;
          border-color: #455a47 !important;
        }
        [data-testid="stChatInput"] textarea::placeholder,
        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder { color: #a8b9a9 !important; }
        [data-testid="stChatInput"] textarea:focus,
        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {
          border-color: #85b98b !important;
          box-shadow: 0 0 0 3px rgba(112, 175, 122, .18) !important;
        }
        [data-testid="stForm"] {
          background: #1e302d !important;
          border-color: #3c5540 !important;
          box-shadow: 0 12px 28px rgba(0, 0, 0, .18) !important;
        }
        [data-testid="stExpander"] {
          background: #1d2921 !important;
          border-color: #3c5140 !important;
          color: #e2ece2 !important;
        }
        [data-testid="stExpander"] summary:hover { background: #29392b !important; }
        .stButton button {
          background: #253329 !important;
          border-color: #4a624b !important;
          color: #dcebdc !important;
        }
        .stButton button:hover { background: #304532 !important; color: #f2f8f1 !important; }
        [data-testid="stChatInput"] button,
        [data-testid="stDownloadButton"] button,
        [data-testid="stFormSubmitButton"] button {
          background: #477c71 !important;
          border-color: #75a97a !important;
          color: #fff !important;
        }
        .footer { color: #9bad9d !important; }
        .teru-bozu { filter: drop-shadow(0 5px 9px rgba(0, 0, 0, .42)); }
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
        confirm_delete_label, cancel_delete_label = "Xóa nhật ký", "Giữ lại"
        confirm_delete_prompt = "Bạn có chắc muốn xóa trang này? Thao tác này không thể hoàn tác."
        delete_error = "Chưa xóa được trang nhật ký. Hãy thử lại."
        delete_success = "Đã xóa trang nhật ký."
        empty_label, privacy_label = "Bạn chưa viết trang nhật ký nào. Khi sẵn sàng, hãy bắt đầu bằng vài dòng về hôm nay.", "Nhật ký được lưu theo tài khoản Supabase để bạn có thể xem lại sau khi đăng nhập trên thiết bị khác."
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
        confirm_delete_label, cancel_delete_label = "Delete entry", "Keep entry"
        confirm_delete_prompt = "Are you sure you want to delete this entry? This cannot be undone."
        delete_error = "Could not delete the journal entry. Please try again."
        delete_success = "Journal entry deleted."
        empty_label, privacy_label = "You have not written any entries yet. Start with a few lines about today whenever you feel ready.", "Journal entries are saved to your Supabase account so you can view them after signing in on another device."
        mood_options = ["😟 Very low", "🙁 Not great", "😐 Okay", "🙂 Good", "😊 Great"]

    if st.session_state.clear_diary_form:
        st.session_state.diary_title_input = ""
        st.session_state.diary_mood_input = 2
        st.session_state.diary_text_input = ""
        st.session_state.clear_diary_form = False

    with st.form("diary_entry_form", clear_on_submit=False):
        diary_title = st.text_input(
            title_label, placeholder=title_placeholder, max_chars=80, key="diary_title_input"
        )
        diary_mood_index = st.select_slider(
            mood_label,
            options=(0, 1, 2, 3, 4),
            value=2,
            format_func=lambda value: mood_options[value],
            key="diary_mood_input",
        )
        diary_text = st.text_area(
            entry_label,
            placeholder=entry_placeholder,
            height=180,
            max_chars=5000,
            key="diary_text_input",
        )
        save_entry = st.form_submit_button(save_label, type="primary", use_container_width=True)

    if save_entry:
        if diary_text.strip():
            try:
                supabase_client.table("diary_entries").insert(
                    {
                        "user_id": st.session_state.auth_user_id,
                        "title": diary_title.strip(),
                        "mood": mood_options[diary_mood_index],
                        "content": diary_text.strip(),
                    }
                ).execute()
                st.session_state.clear_diary_form = True
                st.session_state.journal_saved_recently = True
                st.rerun()
            except Exception as exc:
                LOGGER.warning("Journal save failed: %s", type(exc).__name__)
                st.error(
                    "Chưa lưu được nhật ký. Hãy kiểm tra đã chạy file `supabase_setup.sql` và bật quyền truy cập an toàn."
                    if is_vi
                    else "Could not save the entry. Check that `supabase_setup.sql` has been applied and database access is configured."
                )
        else:
            st.warning(empty_error)

    if st.session_state.pop("journal_saved_recently", False):
        st.success("Đã lưu nhật ký." if is_vi else "Journal entry saved.")

    st.divider()
    st.subheader(history_label)
    try:
        entries = load_diary_entries(supabase_client, st.session_state.auth_user_id)
    except Exception as exc:
        LOGGER.warning("Journal load failed: %s", type(exc).__name__)
        entries = []
        st.error(
            "Chưa tải được nhật ký. Hãy kiểm tra đã tạo bảng `diary_entries` trong Supabase."
            if is_vi
            else "Could not load entries. Check that the `diary_entries` table exists in Supabase."
        )
    if entries:
        export_lines = ["# Nhật ký SkyeChat" if is_vi else "# SkyeChat Journal", ""]
        for entry in reversed(entries):
            title = str(entry.get("title") or ("Trang nhật ký" if is_vi else "Journal entry"))
            formatted_created_at = format_created_at(entry.get("created_at"))
            mood = str(entry.get("mood") or "")
            content = str(entry.get("content") or "")
            export_lines.extend(
                [f"## {title}", f"{formatted_created_at} · {mood}", "", content, "", "---", ""]
            )

        st.download_button(
            download_label,
            data="\n".join(export_lines),
            file_name=f"skyechat_journal_{datetime.now(get_app_timezone()).strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        if len(entries) == 100:
            st.caption(
                "Đang hiển thị 100 trang gần nhất." if is_vi else "Showing your 100 most recent entries."
            )

        for entry in entries:
            entry_id = entry.get("id")
            if entry_id is None:
                continue
            entry_id = str(entry_id)
            label = str(entry.get("title") or ("Trang nhật ký" if is_vi else "Journal entry"))
            formatted_created_at = format_created_at(entry.get("created_at"))
            with st.expander(f"{entry.get('mood', '')} · {label} · {formatted_created_at}"):
                st.write(str(entry.get("content") or ""))
                if st.session_state.get("confirm_delete_diary_id") == entry_id:
                    st.caption(confirm_delete_prompt)
                    delete_col, cancel_col = st.columns(2)
                    if delete_col.button(
                        confirm_delete_label,
                        key=f"confirm_delete_diary_{entry_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        try:
                            (
                                supabase_client.table("diary_entries")
                                .delete()
                                .eq("id", entry_id)
                                .eq("user_id", st.session_state.auth_user_id)
                                .execute()
                            )
                            st.session_state.confirm_delete_diary_id = None
                            st.success(delete_success)
                            st.rerun()
                        except Exception as exc:
                            LOGGER.warning("Journal delete failed: %s", type(exc).__name__)
                            st.error(delete_error)
                    if cancel_col.button(
                        cancel_delete_label,
                        key=f"cancel_delete_diary_{entry_id}",
                        use_container_width=True,
                    ):
                        st.session_state.confirm_delete_diary_id = None
                        st.rerun()
                elif st.button(delete_label, key=f"delete_diary_{entry_id}"):
                    st.session_state.confirm_delete_diary_id = entry_id
                    st.rerun()
    else:
        st.info(empty_label)

    st.caption(privacy_label)

else:
    st.markdown(
        """
        <section class="hero">
          <div class="hero-eyebrow">Không gian an toàn để sẻ chia</div>
          <div class="hero-title">Chào bạn, mình là SkyeChat <span class="hero-tagline">Everything is gonna be alright.</span> ☁️</div>
          <p class="hero-copy">Bạn có thể bắt đầu từ bất cứ điều gì đang ở trong lòng. Mình sẽ lắng nghe, không phán xét.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if is_vi:
        st.header("Trợ lý AI hỗ trợ tâm lý học đường")
        st.text(
            "SkyeChat là không gian lắng nghe dành cho học sinh, sinh viên, giúp bạn chia sẻ cảm xúc "
            "và tìm bước hỗ trợ ban đầu một cách nhẹ nhàng, không phán xét."
        )
    else:
        st.header("AI support for school wellbeing")
        st.text(
            "SkyeChat is a gentle, non-judgmental listening space for students to share how they feel "
            "and explore helpful first steps."
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
    prompt = st.chat_input(placeholder, max_chars=8000, disabled=not ai_is_configured())
    if prompt and prompt.strip():
        prompt = prompt.strip()
        candidate_history = [*st.session_state.messages, {"role": "user", "content": prompt}]
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            with st.chat_message("assistant"):
                with st.spinner("SkyeChat đang lắng nghe..." if is_vi else "SkyeChat is listening..."):
                    reply = st.write_stream(
                        generate_reply(candidate_history, build_system_prompt(is_vi))
                    )
            if not isinstance(reply, str) or not reply.strip():
                raise GeminiAPIError("The configured AI provider returned an empty response.")
            st.session_state.messages = (
                candidate_history + [{"role": "assistant", "content": reply.strip()}]
            )[-MAX_STORED_MESSAGES:]
        except Exception as exc:
            LOGGER.exception("SkyeChat reply generation failed (%s)", type(exc).__name__)
            st.error(friendly_chat_error(exc, is_vi))

st.markdown(
    '<div class="footer">SkyeChat · Lắng nghe bằng sự tử tế · By ThanhAI · since august 2026</div>',
    unsafe_allow_html=True,
)


