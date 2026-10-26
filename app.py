        st.header("An AI companion for emotional wellbeing")
        st.text(
            "SkyeChat is a warm listening space to help you make sense of what you are experiencing "
            "and find a gentle next step that fits you."
        )

    st.caption(
        "Vì quyền riêng tư của bạn, đừng chia sẻ mật khẩu, địa chỉ nhà hoặc thông tin nhận dạng nhạy cảm."
        if is_vi
        else "For your privacy, do not share passwords, home addresses, or sensitive identifying information."
    )

    if not st.session_state.messages:
        if is_vi:
            st.markdown(
                """
                <div class="welcome-card">
                  <strong>Đây là không gian của bạn.</strong><br>
                  Bạn không cần phải tìm đúng từ ngữ. Hãy kể một điều nhỏ đang khiến bạn bận tâm,
                  hoặc chỉ cần nói hôm nay bạn cảm thấy thế nào.
                  <div class="soft-note soft-note--spaced">Mình ở đây để lắng nghe, từng chút một.</div>
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
                  <div class="soft-note soft-note--spaced">I’m here to listen, one step at a time.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    for message in st.session_state.messages:
        message_role = message.get("role")
        if message_role not in ("user", "assistant"):
            continue
        avatar = CHAT_AVATAR if message_role == "assistant" else USER_AVATAR
        with st.chat_message(message_role, avatar=avatar):
            st.markdown(message["content"])

    if not st.session_state.messages:
        starter_prompts = (
            [
                ("🫶 Chỉ cần lắng nghe", "Mình chưa cần lời khuyên, chỉ muốn được lắng nghe một chút."),
                ("🧭 Gỡ rối suy nghĩ", "Có vài điều đang rối trong đầu mình. Giúp mình nhìn từng phần nhé."),
                ("🌱 Tìm bước nhỏ", "Mình đang gặp chuyện khó. Cùng tìm một bước nhỏ mình có thể làm nhé."),
            ]
            if is_vi
            else [
                ("🫶 Just listen", "I do not need advice yet; I would just like to be heard for a moment."),
                ("🧭 Untangle my thoughts", "A few things feel tangled in my mind. Could you help me look at them one at a time?"),
                ("🌱 Find a small step", "I am dealing with something hard. Can we find one small step I could take?"),
            ]
        )
        quick_cols = st.columns(3)
        for index, (label, starter_prompt) in enumerate(starter_prompts):
            if quick_cols[index].button(label, key=f"quick_start_{index}", use_container_width=True, disabled=not ai_is_configured()):
                st.session_state.queued_chat_prompt = starter_prompt
                st.session_state.queued_support_style = ("listen", "untangle", "next_step")[index]
                st.rerun()

    queued_prompt = st.session_state.pop("queued_chat_prompt", None)
    placeholder = "Hãy chia sẻ với SkyeChat..." if is_vi else "Share your thoughts with SkyeChat..."
    chat_input_prompt = st.chat_input(placeholder, max_chars=5000, disabled=not ai_is_configured())
    prompt = queued_prompt or chat_input_prompt
    if prompt and prompt.strip():
        prompt = prompt.strip()
        candidate_history = [*st.session_state.messages, {"role": "user", "content": prompt}]
        # Keep the user's turn even if Gemini is temporarily unavailable.
        st.session_state.messages = candidate_history[-MAX_STORED_MESSAGES:]
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)

        try:
            with st.chat_message("assistant", avatar=CHAT_AVATAR):
                with st.spinner("SkyeChat đang lắng nghe..." if is_vi else "SkyeChat is listening..."):
                    reply = st.write_stream(
                        generate_reply(
                            candidate_history,
                            build_system_prompt(is_vi, st.session_state.support_style),
                        )
                    )
            if not isinstance(reply, str) or not reply.strip():
                raise GeminiAPIError("The configured AI provider returned an empty response.")
            st.session_state.messages = (
                candidate_history + [{"role": "assistant", "content": reply.strip()}]
            )[-MAX_STORED_MESSAGES:]
        except Exception as exc:
            LOGGER.exception("SkyeChat reply generation failed (%s)", type(exc).__name__)
            st.error(friendly_chat_error(exc, is_vi))

footer_text = (
    "SkyeChat · Lắng nghe bằng sự tử tế · By ThanhAI · từ tháng 8 năm 2026"
    if is_vi
    else "SkyeChat · Listening with kindness · By ThanhAI · since August 2026"
)
st.markdown(
    f'<div class="footer">{footer_text}</div>',
    unsafe_allow_html=True,
)
