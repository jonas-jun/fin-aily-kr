import logging

import httpx

from app.services.http_client import NAVER_HEADERS, client_scope

logger = logging.getLogger(__name__)

_AC_URL = "https://ac.stock.naver.com/ac"


async def search_tickers(
    query: str,
    limit: int = 10,
    client: httpx.AsyncClient | None = None,
) -> list[dict]:
    """
    네이버 증권 자동완성 API로 국내 주식 종목 검색.
    반환: [{"ticker": "005930", "name": "삼성전자", "market": "KOSPI"}, ...]
    """
    params = {"q": query, "target": "stock"}
    try:
        async with client_scope(client) as http:
            resp = await http.get(_AC_URL, params=params, headers=NAVER_HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error("종목 검색 API 요청 실패: %s", e)
        return []

    results = []
    for item in data.get("items", []):
        if item.get("nationCode") != "KOR":
            continue
        results.append({
            "ticker": item["code"],
            "name": item["name"],
            "market": item.get("typeName", ""),
        })
        if len(results) >= limit:
            break

    return results
