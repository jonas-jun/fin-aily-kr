import json
import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_MAIN_URL = "https://finance.naver.com/item/main.naver?code={ticker}"
_MOBILE_URL = "https://m.stock.naver.com/api/stock/{ticker}/basic"
_POLLING_URL = "https://polling.finance.naver.com/api/realtime"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://finance.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


async def fetch_current_price(ticker: str) -> float | None:
    """현재주가 조회. 네이버 메인 페이지 → 모바일 API → 폴링 API 순으로 시도한다."""
    price = await _fetch_from_main_page(ticker)
    if price is not None:
        return price

    price = await _fetch_from_mobile_api(ticker)
    if price is not None:
        return price

    return await _fetch_from_polling_api(ticker)


async def _fetch_from_main_page(ticker: str) -> float | None:
    """finance.naver.com 메인 페이지 HTML에서 현재주가를 파싱한다."""
    url = _MAIN_URL.format(ticker=ticker)
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        html = resp.content.decode("euc-kr", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.select_one("p.no_today em span.blind")
        if tag:
            return float(tag.text.strip().replace(",", ""))
    except Exception as e:
        logger.warning("메인페이지 주가 조회 실패 (ticker=%s): %s", ticker, e)
    return None


async def _fetch_from_mobile_api(ticker: str) -> float | None:
    """네이버 모바일 JSON API에서 현재주가를 조회한다."""
    url = _MOBILE_URL.format(ticker=ticker)
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=8) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        price_str = data.get("closePrice") or data.get("stockPrice")
        if price_str is not None:
            return float(str(price_str).replace(",", ""))
    except Exception as e:
        logger.warning("모바일 API 주가 조회 실패 (ticker=%s): %s", ticker, e)
    return None


async def _fetch_from_polling_api(ticker: str) -> float | None:
    """네이버 금융 realtime 폴링 API에서 현재주가를 조회한다."""
    params = {"query": f"SERVICE_ITEM:{ticker}"}
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=8) as client:
            resp = await client.get(_POLLING_URL, params=params)
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
