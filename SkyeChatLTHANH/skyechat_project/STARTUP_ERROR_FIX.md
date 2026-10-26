# Fix: `IndentationError: unexpected indent` at line 1

The screenshot shows Streamlit loading a file whose first line is an indented fragment:

```python
    if breathing_active:
```

That fragment belongs inside SkyeChat's breathing-expander block; it must not be the first line of `app.py`. In the complete app it appears inside the main UI at approximately line 1377, nested under `with st.expander(...)` and after the `breathing_active = st.toggle(...)` assignment.

## Recommended repair

1. Replace the repository's entire `app.py` with `skyechat_project/app.py` from this package. Do not copy only the breathing snippet into `app.py`.
2. Commit and push the replacement file to the branch deployed by Streamlit Community Cloud.
3. In Streamlit Community Cloud, verify **Main file path** points to `app.py` at the project root (or set it to `skyechat_project/app.py` if the project was not unpacked and the nested folder is the repository root).
4. Restart/reboot the app. If the error persists, inspect the deployed repository's first 10 lines; the first line should be `import os`, not `if breathing_active:`.

## Local syntax check

Run this from the directory containing `app.py`:

```bash
python -m py_compile app.py
```

A successful compile exits without output. This checks syntax only; it does not validate credentials or live Supabase, SMS, email, or Gemini connectivity.
