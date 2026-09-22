from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx


# 네이버는 레거시 경로를 신규 도메인으로 302 이관하는 일이 잦다. 리다이렉트를 따라가지
# 않으면 302 본문(0 byte)을 정상 응답으로 오인하게 되므로 항상 follow_redirects를 켠다.
FOLLOW_REDIRECTS = True

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

    async with httpx.AsyncClient(follow_redirects=FOLLOW_REDIRECTS) as owned_client:
        yield owned_client
