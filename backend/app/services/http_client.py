from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx


NAVER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://finance.naver.com/",
}
NAVER_HTML_HEADERS = {
    **NAVER_HEADERS,
    "Accept-Language": "ko-KR,ko;q=0.9",
}


@asynccontextmanager
async def client_scope(
    client: httpx.AsyncClient | None,
) -> AsyncIterator[httpx.AsyncClient]:
    """주입된 클라이언트는 재사용하고, 독립 호출일 때만 임시 클라이언트를 만든다."""
    if client is not None:
        yield client
        return

    async with httpx.AsyncClient() as owned_client:
        yield owned_client
