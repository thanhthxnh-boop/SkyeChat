# SkyeChat — Supabase setup

This app uses Supabase Auth for accounts and a `public.diary_entries` table for the private journal. It does **not** need a Supabase service-role key. Use the project's publishable key (or legacy anon key) with Row Level Security enabled.

## 1. Add the project credentials

In Supabase Dashboard, open **Project Settings → API** and copy:

- Project URL, e.g. `https://YOUR_PROJECT_REF.supabase.co` (the project root only; do not append `/rest/v1` or `/auth/v1`).
- Publishable key. The app also accepts the legacy anon key.

Add these to `.streamlit/secrets.toml` locally or to your Streamlit host's Secrets settings:

```toml
SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "YOUR_PUBLISHABLE_KEY"
```

Never use a service-role/secret key in this app. Do not commit a real `secrets.toml` to Git.

## 2. Configure email confirmation

In **Authentication → Sign In / Providers → Email**:

1. Enable Email.
2. Enable email confirmation so the app's verification-code screen is used for new email signups.
3. Open **Authentication → Email Templates → Confirm signup**. This app expects a code the user can copy into the app, rather than a confirmation link. Include `{{ .Token }}`, for example:

   **Subject:** `Your SkyeChat verification code`

   ```html
   <h2>Confirm your email</h2>
   <p>Your SkyeChat verification code is <strong>{{ .Token }}</strong>.</p>
   <p>If you did not request this code, you can ignore this email.</p>
   ```

4. Open **Authentication → Email Templates → Reset password** and include `{{ .Token }}` as well, because the app asks users to enter a reset code:

   ```html
   <h2>Reset your password</h2>
   <p>Your SkyeChat password-reset code is <strong>{{ .Token }}</strong>.</p>
   <p>If you did not request this code, you can ignore this email.</p>
   ```

The code calls `verify_otp` with type `email` for email confirmation and `recovery` for password recovery. The Magic Link / OTP template should also use `{{ .Token }}` if you later add email-based passwordless sign-in.

### Configure production email delivery

Supabase's built-in sender is for testing: it only sends to pre-authorized team addresses and has a low, changeable sending limit (currently documented as 2 messages/hour). For real users, configure a custom SMTP provider in **Authentication settings**. Verify your sender domain and set SPF, DKIM and DMARC records. Check spam folders and Supabase Auth logs when delivery fails. Keep the subject and body simple and avoid changing the OTP to a confirmation link unless you also implement link handling in the app.

## 3. Configure phone verification (SMS)

In **Authentication → Sign In / Providers → Phone**:

1. Enable Phone.
2. Enable phone confirmation for signups.
3. Configure a supported SMS provider (for example Twilio, MessageBird or Vonage) with its real production credentials and sender/service ID, then save.
4. In **Authentication → Templates → SMS**, ensure your SMS body includes `{{ .Code }}`, for example: `Your SkyeChat verification code is {{ .Code }}`.
5. Set sensible OTP expiry and send-rate limits. Before enabling Supabase CAPTCHA, add a compatible CAPTCHA component that obtains a per-user token and passes it to each relevant Supabase Auth request. This Streamlit build does not yet collect/pass CAPTCHA tokens, so enabling CAPTCHA without that integration can block sign-up and OTP requests.

Enter numbers in international E.164 format. For Vietnam, use `+84` followed by the subscriber number without the domestic leading `0`, for example `+84901234567`. The app normalizes spaces, parentheses, periods and hyphens but intentionally requires a leading `+` country code.

The app uses `type: "sms"` when verifying a phone signup or phone OTP login. OTP delivery still depends on a correctly configured provider, provider account status/balance, destination-country support, sender registration and rate limits.

## 4. Create and secure the journal table

If you do **not** already have `public.diary_entries`, run this once in **SQL Editor**. The table matches the columns expected by `app.py`.

```sql
create table if not exists public.diary_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default '',
  mood text not null default '',
  content text not null check (char_length(content) <= 5000),
  created_at timestamptz not null default now()
);

create index if not exists diary_entries_user_created_at_idx
  on public.diary_entries (user_id, created_at desc);

alter table public.diary_entries enable row level security;

-- This app only needs authenticated SELECT, INSERT and DELETE.
revoke all on table public.diary_entries from anon, authenticated;
grant select, insert, delete on table public.diary_entries to authenticated;

drop policy if exists "diary_entries_select_own" on public.diary_entries;
create policy "diary_entries_select_own"
  on public.diary_entries for select to authenticated
  using ((select auth.uid()) is not null and (select auth.uid()) = user_id);

drop policy if exists "diary_entries_insert_own" on public.diary_entries;
create policy "diary_entries_insert_own"
  on public.diary_entries for insert to authenticated
  with check ((select auth.uid()) is not null and (select auth.uid()) = user_id);

drop policy if exists "diary_entries_delete_own" on public.diary_entries;
create policy "diary_entries_delete_own"
  on public.diary_entries for delete to authenticated
  using ((select auth.uid()) is not null and (select auth.uid()) = user_id);
```

If the table already exists, compare its columns and existing grants/policies instead of assuming `create table if not exists` changes its structure. Remove any overly broad policies that let users read or change rows belonging to another user. RLS and grants must both be correct.

## 5. Set URL configuration

In **Authentication → URL Configuration**, set Site URL to the actual deployed app's canonical HTTPS origin if you use email confirmation links or add redirects later. This app's current verification UX uses copy-and-paste codes (`{{ .Token }}`), so it does not rely on a Supabase confirmation link returning to the Streamlit page.

## 6. Test end to end

1. Sign up with an email address you can access. Confirm that the email contains a visible code, enter it in SkyeChat, and verify that the app signs you in.
2. Request password recovery, confirm the email contains a code, enter it, and set a new password.
3. Sign up with a phone number in E.164 format. Confirm the SMS arrives, enter the code, and verify that the app signs you in.
4. Create a journal entry, sign out and back in, and confirm the entry is still there.
5. If possible, create a second test account and verify it cannot see or delete the first account's journal entries.

## Troubleshooting

- **Email address not authorized / email doesn't send:** configure custom SMTP; the default sender is only for testing.
- **Code not visible in email:** edit Confirm signup and Reset password templates to include `{{ .Token }}`.
- **SMS doesn't arrive:** verify Phone is enabled and confirmed, provider credentials are live/correct, the destination country is supported, the number is E.164, and provider quotas/rate limits are not exhausted.
- **Journal permission error:** check RLS is enabled, the three own-row policies exist, and the logged-in client is using the publishable/anon key plus the user's real Auth session.
- **Do not fix delivery problems by disabling confirmations or exposing the service-role key.**
