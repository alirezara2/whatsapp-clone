from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse


router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/app", response_class=HTMLResponse)
async def app_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@router.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse("/login")