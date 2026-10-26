from fastapi import APIRouter, HTTPException, Query

from services import deezer

router = APIRouter()


@router.get("/search/")
async def search(searchValue: str = Query(..., min_length=1, max_length=200)):
    """Type-ahead on Deezer since Q3: no Spotify quota per keystroke. Results
    carry an ISRC key; the chosen one resolves via POST /tracks/resolve/."""
    try:
        songs = await deezer.client().search(searchValue, limit=10)
    except deezer.DeezerUnavailable:
        raise HTTPException(status_code=503, detail="Search isn't available right now. Try again in a moment.")
    return {'type': 'searchSongs', 'tracks': [deezer.as_track(s) for s in songs]}
