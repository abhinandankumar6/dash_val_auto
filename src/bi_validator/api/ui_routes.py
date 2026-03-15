from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bi_validator.core.settings import get_settings

router = APIRouter(include_in_schema=False)
settings = get_settings()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


@router.get("/", response_class=HTMLResponse)
def app_home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "app.html.j2",
        {
            "request": request,
            "app_name": settings.app_name,
            "api_prefix": settings.api_prefix,
            "default_rules_path": "config/rules/default_rules.yaml",
        },
    )
