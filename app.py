import os
import requests
import streamlit as st

# Kiểm tra file logo (.png hoặc .jpg)
logo_file = None
for file_name in ["logo.png", "logo.jpg", "Logo.png", "Logo.jpg"]:
  if os.path.exists(file_name):
    logo_file = file_name
    break

# 1. Cấu hình trang Streamlit
st.set_page_config(
    page_title="SkyeChat - Sơ cứu tâm lý học đường",
    page_icon=logo_file if logo_file else "☁️️",
    layout="wide",
)

# 2. Mã API Key (Dùng mã AQ... của em)
GEMINI_API_KEY = "AQ.Ab8RN6I9wtOccQSGABf5TWTsNLrPoU1O3yRruqPAGpAFqzO2dA"

# 3. System Prompts
SYSTEM_PROMPT_VI = """Bạn là SkyeChat, một trợ lý AI thân thiện, cởi mở, không phán xét, chuyên hỗ trợ sơ cứu tâm lý học đường và lắng nghe học sinh, sinh viên. Hãy lắng nghe và phản hồi bằng tiếng Việt ấm áp, chu đáo."""
SYSTEM_PROMPT_EN = """You are SkyeChat, a friendly, open, non-judgmental AI assistant specializing in school psychological first aid and listening to students. Respond with care and empathy."""

# 4. Khởi tạo Session State
if "messages" not in st.session_state:
  st.session_state.messages = []

if "nickname" not in st.session_state:
  st.session_state.nickname = "Bạn"

# 5. Thanh Sidebar bên trái
with st.sidebar:
  if logo_file:
    st.image(logo_file, width=150)

  st.title("⚙️ Cấu hình SkyeChat")

  nickname_input = st.text_input(
      "Biệt danh của bạn:", value=st.session_state.nickname
  )
  if nickname_input:
    st.session_state.nickname = nickname_input

  st.success(f"👋 Chào mừng **{st.session_state.nickname}**!")

  lang = st.radio("Ngôn ngữ / Language:", ["Tiếng Việt 🇻🇳", "English 🇬🇧"])
  is_vi = "Tiếng Việt" in lang

  st.divider()
  st.markdown("👨‍💻 **Nhà phát triển:** ThanhAI")

  if st.button("🗑️ Xóa lịch sử trò chuyện"):
    st.session_state.messages = []
    st.rerun()

  st.markdown("---")
  st.warning(
      "⚠️ **Lưu ý an toàn:** SkyeChat hỗ trợ sơ cứu tâm lý ban đầu. Trong"
      " trường hợp khủng hoảng nghiêm trọng, vui lòng liên hệ ngay người thân"
      " hoặc tổng đài bảo vệ trẻ em **111**."
  )

# 6. Khung chat chính (Header)
col1, col2 = st.columns([1, 8])
with col1:
  if logo_file:
    st.image(logo_file, width=70)
  else:
    st.write("☁️")
with col2:
  st.title("SkyeChat")

st.caption(
    "Trợ lý AI hỗ trợ sơ cứu tâm lý học đường | Phát triển bởi **ThanhAI**"
)

# Hiển thị các tin nhắn đã gửi
for message in st.session_state.messages:
  with st.chat_message(message["role"]):
    st.markdown(message["content"])

# 7. Nhập tin nhắn & Gọi Gemini REST API
placeholder = (
    "Hãy chia sẻ với SkyeChat..."
    if is_vi
    else "Share your thoughts with SkyeChat..."
)
if prompt := st.chat_input(placeholder):
  st.session_state.messages.append({"role": "user", "content": prompt})
  with st.chat_message("user"):
    st.markdown(prompt)

  with st.chat_message("assistant"):
    with st.spinner("SkyeChat đang suy nghĩ..."):
      try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

        contents = []
        for msg in st.session_state.messages:
          role_name = "user" if msg["role"] == "user" else "model"
          contents.append(
              {"role": role_name, "parts": [{"text": msg["content"]}]}
          )

        sys_prompt = SYSTEM_PROMPT_VI if is_vi else SYSTEM_PROMPT_EN
        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": sys_prompt}]},
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        res_data = response.json()

        if response.status_code == 200:
          bot_reply = res_data["candidates"][0]["content"]["parts"][0]["text"]
          st.markdown(bot_reply)
          st.session_state.messages.append(
              {"role": "assistant", "content": bot_reply}
          )
        else:
          err_msg = res_data.get("error", {}).get(
              "message", "Lỗi không xác định"
          )
          st.error(f"❌ Lỗi API ({response.status_code}): {err_msg}")

      except Exception as e:
        st.error(f"❌ Lỗi kết nối: {e}")
