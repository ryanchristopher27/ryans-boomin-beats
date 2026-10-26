-- Shared cache of Spotify search results (song + artist -> track), so the
-- DJ's validation doesn't re-search songs any instance or device already
-- looked up. Spotify's Development Mode search quota is daily and shared by
-- the whole developer account. Written only by the backend (service role).
create table public.track_lookup (
  key         text primary key,          -- sha256 of casefolded title|artist|fallback
  track       jsonb,                     -- the formatted track, or null for "no match"
  created_at  timestamptz not null default now()
);

create index track_lookup_created_at on public.track_lookup (created_at);

-- Defence in depth, as for dj_state: RLS on, no policies.
alter table public.track_lookup enable row level security;
