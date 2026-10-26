        if breathing_active:
            breathing_aria = "Hít vào rồi thở ra" if is_vi else "Breathe in, then out"
            st.markdown(
                f'<div class="breathing-orb" role="img" aria-label="{breathing_aria}"></div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Hít vào 4 giây · Thở ra 6 giây · 6 nhịp" if is_vi
                else "Breathe in 4 seconds · Breathe out 6 seconds · 6 rounds"
            )

    mood_labels = (
        {1: "😔 Nặng nề", 2: "🙁 Hơi khó", 3: "😐 Bình thường", 4: "🙂 Khá ổn", 5: "😊 Dễ chịu"}
        if is_vi
        else {1: "😔 Very hard", 2: "🙁 A bit difficult", 3: "😐 Okay", 4: "🙂 Pretty good", 5: "😊 At ease"}
    )
    mood_value = st.select_slider(
        "Check-in cảm xúc · chỉ lưu trong phiên" if is_vi else "Mood check-in · session only",
        options=(1, 2, 3, 4, 5),
        format_func=lambda value: mood_labels[value],
        key="mood_checkin",
    )
    if st.button(
        "Chia sẻ cảm xúc này" if is_vi else "Share this check-in",
        key="share_mood_checkin",
        use_container_width=True,
        disabled=not ai_is_configured(),
    ):
        st.session_state.queued_support_style = "listen"
        st.session_state.queued_chat_prompt = (
            f"Check-in cảm xúc của mình hôm nay là: {mood_labels[mood_value]}. "
            "Hãy lắng nghe nhẹ nhàng, không suy đoán hay chẩn đoán, và hỏi mình muốn được hỗ trợ thế nào."
            if is_vi
            else f"My mood check-in today is: {mood_labels[mood_value]}. "
            "Please respond gently without making assumptions or diagnosing, and ask how I would like support."
        )
        st.session_state.page_mode = "chat"
        st.rerun()

    if st.session_state.guest_mode:
        st.session_state.page_mode = "chat"
        page_mode = "chat"
        st.caption(
            "Nhật ký riêng cần tài khoản để lưu an toàn."
            if is_vi
            else "A private journal requires an account to save entries securely."
        )
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
        st.info(
            "Thêm `GEMINI_API_KEY` vào Streamlit Secrets để bật trò chuyện với Gemini."
            if is_vi
            else "Add `GEMINI_API_KEY` to Streamlit Secrets to enable Gemini chat."
        )

    st.divider()
    st.markdown("**Nhà phát triển:** ThanhAI" if is_vi else "**Developer:** ThanhAI")
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
            st.session_state.queued_chat_prompt = None
            st.session_state.queued_support_style = None
            st.session_state.confirm_clear_chat = False
            st.rerun()
        if keep_col.button("Giữ lại" if is_vi else "Keep", key="cancel_clear_chat"):
            st.session_state.confirm_clear_chat = False
            st.rerun()

    if st.session_state.messages:
        export_role_names = {"user": "Bạn", "assistant": "SkyeChat"} if is_vi else {"user": "You", "assistant": "SkyeChat"}
        export_text = "\n\n".join(
            f"## {export_role_names.get(item.get('role'), 'SkyeChat')}\n\n{item.get('content', '')}"
            for item in st.session_state.messages
            if isinstance(item, dict) and item.get("role") in export_role_names and isinstance(item.get("content"), str)
        )
        st.download_button(
            "⬇️ Tải hội thoại" if is_vi else "⬇️ Download chat",
            data=f"# SkyeChat\n\n{export_text}\n",
            file_name=f"skyechat_chat_{datetime.now(get_app_timezone()).strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
            help="Bản tải xuống chỉ được tạo khi bạn bấm nút." if is_vi else "The download is created only when you click.",
        )

    st.divider()
    with st.expander("🆘 Cần trợ giúp ngay?" if is_vi else "🆘 Need urgent help?"):
        st.warning(
            (
                "SkyeChat không phải dịch vụ khẩn cấp hay chuyên gia. Nếu bạn có thể bị thương ngay lúc này, hãy đến nơi có người, tránh xa vật có thể gây hại và nhờ một người bạn tin cậy ở bên. Liên hệ dịch vụ khẩn cấp tại nơi bạn sống hoặc đến cơ sở cấp cứu gần nhất."
                if is_vi
                else "SkyeChat is not an emergency service or a professional. If you may be hurt right now, move to a place with other people, put distance between yourself and anything you could use to cause harm, and ask someone you trust to stay with you. Contact local emergency services or go to the nearest emergency department."
            ),
            icon="🫶",
        )
        st.caption(
            "Nếu bạn chưa gặp nguy hiểm tức thời nhưng cần người thật hỗ trợ, hãy liên hệ chuyên gia sức khỏe tâm thần hoặc một người tin cậy. Đừng chờ chatbot trả lời trong tình huống khẩn cấp."
            if is_vi
            else "If there is no immediate danger but you need human support, contact a mental-health professional or someone you trust. Do not wait for a chatbot in an emergency."
        )
    st.caption(
        "Lịch sử chat của SkyeChat chỉ lưu trong phiên trình duyệt hiện tại."
        if is_vi
        else "SkyeChat keeps chat history only for the current browser session."
    )


# A visible account switch keeps guest access discoverable without opening the sidebar.
if is_authenticated or st.session_state.guest_mode:
    _, account_action_col = st.columns([7.4, 2.1])
    with account_action_col:
        account_action = "👤 Đổi người dùng" if is_vi else "👤 Switch user"
        if st.session_state.guest_mode:
            account_action = "👤 Đăng nhập / đổi người dùng" if is_vi else "👤 Sign in / switch user"
        if st.button(account_action, key="top_account_switch", use_container_width=True):
            if is_authenticated:
                try:
                    if supabase_client:
                        supabase_client.auth.sign_out()
                except Exception as exc:
                    LOGGER.warning("Supabase sign out failed: %s", type(exc).__name__)
                clear_auth_state()
            else:
                st.session_state.guest_mode = False
                st.session_state.messages = []
                st.session_state.queued_chat_prompt = None
                st.session_state.queued_support_style = None
                st.session_state.page_mode = "chat"
            st.rerun()
