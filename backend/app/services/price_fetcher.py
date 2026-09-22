import json
import logging

import httpx

from app.services.http_client import NAVER_HTML_HEADERS, client_scope

logger = logging.getLogger(__name__)

_MOBILE_URL = "https://m.stock.naver.com/api/stock/{ticker}/basic"
_POLLING_URL = "https://polling.finance.naver.com/api/realtime"


async def fetch_current_price(
    ticker: str,
    client: httpx.AsyncClient | None = None,
) -> float | None:
    """현재주가 조회. 모바일 API → 폴링 API 순으로 시도한다."""
    async with client_scope(client) as http:
        price = await _fetch_from_mobile_api(ticker, client=http)
        if price is not None:
            return price

        return await _fetch_from_polling_api(ticker, client=http)


async def _fetch_from_mobile_api(ticker: str, client: httpx.AsyncClient | None = None) -> float | None:
    """네이버 모바일 JSON API에서 현재주가를 조회한다."""
    url = _MOBILE_URL.format(ticker=ticker)
    try:
        async with client_scope(client) as http:
            resp = await http.get(url, headers=NAVER_HTML_HEADERS, timeout=8)
            resp.raise_for_status()
            data = resp.json()
        price_str = data.get("closePrice") or data.get("stockPrice")
        if price_str is not None:
            return float(str(price_str).replace(",", ""))
    except Exception as e:
        logger.warning("모바일 API 주가 조회 실패 (ticker=%s): %s", ticker, e)
    return None


async def _fetch_from_polling_api(ticker: str, client: httpx.AsyncClient | None = None) -> float | None:
    """네이버 금융 realtime 폴링 API에서 현재주가를 조회한다."""
    params = {"query": f"SERVICE_ITEM:{ticker}"}
    try:
        async with client_scope(client) as http:
            resp = await http.get(
                _POLLING_URL, params=params, headers=NAVER_HTML_HEADERS, timeout=8
            )
            resp.raise_for_status()
        data = json.loads(resp.content.decode("euc-kr", errors="replace"))
        areas = data.get("result", {}).get("areas", [])
        for area in areas:
            if area.get("name") == "SERVICE_ITEM":
                datas = area.get("datas", [])
                if datas:
                    nv = datas[0].get("nv")
                    if nv is not None:
                        return float(nv)
    except Exception as e:
        logger.warning("폴링 API 주가 조회 실패 (ticker=%s): %s", ticker, e)
    return None
