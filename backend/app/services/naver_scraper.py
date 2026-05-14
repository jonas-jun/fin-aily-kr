import logging
import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_BASE = "https://finance.naver.com/research"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://finance.naver.com/",
}


@dataclass
class ReportMeta:
    nid: str
    title: str
    firm: str
    date: str          # "YYYY-MM-DD"
    detail_url: str
    pdf_url: str = ""  # fetch_pdf_url() 호출 후 채워짐


async def fetch_report_list(ticker: str, n: int = 5) -> list[ReportMeta]:
    """
    네이버 증권 리서치에서 특정 종목의 최신 리포트 목록을 수집한다.
    최대 3페이지까지 순회하여 n개를 채운다.
    """
    reports: list[ReportMeta] = []
    page = 1

    async with httpx.AsyncClient(headers=_HEADERS, timeout=15) as client:
        while len(reports) < n and page <= 3:
            url = f"{_BASE}/company_list.naver?searchType=itemCode&itemCode={ticker}&page={page}"
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("리포트 목록 요청 실패 (ticker=%s, page=%d): %s", ticker, page, e)
                break

            html = resp.content.decode("euc-kr", errors="replace")
            soup = BeautifulSoup(html, "lxml")
            rows = soup.select("table.type_1 tr")

            found_in_page = 0
            for row in rows:
                cols = row.select("td")
                # 구조: [종목명, 제목, 증권사, (빈칸), 날짜, 조회수]
                if len(cols) < 5:
                    continue

                link_tag = cols[1].find("a")
                if not link_tag:
                    continue

                title = link_tag.get_text(strip=True)
                firm = cols[2].get_text(strip=True)
                date_raw = cols[4].get_text(strip=True)  # "26.05.14"
                href = link_tag.get("href", "")

                nid_match = re.search(r"nid=(\d+)", href)
                if not nid_match:
                    continue

                nid = nid_match.group(1)
                date = _parse_date(date_raw)
                detail_url = f"{_BASE}/{href}" if href.startswith("company_read") else href

                reports.append(ReportMeta(
                    nid=nid,
                    title=title,
                    firm=firm,
                    date=date,
                    detail_url=detail_url,
                ))
                found_in_page += 1

                if len(reports) >= n:
                    break

            if found_in_page == 0:
                break
            page += 1

    return reports[:n]


async def fetch_pdf_url(detail_url: str) -> str:
    """리포트 상세 페이지에서 PDF 직접 링크를 추출한다."""
    async with httpx.AsyncClient(headers=_HEADERS, timeout=15) as client:
        try:
            resp = await client.get(detail_url)
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


async def fetch_reports_with_pdf(ticker: str, n: int = 5) -> list[ReportMeta]:
    """리포트 목록 수집 후 각 리포트의 PDF URL까지 채워서 반환한다."""
    reports = await fetch_report_list(ticker, n)

    async with httpx.AsyncClient(headers=_HEADERS, timeout=15) as client:
        for report in reports:
            pdf_url = await fetch_pdf_url(report.detail_url)
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
