# SkyeChat — refreshed Streamlit app

A bilingual (Vietnamese/English) emotional-support companion with Supabase sign-in, email/SMS code verification, a private journal, a streaming Gemini chat, a mood check-in, breathing space, exportable chat history and a light/dark appearance toggle with separate video backgrounds.

## Run locally

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, fill in your Supabase and Gemini values, then start:

```bash
streamlit run app.py
```

On Streamlit Community Cloud, open **App → Settings → Secrets** and paste the equivalent TOML there. Do not upload or commit your real secrets file.

## Required secrets

```toml
SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "YOUR_SUPABASE_PUBLISHABLE_KEY"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_FALLBACK_MODEL = "gemini-3.6-flash"
GEMINI_THINKING_LEVEL = "low"
GEMINI_MAX_OUTPUT_TOKENS = 512
APP_TIMEZONE = "Asia/Ho_Chi_Minh"
```

`SUPABASE_ANON_KEY` is accepted as a legacy alternative to `SUPABASE_PUBLISHABLE_KEY`. Never place a Supabase service-role/secret key in the app.

## Useful tuning

- Chat replies stream token-by-token from the Gemini Interactions API; the HTTP session is reused per Streamlit session.
- Defaults use low-latency `low` thinking, a 512-token output budget and a 75-second read timeout. Adjust `GEMINI_THINKING_LEVEL` or `GEMINI_MAX_OUTPUT_TOKENS` if you need more detailed answers; more reasoning and longer replies usually take longer.
- The app requests stateless interactions (`store: false`) and keeps a bounded conversation history in the Streamlit session, rather than retaining chat messages with Gemini.
- Video sources default to the two HTTPS URLs provided in the original project. Override them with `BACKGROUND_VIDEO_LIGHT_URL` and `BACKGROUND_VIDEO_DARK_URL` secrets, or set either to an empty string to disable that video's source. Videos are muted, decorative, and hidden for users who prefer reduced motion.
- Chat history is held in the current Streamlit session only. Journal entries are stored in Supabase and protected by RLS.

## Setup and security

Read [SUPABASE_SETUP.md](SUPABASE_SETUP.md) for exact email/SMS template settings, SMTP requirements, journal SQL, RLS policies and an end-to-end verification checklist. The reusable SQL is also provided in `supabase/diary_entries.sql`.

## Notes

Supabase and Gemini credentials, external email delivery, phone SMS delivery and internet access are required for their respective features. This code was syntax-checked locally, but real verification and provider delivery must be confirmed with your own Supabase project and service credentials.
