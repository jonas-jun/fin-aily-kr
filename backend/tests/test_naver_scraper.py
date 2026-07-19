from pathlib import Path

import httpx
import respx

from app.services.naver_scraper import _parse_date, fetch_report_list


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_date_normalizes_two_digit_year():
    assert _parse_date("26.07.18") == "2026-07-18"
    assert _parse_date("2026.07.18") == "2026-07-18"
    assert _parse_date("unknown") == "unknown"


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
