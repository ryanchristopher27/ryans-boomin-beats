import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']
REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:5173/profile')
SCOPE = 'user-library-read user-top-read playlist-read-private'
LASTFM_API_KEY = os.environ.get('LASTFM_API_KEY', '')
