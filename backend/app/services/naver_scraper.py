import logging
import re
from datetime import date, timedelta

import httpx
from bs4 import BeautifulSoup

from app.models.schemas import ReportMeta
from app.services.http_client import NAVER_HTML_HEADERS, client_scope

logger = logging.getLogger(__name__)

_BASE = "https://finance.naver.com/research"
_REQUEST_TIMEOUT = 15
_MAX_REPORT_PAGES = 3


async def fetch_report_list(
    ticker: str,
    n: int = 5,
    days_limit: int = 90,
    client: httpx.AsyncClient | None = None,
) -> list[ReportMeta]:
    """
    네이버 증권 리서치에서 특정 종목의 최신 리포트 목록을 수집한다.
    최대 3페이지까지 순회하여 n개를 채우며, days_limit일 이내의 리포트만 수집한다.
    """
    reports: list[ReportMeta] = []
    page = 1
    cutoff = date.today() - timedelta(days=days_limit)

    async with client_scope(client) as http:
        while len(reports) < n and page <= _MAX_REPORT_PAGES:
            url = f"{_BASE}/company_list.naver?searchType=itemCode&itemCode={ticker}&page={page}"
            try:
                resp = await http.get(url, headers=NAVER_HTML_HEADERS, timeout=_REQUEST_TIMEOUT)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("리포트 목록 요청 실패 (ticker=%s, page=%d): %s", ticker, page, e)
                break

            html = resp.content.decode("euc-kr", errors="replace")
            soup = BeautifulSoup(html, "lxml")
            rows = soup.select("table.type_1 tr")

            found_in_page = 0
            date_exceeded = False
            for row in rows:
                parsed = _parse_row(row)
                if parsed is None:
                    continue
                report, report_date = parsed

                # 네이버 리서치는 날짜 역순이므로 cutoff를 벗어나면 이후 리포트도 모두 오래됨
                if report_date is not None and report_date < cutoff:
                    date_exceeded = True
                    break

                reports.append(report)
                found_in_page += 1

                if len(reports) >= n:
                    break

            if found_in_page == 0 or date_exceeded:
                break
            page += 1

    return reports[:n]


async def fetch_pdf_url(detail_url: str, client: httpx.AsyncClient | None = None) -> str:
    """리포트 상세 페이지에서 PDF 직접 링크를 추출한다."""
    async with client_scope(client) as http:
        try:
            resp = await http.get(
                detail_url,
                headers=NAVER_HTML_HEADERS,
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("상세 페이지 요청 실패 (%s): %s", detail_url, e)
            return ""

    html = resp.content.decode("euc-kr", errors="replace")
    soup = BeautifulSoup(html, "lxml")

    # PDF 링크 패턴: stock.pstatic.net/stock-research/...pdf
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if "pstatic.net" in href and href.lower().endswith(".pdf"):
            return href

    # 정규식 폴백
    match = re.search(r'(https://stock\.pstatic\.net[^"\']+\.pdf)', html)
    return match.group(1) if match else ""


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
            pdf_url = await fetch_pdf_url(report.detail_url, client=http)
            report.pdf_url = pdf_url

    return reports


def _parse_date(raw: str) -> str:
    """'26.05.14' → '2026-05-14'"""
    parts = raw.strip().split(".")
    if len(parts) == 3:
        yy, mm, dd = parts
        year = f"20{yy}" if len(yy) == 2 else yy
        return f"{year}-{mm}-{dd}"
    return raw


def _parse_row(row) -> tuple[ReportMeta, date | None] | None:
    """네이버 리서치 테이블 행을 리포트 메타데이터로 변환한다."""
    columns = row.select("td")
    if len(columns) < 5:
        return None

    link = columns[1].find("a")
    if not link:
        return None

    href = link.get("href", "")
    nid_match = re.search(r"nid=(\d+)", href)
    if not nid_match:
        return None

    report_date_text = _parse_date(columns[4].get_text(strip=True))
    try:
        report_date = date.fromisoformat(report_date_text)
    except ValueError:
        report_date = None

    detail_url = f"{_BASE}/{href}" if href.startswith("company_read") else href
    return (
        ReportMeta(
            nid=nid_match.group(1),
            title=link.get_text(strip=True),
            firm=columns[2].get_text(strip=True),
            date=report_date_text,
            detail_url=detail_url,
        ),
        report_date,
    )
