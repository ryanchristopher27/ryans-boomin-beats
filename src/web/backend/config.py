import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
# Market for choose-time Spotify lookups (plan Q1): the version returned must be
# playable here. A fixed market because `from_token` needs the user-read-private
# scope, which the apps don't request (Q4 live check: 403).
SPOTIFY_MARKET = os.environ.get('SPOTIFY_MARKET', 'US')
CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']
REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:5173/profile')
SCOPE = 'user-library-read user-top-read playlist-read-private'
LASTFM_API_KEY = os.environ.get('LASTFM_API_KEY', '')

# Shared secret guarding the hosted instance (sent as X-Device-Key). Leave unset
# for the local instance — the guard is a no-op when empty, so localhost dev is
# unaffected. Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
DEVICE_KEY = os.environ.get('DEVICE_KEY', '')

# The hosted web app can't hold the device key (its code is public), so the
# guard also accepts a Spotify bearer token from one of these Spotify user ids
# (comma-separated). Required: any Spotify account can mint a valid token, so
# without the list the guard would admit everyone. Unset = bearer path off.
ALLOWED_SPOTIFY_USERS = {
    u.strip() for u in os.environ.get('ALLOWED_SPOTIFY_USERS', '').split(',') if u.strip()
}

# DJ sync (SY1). Both local and hosted instances point at the same Supabase
# project, so devices on either one share state. Unset = sync disabled; the
# rest of the backend runs unchanged and sync routes answer 503.
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
SYNC_ENABLED = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)

# Browser origins allowed to call this instance. Native clients send no Origin
# and are unaffected by CORS; the hosted instance normally needs no origins at all.
ALLOWED_ORIGINS = [
    o.strip() for o in
    os.environ.get('ALLOWED_ORIGINS', 'http://127.0.0.1:5173').split(',')
    if o.strip()
]
