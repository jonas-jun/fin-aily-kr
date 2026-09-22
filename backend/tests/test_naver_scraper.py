import json
from datetime import date, timedelta
from pathlib import Path

import httpx
import pytest
import respx

from app.services.naver_scraper import (
    ReportFetchError,
    _parse_item,
    fetch_pdf_url,
    fetch_report_list,
    fetch_reports_with_pdf,
)


FIXTURES = Path(__file__).parent / "fixtures"
LIST_URL = "https://m.stock.naver.com/api/research/stock/005930"
DETAIL_URL = "https://m.stock.naver.com/api/research/company/96282"


def _list_item(research_id: int, days_ago: int, **overrides) -> dict:
    item = {
        "researchId": research_id,
        "title": f"리포트 {research_id}",
        "brokerName": "테스트증권",
        "writeDate": (date.today() - timedelta(days=days_ago)).isoformat(),
    }
    item.update(overrides)
    return item


def test_parse_item_maps_api_response_to_report_metadata():
    item = json.loads((FIXTURES / "naver_reports.json").read_text())[0]

    parsed = _parse_item(item)

    assert parsed is not None
    report, report_date = parsed
    assert report.model_dump() == {
        "nid": "96282",
        "title": "Beyond the cycle",
        "firm": "대신증권",
        "date": "2026-09-22",
        "detail_url": "https://stock.naver.com/research/company/96282",
        "pdf_url": "",
    }
    assert report_date == date(2026, 9, 22)


def test_parse_item_skips_entry_without_research_id_or_title():
    assert _parse_item({"title": "제목만 있음"}) is None
    assert _parse_item({"researchId": 1, "title": ""}) is None


def test_parse_item_tolerates_unparseable_write_date():
    parsed = _parse_item({"researchId": 1, "title": "리포트", "writeDate": "unknown"})

    assert parsed is not None
    report, report_date = parsed
    assert report.date == "unknown"
    assert report_date is None


@respx.mock
async def test_fetch_report_list_collects_recent_reports():
    respx.get(LIST_URL).mock(
        return_value=httpx.Response(200, json=[_list_item(2, 1), _list_item(1, 10)])
    )

    reports = await fetch_report_list("005930", n=5, days_limit=90)

    assert [report.nid for report in reports] == ["2", "1"]
    assert reports[0].firm == "테스트증권"


@respx.mock
async def test_fetch_report_list_stops_at_days_limit():
    respx.get(LIST_URL).mock(
        return_value=httpx.Response(200, json=[_list_item(2, 5), _list_item(1, 200)])
    )

    reports = await fetch_report_list("005930", n=5, days_limit=90)

    assert [report.nid for report in reports] == ["2"]


@respx.mock
async def test_fetch_report_list_returns_empty_when_all_reports_are_stale():
    """빈 리스트는 '실제로 최근 리포트가 없음'만을 의미한다 (DART 폴백의 정당한 조건)."""
    respx.get(LIST_URL).mock(return_value=httpx.Response(200, json=[_list_item(1, 400)]))

    assert await fetch_report_list("005930", n=5, days_limit=90) == []


@respx.mock
async def test_fetch_report_list_raises_when_api_redirects_to_html_page():
    """
    레거시 스크래핑이 조용히 0건을 반환하던 회귀 케이스.
    302로 HTML 페이지에 도달하면 '리포트 없음'이 아니라 수집 실패로 올려야 한다.
    """
    respx.get(LIST_URL).mock(
        return_value=httpx.Response(
            302, headers={"location": "https://stock.naver.com/research/company"}
        )
    )
    respx.get("https://stock.naver.com/research/company").mock(
        return_value=httpx.Response(200, html="<html><body>SPA</body></html>")
    )

    with pytest.raises(ReportFetchError):
        await fetch_report_list("005930", n=5, days_limit=90)


@respx.mock
async def test_fetch_report_list_raises_on_server_error():
    respx.get(LIST_URL).mock(return_value=httpx.Response(500))

    with pytest.raises(ReportFetchError):
        await fetch_report_list("005930", n=5, days_limit=90)


@respx.mock
async def test_fetch_report_list_raises_on_unexpected_payload_shape():
    respx.get(LIST_URL).mock(return_value=httpx.Response(200, json={"error": "nope"}))

    with pytest.raises(ReportFetchError):
        await fetch_report_list("005930", n=5, days_limit=90)


@respx.mock
async def test_fetch_reports_with_pdf_fills_attach_url():
    detail = json.loads((FIXTURES / "naver_report_detail.json").read_text())
    respx.get(LIST_URL).mock(return_value=httpx.Response(200, json=[_list_item(96282, 1)]))
    respx.get(DETAIL_URL).mock(return_value=httpx.Response(200, json=detail))

    reports = await fetch_reports_with_pdf("005930", n=1, days_limit=90)

    assert len(reports) == 1
    assert reports[0].pdf_url == detail["researchContent"]["attachUrl"]


@respx.mock
async def test_fetch_pdf_url_returns_empty_when_detail_lookup_fails():
    """PDF가 없어도 메타데이터만으로 분석이 가능하므로 여기서는 예외를 올리지 않는다."""
    respx.get(DETAIL_URL).mock(return_value=httpx.Response(500))

    assert await fetch_pdf_url("96282") == ""


@respx.mock
async def test_fetch_pdf_url_returns_empty_when_attachment_missing():
    respx.get(DETAIL_URL).mock(
        return_value=httpx.Response(200, json={"researchContent": {"researchId": "96282"}})
    )

    assert await fetch_pdf_url("96282") == ""
