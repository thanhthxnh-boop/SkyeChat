-- Run once if public.diary_entries does not exist yet.
-- If you already have this table, compare its columns and existing policies before applying.

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
