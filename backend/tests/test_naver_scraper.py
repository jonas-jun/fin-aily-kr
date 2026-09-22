import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

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
SPA_URL = "https://stock.naver.com/research/company"


def _kst_today():
    """수집 코드가 KST 기준으로 cutoff를 잡으므로 테스트도 같은 기준을 쓴다."""
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


def _list_item(research_id: int, days_ago: int, **overrides) -> dict:
    item = {
        "researchId": research_id,
        "title": f"리포트 {research_id}",
        "brokerName": "테스트증권",
        "writeDate": (_kst_today() - timedelta(days=days_ago)).isoformat(),
    }
    item.update(overrides)
    return item


# ── _parse_item ──────────────────────────────────────────────────────────────

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
    assert report_date.isoformat() == "2026-09-22"


def test_parse_item_skips_entry_without_research_id_or_title():
    assert _parse_item({"title": "제목만 있음"}) is None
    assert _parse_item({"researchId": 1, "title": ""}) is None


def test_parse_item_skips_non_dict_entry():
    assert _parse_item("oops") is None
    assert _parse_item(["oops"]) is None


def test_parse_item_skips_unparseable_write_date():
    """나이를 모르는 항목은 days_limit 판정이 불가능하므로 '최근 리포트'로 통과시키지 않는다."""
    assert _parse_item({"researchId": 1, "title": "리포트", "writeDate": "2019/01/01"}) is None
    assert _parse_item({"researchId": 1, "title": "리포트"}) is None


def test_parse_item_normalizes_compact_iso_date():
    """date.fromisoformat은 축약 형식도 받으므로 응답·UI에는 정규화된 값이 담겨야 한다."""
    parsed = _parse_item({"researchId": 1, "title": "리포트", "writeDate": "20260922"})

    assert parsed is not None
    report, _ = parsed
    assert report.date == "2026-09-22"


# ── fetch_report_list: 정상 수집 ──────────────────────────────────────────────

@respx.mock
async def test_fetch_report_list_collects_recent_reports():
    route = respx.get(LIST_URL).mock(
        return_value=httpx.Response(200, json=[_list_item(2, 1), _list_item(1, 10)])
    )

    reports = await fetch_report_list("005930", n=5, days_limit=90)

    assert [report.nid for report in reports] == ["2", "1"]
    assert reports[0].firm == "테스트증권"
    assert dict(route.calls.last.request.url.params) == {"pageSize": "5", "page": "1"}


@respx.mock
async def test_fetch_report_list_drops_stale_reports():
    respx.get(LIST_URL).mock(
        return_value=httpx.Response(200, json=[_list_item(2, 5), _list_item(1, 200)])
    )

    reports = await fetch_report_list("005930", n=5, days_limit=90)

    assert [report.nid for report in reports] == ["2"]


@respx.mock
async def test_fetch_report_list_keeps_fresh_reports_behind_a_stale_one():
    """발행일 역순 전제가 깨져도 신선한 리포트를 버리지 않는다 (0건 → DART 폴백 방지)."""
    respx.get(LIST_URL).mock(
        return_value=httpx.Response(
            200, json=[_list_item(1, 200), _list_item(2, 1), _list_item(3, 2)]
        )
    )

    reports = await fetch_report_list("005930", n=5, days_limit=90)

    assert [report.nid for report in reports] == ["2", "3"]


@pytest.mark.parametrize(("days_ago", "expected"), [(90, ["1"]), (91, [])])
@respx.mock
async def test_fetch_report_list_days_limit_boundary_is_inclusive(days_ago, expected):
    respx.get(LIST_URL).mock(return_value=httpx.Response(200, json=[_list_item(1, days_ago)]))

    reports = await fetch_report_list("005930", n=5, days_limit=90)

    assert [report.nid for report in reports] == expected


@respx.mock
async def test_fetch_report_list_truncates_to_n():
    """pageSize는 서버에 대한 요청일 뿐이므로 실제 보장은 클라이언트 쪽 상한이다."""
    respx.get(LIST_URL).mock(
        return_value=httpx.Response(200, json=[_list_item(i, i) for i in range(1, 8)])
    )

    reports = await fetch_report_list("005930", n=3, days_limit=90)

    assert [report.nid for report in reports] == ["1", "2", "3"]


@respx.mock
async def test_fetch_report_list_returns_empty_when_all_reports_are_stale():
    """빈 리스트는 '실제로 최근 리포트가 없음'만을 의미한다 (DART 폴백의 정당한 조건)."""
    respx.get(LIST_URL).mock(return_value=httpx.Response(200, json=[_list_item(1, 400)]))

    assert await fetch_report_list("005930", n=5, days_limit=90) == []


