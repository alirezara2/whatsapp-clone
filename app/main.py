from contextlib import asynccontextmanager
from pathlib import Path
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db

from app.routers import auth
from app.routers import users
from app.routers import contacts
from app.routers import chats
from app.routers import groups
from app.routers import channels
from app.routers import ws
from app.routers import pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("✅ Database initialized")
    yield
    print("👋 Shutting down")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

STATIC_DIR = Path("app/static")
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "uploads" / "avatars").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "uploads" / "messages").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "img").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(contacts.router)
app.include_router(chats.router)
app.include_router(groups.router)
app.include_router(channels.router)
app.include_router(ws.router)
app.include_router(pages.router)


# ---------- Debug exception handler (موقت برای دیباگ) ----------
@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print("\n" + "=" * 70)
    print(f"🔥 ERROR on {request.method} {request.url.path}")
    print(tb)
    print("=" * 70 + "\n")
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"{type(exc).__name__}: {exc}",
            "traceback": tb.splitlines()[-8:],
        },
    )


@app.get("/health")
async def health():
    return {"status": "healthy"}