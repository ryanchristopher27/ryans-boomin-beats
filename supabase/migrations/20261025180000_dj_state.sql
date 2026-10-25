-- Shared DJ state, one row per Spotify user (SY1, docs/plan.md).
-- Written only by the backend with the service-role key; clients never touch
-- this table directly.
create table public.dj_state (
  spotify_user_id  text primary key,
  version          bigint      not null default 1,
  state            jsonb       not null,
  primary_device   text,
  primary_label    text,
  primary_seen_at  timestamptz,
  updated_at       timestamptz not null default now()
);

-- Defence in depth: RLS on with no policies denies the anon and authenticated
-- roles entirely. The service role bypasses RLS, which is the only writer.
alter table public.dj_state enable row level security;
