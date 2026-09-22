import logging
from datetime import date, timedelta

import httpx

from app.models.schemas import ReportMeta
from app.services.http_client import NAVER_HEADERS, client_scope

logger = logging.getLogger(__name__)

# 레거시 finance.naver.com/research/*.naver 페이지는 stock.naver.com SPA로 이관되어
# 302만 돌려주므로, 종목별 리포트는 모바일 JSON API로 조회한다.
_LIST_URL = "https://m.stock.naver.com/api/research/stock/{ticker}"
_DETAIL_URL = "https://m.stock.naver.com/api/research/company/{nid}"
_WEB_DETAIL_URL = "https://stock.naver.com/research/company/{nid}"
_REQUEST_TIMEOUT = 15


class ReportFetchError(Exception):
    """리포트 수집 자체가 실패한 경우. '최근 리포트가 없음'과 반드시 구분한다."""


async def fetch_report_list(
    ticker: str,
    n: int = 5,
    days_limit: int = 90,
    client: httpx.AsyncClient | None = None,
) -> list[ReportMeta]:
    """
    네이버 증권 리서치 API에서 특정 종목의 최신 리포트 목록을 수집한다.
    응답은 발행일 역순이므로 days_limit를 벗어나는 항목을 만나면 순회를 멈춘다.

    수집에 실패하면 ReportFetchError를 던진다. 빈 리스트는 "days_limit 이내에
    발행된 리포트가 실제로 없다"는 의미로만 쓰인다 — 수집 실패를 빈 리스트로
    뭉개면 호출부가 DART 폴백으로 조용히 넘어가버린다.
    """
    url = _LIST_URL.format(ticker=ticker)
    params = {"pageSize": n, "page": 1}

    async with client_scope(client) as http:
        try:
            resp = await http.get(
                url, params=params, headers=NAVER_HEADERS, timeout=_REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            raise ReportFetchError(f"리포트 목록 조회 실패 (ticker={ticker}): {e}") from e

    if not isinstance(payload, list):
        raise ReportFetchError(
            f"리포트 목록 응답 형식이 예상과 다름 (ticker={ticker}): {type(payload).__name__}"
        )

    cutoff = date.today() - timedelta(days=days_limit)
    reports: list[ReportMeta] = []
    for item in payload:
        parsed = _parse_item(item)
        if parsed is None:
            continue
        report, report_date = parsed

        if report_date is not None and report_date < cutoff:
            break

        reports.append(report)
        if len(reports) >= n:
            break

    return reports


async def fetch_pdf_url(nid: str, client: httpx.AsyncClient | None = None) -> str:
    """
    리포트 상세 API에서 PDF 첨부 URL을 추출한다.
    PDF는 없어도 메타데이터만으로 분석이 가능하므로 실패 시 빈 문자열을 반환한다.
    """
    url = _DETAIL_URL.format(nid=nid)

    async with client_scope(client) as http:
        try:
            resp = await http.get(url, headers=NAVER_HEADERS, timeout=_REQUEST_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("리포트 상세 조회 실패 (nid=%s): %s", nid, e)
            return ""

    content = payload.get("researchContent") or {}
    return content.get("attachUrl") or ""


async def fetch_reports_with_pdf(
    ticker: str,
    n: int = 5,
    days_limit: int = 90,
    client: httpx.AsyncClient | None = None,
) -> list[ReportMeta]:
    """리포트 목록 수집 후 각 리포트의 PDF URL까지 채워서 반환한다."""
    async with client_scope(client) as http:
        reports = await fetch_report_list(ticker, n, days_limit, client=http)
        for report in reports:
            report.pdf_url = await fetch_pdf_url(report.nid, client=http)

    return reports


def _parse_item(item: dict) -> tuple[ReportMeta, date | None] | None:
    """리서치 API 응답 항목을 리포트 메타데이터로 변환한다."""
    research_id = item.get("researchId")
    title = item.get("title")
    if research_id is None or not title:
        return None

    nid = str(research_id)
    write_date = str(item.get("writeDate") or "")
    try:
        report_date = date.fromisoformat(write_date)
    except ValueError:
        report_date = None

    return (
        ReportMeta(
            nid=nid,
            title=title,
            firm=item.get("brokerName") or "",
            date=write_date,
            detail_url=_WEB_DETAIL_URL.format(nid=nid),
        ),
        report_date,
    )
