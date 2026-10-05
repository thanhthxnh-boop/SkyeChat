import streamlit as st
import google.generativeai as genai

# ==========================================
# 0. CẤU HÌNH GEMINI API KEY
# ==========================================
# Dán API Key Gemini của em (dạng AQ... hoặc AIza...) vào giữa 2 dấu ngoặc kép ở dưới:
GEMINI_API_KEY = "AQ.Ab8RN6L1Bm4Vv2BJkJWLKTpmqhApxWXceHjuBLwfor6_vBBm8A"

if GEMINI_API_KEY and GEMINI_API_KEY != "DÁN_GEMINI_API_KEY_CỦA_EM_VÀO_ĐÂY":
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("⚠️ Vui lòng dán API Key Gemini của em vào dòng GEMINI_API_KEY ở đầu file app.py!")

# ==========================================
# 1. CẤU HÌNH TRANG CHUNG
# ==========================================
st.set_page_config(
    page_title="SkyeChat - Hỗ trợ tâm lý", 
    page_icon="☁️", 
    layout="centered"
)

# Khởi tạo bộ nhớ tạm (Session State)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "lang" not in st.session_state:
    st.session_state.lang = "🇻🇳 Tiếng Việt"
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# 2. THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR) & NÚT SONG NGỮ
# ==========================================
with st.sidebar:
    # 1. Hiển thị Logo
    try:
        st.image("logo.png", use_container_width=True)
    except:
        pass
        
    st.markdown("### ☁️ SkyeChat")
    st.caption("✨ Developed by **ThanhAI**")
    
    st.markdown("---")
    
    # NÚT CHỌN NGÔN NGỮ SONG NGỮ
    selected_lang = st.selectbox(
        "🌐 Ngôn ngữ / Language", 
        ["🇻🇳 Tiếng Việt", "🇬🇧 English"],
        index=0 if st.session_state.lang == "🇻🇳 Tiếng Việt" else 1
    )
    
    # Nếu đổi ngôn ngữ thì reset lại hệ thống
    if selected_lang != st.session_state.lang:
        st.session_state.lang = selected_lang
        st.session_state.messages = [] # Xóa lịch sử cũ để đổi kịch bản ngôn ngữ mới
        st.rerun()

    # Nội dung Sidebar theo ngôn ngữ đã chọn
    if st.session_state.lang == "🇻🇳 Tiếng Việt":
        st.info("Dự án KHKT: Ứng dụng AI hỗ trợ sơ cứu tâm lý học đường.")
        st.markdown("---")
        st.markdown("### ⚙️ Tùy chỉnh giao diện")
        dark_mode_toggle = st.toggle("🌙 Chế độ tối (Dark Mode)", value=st.session_state.dark_mode)
        st.markdown("---")
        st.markdown("**Nguyên tắc:**\n- Trò chuyện cởi mở\n- Ẩn danh tuyệt đối\n- Không phán xét")
    else:
        st.info("Science Project: AI Application for School Psychological First Aid.")
        st.markdown("---")
        st.markdown("### ⚙️ Appearance")
        dark_mode_toggle = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
        st.markdown("---")
        st.markdown("**Principles:**\n- Open conversation\n- Completely anonymous\n- Non-judgmental")

    if dark_mode_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode_toggle
        st.rerun()

# Cấu hình Prompt tâm lý theo ngôn ngữ
SYSTEM_PROMPT_VI = "Bạn là SkyeChat, một người bạn thấu cảm, hỗ trợ học sinh giải tỏa căng thẳng. Tuyệt đối không chẩn đoán y khoa, không khuyên dùng thuốc, không dập khuôn. Hãy xưng 'mình' và gọi người dùng là 'bạn'. Nhiệm vụ của bạn là lắng nghe, công nhận cảm xúc và đặt 1 câu hỏi mở ngắn gọn để họ giãi bày."
SYSTEM_PROMPT_EN = "You are SkyeChat, an empathetic friend supporting students to relieve stress. Never provide medical diagnosis or medication advice. Call yourself 'I' or 'SkyeChat' and address the user warmly. Your goal is to listen, validate feelings, and ask 1 short open-ended question to help them open up."

# ==========================================
# 3. TIÊM CSS TÙY CHỈNH (DARK/LIGHT + RESPONSIVE)
# ==========================================
if st.session_state.dark_mode:
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #121212; color: #FFFFFF; }
        [data-testid="stChatMessage"]:nth-child(odd) { background-color: #2C2C2C; border-radius: 15px; padding: 12px; margin-bottom: 10px; }
        [data-testid="stChatMessage"]:nth-child(even) { background-color: #1E3A28; border-radius: 15px; padding: 12px; margin-bottom: 10px; border-left: 5px solid #4CAF50; }
        h1, h2, h3, p, span { color: #E0E0E0 !important; }
        @media only screen and (max-width: 600px) { [data-testid="stChatMessage"] { font-size: 14px; padding: 8px; } h1 { font-size: 22px !important; } }
        @media only screen and (min-width: 601px) and (max-width: 1024px) { [data-testid="stChatMessage"] { font-size: 15px; padding: 10px; } }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #F9FBF9; color: #2E3B32; }
        [data-testid="stChatMessage"]:nth-child(odd