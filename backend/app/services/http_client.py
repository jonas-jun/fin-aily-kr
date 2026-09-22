from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx


# httpx는 기본적으로 리다이렉트를 따라가지 않고, raise_for_status()는 3xx에서도 예외를
# 던진다. 네이버는 레거시 경로를 신규 도메인으로 302 이관하는 일이 잦아, 끄고 두면 이관된
# 엔드포인트가 전부 실패한다. 우리가 만드는 클라이언트는 항상 켠다 (주입된 클라이언트는
# 호출부 책임이다).
# 주의: 이것만으로 조용한 실패가 막히지는 않는다 — 실제 방어는 수집 실패를 빈 리스트가
# 아닌 예외(ReportFetchError)로 올리는 쪽이다.
FOLLOW_REDIRECTS = True

NAVER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://finance.naver.com/",
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
