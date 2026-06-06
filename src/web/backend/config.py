import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']
REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:5173/profile')
SESSION_SECRET_KEY = os.environ.get('SESSION_SECRET_KEY', 'boomin-beats-dev-secret-key')
SCOPE = 'user-library-read user-top-read playlist-read-private'
LASTFM_API_KEY = os.environ.get('LASTFM_API_KEY', '')
