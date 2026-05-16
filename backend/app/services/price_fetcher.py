import asyncio
import json
import logging

import httpx
import yfinance as yf

logger = logging.getLogger(__name__)

_MOBILE_URL = "https://m.stock.naver.com/api/stock/{ticker}/basic"
_POLLING_URL = "https://polling.finance.naver.com/api/realtime"
_HEADERS = {
    "Referer": "https://finance.naver.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


async def fetch_current_price(ticker: str) -> float | None:
    """현재주가 조회. yfinance → 네이버 모바일 API → 폴링 API 순으로 시도한다."""
    print(f"[price] 주가 조회 시작 ticker={ticker}", flush=True)

    price = await _fetch_from_yahoo(ticker)
    if price is not None:
        print(f"[price] yfinance 성공 ticker={ticker} price={price}", flush=True)
        return price

    print(f"[price] yfinance 실패, 네이버 모바일 API 시도 ticker={ticker}", flush=True)
    price = await _fetch_from_mobile_api(ticker)
    if price is not None:
        print(f"[price] 네이버 모바일 API 성공 ticker={ticker} price={price}", flush=True)
        return price

    print(f"[price] 네이버 모바일 API 실패, 폴링 API 시도 ticker={ticker}", flush=True)
    price = await _fetch_from_polling_api(ticker)
    if price is not None:
        print(f"[price] 폴링 API 성공 ticker={ticker} price={price}", flush=True)
    else:
        print(f"[price] 모든 API 실패 ticker={ticker}", flush=True)
    return price


def _yf_sync_price(ticker: str) -> float | None:
    """yfinance로 주가 조회 (동기). KOSPI(.KS) → KOSDAQ(.KQ) 순으로 시도."""
    for suffix in (".KS", ".KQ"):
        try:
            t = yf.Ticker(ticker + suffix)
            price = t.fast_info.last_price
            if price and float(price) > 0:
                return float(price)
        except Exception as e:
            print(f"[price] yfinance {ticker}{suffix} 실패: {e}", flush=True)
    return None


async def _fetch_from_yahoo(ticker: str) -> float | None:
    try:
        return await asyncio.to_thread(_yf_sync_price, ticker)
    except Exception as e:
        print(f"[price] yfinance 예외 ticker={ticker}: {e}", flush=True)
        return None


async def _fetch_from_mobile_api(ticker: str) -> float | None:
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
        print(f"[price] 네이버 모바일 API 예외 ticker={ticker}: {e}", flush=True)
    return None


async def _fetch_from_polling_api(ticker: str) -> float | None:
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
        print(f"[price] 폴링 API 예외 ticker={ticker}: {e}", flush=True)
    return None
