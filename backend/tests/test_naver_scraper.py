from pathlib import Path

import httpx
import respx
from bs4 import BeautifulSoup

from app.services.naver_scraper import _parse_date, _parse_row, fetch_report_list


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_date_normalizes_two_digit_year():
    assert _parse_date("26.07.18") == "2026-07-18"
    assert _parse_date("2026.07.18") == "2026-07-18"
    assert _parse_date("unknown") == "unknown"


def test_parse_row_extracts_report_metadata():
    html = (FIXTURES / "naver_reports.html").read_text()
    row = BeautifulSoup(html, "lxml").select_one("table.type_1 tr")

    parsed = _parse_row(row)

    assert parsed is not None
    report, report_date = parsed
    assert report.model_dump() == {
        "nid": "12345",
        "title": "실적 개선 전망",
        "firm": "테스트증권",
        "date": "2026-07-18",
        "detail_url": "https://finance.naver.com/research/company_read.naver?nid=12345&page=1",
        "pdf_url": "",
    }
    assert report_date is not None
    assert report_date.isoformat() == "2026-07-18"


@respx.mock
async def test_fetch_report_list_parses_naver_html_fixture():
    html = (FIXTURES / "naver_reports.html").read_text()
    respx.get("https://finance.naver.com/research/company_list.naver").mock(
        return_value=httpx.Response(200, content=html.encode("euc-kr"))
    )

    reports = await fetch_report_list("000001", n=1, days_limit=90)

    assert len(reports) == 1
    assert reports[0].nid == "12345"
    assert reports[0].title == "실적 개선 전망"
    assert reports[0].firm == "테스트증권"
    assert reports[0].date == "2026-07-18"
    assert reports[0].detail_url.endswith("company_read.naver?nid=12345&page=1")
