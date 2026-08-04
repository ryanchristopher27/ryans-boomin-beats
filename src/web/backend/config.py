import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']
REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:5173/profile')
SCOPE = 'user-library-read user-top-read playlist-read-private'
LASTFM_API_KEY = os.environ.get('LASTFM_API_KEY', '')

# Shared secret guarding the hosted instance (sent as X-Device-Key). Leave unset
# for the local instance — the guard is a no-op when empty, so localhost dev is
# unaffected. Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
DEVICE_KEY = os.environ.get('DEVICE_KEY', '')

# Browser origins allowed to call this instance. Native clients send no Origin
# and are unaffected by CORS; the hosted instance normally needs no origins at all.
ALLOWED_ORIGINS = [
    o.strip() for o in
    os.environ.get('ALLOWED_ORIGINS', 'http://127.0.0.1:5173').split(',')
    if o.strip()
]