# ── fetch_report_list: 수집 실패 ──────────────────────────────────────────────

@respx.mock
async def test_fetch_report_list_raises_when_every_item_is_unparseable():
    """
    필드명이 바뀌면 전 항목이 파싱 실패한다. 이때의 0건은 '리포트 없음'이 아니라
    스키마 변경이므로, 빈 리스트로 돌려주면 이번 버그가 그대로 재현된다.
    """
    respx.get(LIST_URL).mock(
        return_value=httpx.Response(
            200, json=[{"id": 96282, "researchTitle": "Beyond the cycle", "writeDate": "2026-09-22"}]
        )
    )

    with pytest.raises(ReportFetchError):
        await fetch_report_list("005930", n=5, days_limit=90)


@respx.mock
async def test_fetch_report_list_raises_when_items_are_not_objects():
    respx.get(LIST_URL).mock(return_value=httpx.Response(200, json=["oops"]))

    with pytest.raises(ReportFetchError):
        await fetch_report_list("005930", n=5, days_limit=90)


@respx.mock
async def test_fetch_report_list_follows_redirect_then_raises():
    """
    레거시 스크래핑이 조용히 0건을 반환하던 회귀 케이스.
    리다이렉트를 실제로 따라갔는지(FOLLOW_REDIRECTS)와, 도달한 HTML이 '리포트 없음'이
    아니라 수집 실패가 되는지를 함께 고정한다.
    """
    respx.get(LIST_URL).mock(
        return_value=httpx.Response(302, headers={"location": SPA_URL})
    )
    spa = respx.get(SPA_URL).mock(
        return_value=httpx.Response(200, html="<html><body>SPA</body></html>")
    )

    with pytest.raises(ReportFetchError):
        await fetch_report_list("005930", n=5, days_limit=90)

    assert spa.called, "리다이렉트를 따라가지 않았다 — FOLLOW_REDIRECTS 회귀"


@respx.mock
async def test_fetch_report_list_raises_on_empty_body():
    """실제 장애 상황의 재현 — 이관된 경로는 본문 0 byte를 돌려줬다."""
    respx.get(LIST_URL).mock(return_value=httpx.Response(200, content=b""))

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


# ── PDF 첨부 ─────────────────────────────────────────────────────────────────

@respx.mock
async def test_fetch_reports_with_pdf_fills_attach_url():
    detail = json.loads((FIXTURES / "naver_report_detail.json").read_text())
    respx.get(LIST_URL).mock(return_value=httpx.Response(200, json=[_list_item(96282, 1)]))
    respx.get(DETAIL_URL).mock(return_value=httpx.Response(200, json=detail))

    reports = await fetch_reports_with_pdf("005930", n=1, days_limit=90)

    assert len(reports) == 1
    assert reports[0].pdf_url == detail["researchContent"]["attachUrl"]


@respx.mock
async def test_fetch_reports_with_pdf_logs_error_when_no_report_has_pdf(caplog):
    """전건 PDF 누락은 개별 리포트의 사정이 아니라 상세 API 스키마 변경 신호다."""
    respx.get(LIST_URL).mock(return_value=httpx.Response(200, json=[_list_item(96282, 1)]))
    respx.get(DETAIL_URL).mock(
        return_value=httpx.Response(200, json={"researchContent": {"fileUrl": "x.pdf"}})
    )

    with caplog.at_level(logging.ERROR):
        reports = await fetch_reports_with_pdf("005930", n=1, days_limit=90)

    assert [report.pdf_url for report in reports] == [""]
    assert "전부 PDF URL 없음" in caplog.text


@respx.mock
async def test_fetch_pdf_url_returns_empty_when_detail_lookup_fails():
    """PDF는 없어도 제목·증권사·날짜만으로 프롬프트가 구성되므로 예외를 올리지 않는다."""
    respx.get(DETAIL_URL).mock(return_value=httpx.Response(500))

    assert await fetch_pdf_url("96282") == ""


@respx.mock
async def test_fetch_pdf_url_returns_empty_when_attachment_missing():
    respx.get(DETAIL_URL).mock(
        return_value=httpx.Response(200, json={"researchContent": {"researchId": "96282"}})
    )

    assert await fetch_pdf_url("96282") == ""


@pytest.mark.parametrize("payload", [None, [], "oops", {"researchContent": []}])
@respx.mock
async def test_fetch_pdf_url_returns_empty_on_unexpected_payload_shape(payload):
    """선택적 조회가 예외를 뿜어 분석 전체를 502로 끌어내리지 않아야 한다."""
    respx.get(DETAIL_URL).mock(return_value=httpx.Response(200, json=payload))

    assert await fetch_pdf_url("96282") == ""
