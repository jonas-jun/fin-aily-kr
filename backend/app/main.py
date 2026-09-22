import logging
import sys
from contextlib import asynccontextmanager

import httpx
from google import genai

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import research_router
from app.services.http_client import FOLLOW_REDIRECTS

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    gemini_client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None
    async with httpx.AsyncClient(follow_redirects=FOLLOW_REDIRECTS) as http_client:
        app.state.http = http_client
        app.state.gemini = gemini_client
        try:
            yield
        finally:
            if gemini_client is not None:
                await gemini_client.aio.aclose()
                gemini_client.close()


app = FastAPI(
    title="KRX-Aily API",
    description="한국 주식 리서치 리포트 수집 및 AI 분석",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router.router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "서버 오류가 발생했습니다.", "status": 500}},
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}
