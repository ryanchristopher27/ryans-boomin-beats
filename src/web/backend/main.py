from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from config import SESSION_SECRET_KEY
from routers import search, recommendations, profile, account_analysis
from routers import llm_connect, llm_playlist, spotify_actions, song_profile

app = FastAPI(title="Boomin Beats API")

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin", "")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"},
    )


app.include_router(search.router)
app.include_router(recommendations.router)
app.include_router(profile.router)
app.include_router(account_analysis.router)
app.include_router(llm_connect.router)
app.include_router(llm_playlist.router)
app.include_router(spotify_actions.router)
app.include_router(song_profile.router)
