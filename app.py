# -*- coding: utf-8 -*-
import streamlit as st
import google.generativeai as genai

# ==========================================
# 0. CẤU HÌNH GEMINI API KEY
# ==========================================
# Dán API Key Gemini của em vào giữa 2 dấu ngoặc kép bên dưới:
# ==========================================
# 0. CẤU HÌNH GEMINI API KEY
# ==========================================
GEMINI_API_KEY = "AQ.Ab8RN6I4evp8JpU9GHxHyxdR5Cr-yKKTTYHJcJerarWGyuELqg"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
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
    # Hiển thị Logo
    try:
        st.image("logo.png", use_container_width=True)
    except Exception:
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
        st.session_state.messages = []
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
# 3. TIÊM CSS TÙY CHỈNH (DARK/LIGHT)
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
        [data-testid="stChatMessage"]:nth-child(odd) { background-color: #E3F2FD; border-radius: 15px; padding: 12px; margin-bottom: 10px; }
        [data-testid="stChatMessage"]:nth-child(even) { background-color: #F1F8E9; border-radius: 15px; padding: 12px; margin-bottom: 10px; border-left: 5px solid #8BC34A; }
        @media only screen and (max-width: 600px) { [data-testid="stChatMessage"] { font-size: 14px; padding: 8px; } h1 { font-size: 22px !important; } }
        @media only screen and (min-width: 601px) and (max-width: 1024px) { [data-testid="stChatMessage"] { font-size: 15px; padding: 10px; } }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 4. MÀN HÌNH ĐĂNG KÝ / ĐĂNG NHẬP ẨN DANH
# ==========================================
if not st.session_state.logged_in:
    if st.session_state.lang == "🇻🇳 Tiếng Việt":
        st.title("☁️ Chào mừng bạn đến với SkyeChat")
        st.caption("By **ThanhAI**")
        st.write("Vui lòng tạo một biệt danh ẩn danh để bắt đầu trải nghiệm không gian riêng tư.")
        with st.form("register_form"):
            username_input = st.text_input("👤 Biệt danh (Ví dụ: Đám Mây Nhỏ, Mèo Lười...)", placeholder="Nhập biệt danh...")
            submit_button = st.form_submit_button("Bắt đầu trò chuyện 🚀")
            if submit_button:
                if username_input.strip() == "":
                    st.error("Vui lòng nhập biệt danh để tiếp tục!")
                else:
                    st.session_state.username = username_input
                    st.session_state.logged_in = True
                    st.rerun()
    else:
        st.title("☁️ Welcome to SkyeChat")
        st.caption("By **ThanhAI**")
        st.write("Please create an anonymous nickname to enter your private safe space.")
        with st.form("register_form"):
            username_input = st.text_input("👤 Nickname (e.g., Little Cloud, Lazy Cat...)", placeholder="Enter your nickname...")
            submit_button = st.form_submit_button("Start Chatting 🚀")
            if submit_button:
                if username_input.strip() == "":
                    st.error("Please enter a nickname to proceed!")
                else:
                    st.session_state.username = username_input
                    st.session_state.logged_in = True
                    st.rerun()

# ==========================================
# 5. MÀN HÌNH CHAT CHÍNH
# ==========================================
else:
    is_vi = st.session_state.lang == "🇻🇳 Tiếng Việt"
    
    # Tiêu đề & Cảnh báo an toàn
    title_text = f"☁️ Chào {st.session_state.username}, mình là SkyeChat!" if is_vi else f"☁️ Hello {st.session_state.username}, I'm SkyeChat!"
    warning_text = "🚨 SkyeChat luôn giữ bí mật cuộc trò chuyện. Nếu bạn đang gặp khủng hoảng khẩn cấp, vui lòng gọi ngay Tổng đài Quốc gia: 111" if is_vi else "🚨 SkyeChat keeps conversations completely confidential. In case of emergency, please reach out to your local helpline immediately."
    
    st.title(title_text)
    st.caption("By **ThanhAI**")
    st.warning(warning_text)
    
    # Thanh bên Sidebar (Đăng xuất)
    with st.sidebar:
        user_label = f"👤 Đang đăng nhập: **{st.session_state.username}**" if is_vi else f"👤 Logged in as: **{st.session_state.username}**"
        logout_label = "🚪 Đăng xuất" if is_vi else "🚪 Log out"
        
        st.write(user_label)
        if st.button(logout_label):
            st.session_state.logged_in = False
            st.session_state.messages = []
            st.rerun()

    # Hiển thị lịch sử trò chuyện
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Ô nhập tin nhắn
    chat_placeholder = f"{st.session_state.username} đang nghĩ gì thế? Hãy chia sẻ nhé..." if is_vi else f"What's on your mind, {st.session_state.username}? Share with me..."
    
    if prompt := st.chat_input(chat_placeholder):
        
        # User nhắn
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI Trả lời qua Gemini
        with st.chat_message("assistant"):
            try:
                # 1. Thiết lập System Prompt chỉ dẫn tâm lý cho Gemini
                sys_instruction = SYSTEM_PROMPT_VI if is_vi else SYSTEM_PROMPT_EN
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=sys_instruction
                )

                # 2. Chuyển đổi lịch sử cuộc trò chuyện sang định dạng Gemini
                gemini_history = []
                for msg in st.session_state.messages[:-1]:  # Bỏ qua tin nhắn user mới nhất
                    role_gemini = "user" if msg["role"] == "user" else "model"
                    gemini_history.append({"role": role_gemini, "parts": [msg["content"]]})

                # 3. Gửi câu hỏi và nhận câu trả lời
                chat = model.start_chat(history=gemini_history)
                response = chat.send_message(prompt)
                bot_reply = response.text
                
                st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                
            except Exception as e:
                st.error(f"❌ Đã xảy ra lỗi kết nối Gemini API: {e}")
  
