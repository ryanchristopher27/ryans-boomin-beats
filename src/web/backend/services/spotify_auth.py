"""Spotify user token, read from the Authorization header.

Previously the token travelled as an `access_token` query parameter (GET) or a
body field (POST). Query strings are recorded verbatim in access logs, by any
proxy in front of the app, and by the hosting platform — so a token in the URL
leaks to places you cannot scrub. A bearer header keeps it out of the request
line, and matches what the iOS client will send.
"""
from fastapi import Header, HTTPException

_NOT_LOGGED_IN = 'Log in to Spotify on the Profile page first.'


def get_spotify_token(authorization: str | None = Header(default=None)) -> str:
    """Extract a bearer token, or 401 with the message the frontend expects."""
    if not authorization:
        raise HTTPException(status_code=401, detail=_NOT_LOGGED_IN)
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        raise HTTPException(status_code=401, detail=_NOT_LOGGED_IN)
    return token.strip()
