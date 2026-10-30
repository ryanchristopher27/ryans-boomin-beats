-- Each Spotify user's plays, kept past Spotify's 50-play recently-played window
-- so Profile can show weeks and months of listening. Rows come from upserting
-- recently-played on Profile visits and while the DJ page is open; a play is
-- identified by its timestamp, so repeats are ignored. Written and read only by
-- the backend (service role).
create table public.listening_history (
  spotify_user_id  text        not null,
  played_at        timestamptz not null,
  track_id         text        not null,
  title            text        not null default '',
  artist           text        not null default '',
  duration_ms      integer     not null default 0,
  primary key (spotify_user_id, played_at)
);

-- Defence in depth, as for dj_state: RLS on, no policies.
alter table public.listening_history enable row level security;
