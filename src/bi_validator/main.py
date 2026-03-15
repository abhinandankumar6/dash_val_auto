from __future__ import annotations

from fastapi import FastAPI

from bi_validator.api.routes import router
from bi_validator.api.ui_routes import router as ui_router
from bi_validator.core.logging import configure_logging
from bi_validator.core.settings import get_settings
from bi_validator.core.utils import ensure_directory
from bi_validator.db.base import Base
from bi_validator.db.session import engine

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    ensure_directory(settings.report_root)
    ensure_directory(settings.screenshot_root)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)


app.include_router(ui_router)
app.include_router(router, prefix=settings.api_prefix)
