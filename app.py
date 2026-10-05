import streamlit as st
import requests

# 1. Cấu hình trang Streamlit
st.set_page_config(page_title="SkyeChat", page_icon="☁️", layout="centered")

# 2. Khai báo API Key (AQ.Ab8RN6I9wtOccQSGABf5TWTsNLrPoU1O3yRruqPAGpAFqzO2dA)
GEMINI_API_KEY = "AQ..."  # Thay bằng mã API Key của em

# 3. System Prompt
SYSTEM_PROMPT = """Bạn là SkyeChat, một trợ lý AI thân thiện, cởi mở, không phán xét, chuyên hỗ trợ tâm lý và lắng nghe người dùng."""

st.title("☁️ SkyeChat")
st.caption("Ứng dụng AI hỗ trợ sơ cứu tâm lý học đường.")

# 4. Khởi tạo lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. Hiển thị lại các tin nhắn cũ
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. Xử lý khi người dùng gửi tin nhắn
if prompt := st.chat_input("Hãy chia sẻ với SkyeChat..."):
    # Hiển thị tin nhắn người dùng
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gọi Gemini REST API
    with st.chat_message("assistant"):
        with st.spinner("SkyeChat đang suy nghĩ..."):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
                
                # Chuẩn bị dữ liệu lịch sử cuộc trò chuyện
                contents = []
                for msg in st.session_state.messages:
                    role_name = "user" if msg["role"] == "user" else "model"
                    contents.append({"role": role_name, "parts": [{"text": msg["content"]}]})

                payload = {
                    "contents": contents,
                    "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]}
                }

                headers = {"Content-Type": "application/json"}
                response = requests.post(url, json=payload, headers=headers)
                res_data = response.json()

                if response.status_code == 200:
                    bot_reply = res_data["candidates"][0]["content"]["parts"][0]["text"]
                    st.markdown(bot_reply)
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                else:
                    err_msg = res_data.get("error", {}).get("message", "Lỗi không xác định")
                    st.error(f"❌ Lỗi từ Gemini API ({response.status_code}): {err_msg}")

            except Exception as e:
                st.error(f"❌ Lỗi kết nối: {e}")
