"""수집 계층과 파이프라인의 이음매 테스트.

이번 버그는 스크래퍼가 실패를 빈 리스트로 돌려주고 파이프라인이 그걸 '리포트 없음'으로
읽으면서 생겼다. 두 계층을 각각 mock으로 고정하면 그 이음매는 영원히 덮이지 않으므로,
여기서는 HTTP 계층만 mock하고 진짜 스크래퍼 → 진짜 파이프라인을 통과시킨다.
"""
import httpx
import pytest
import respx

from app.models.schemas import AnalyzeRequest
from app.services.http_client import FOLLOW_REDIRECTS
from app.services.research_pipeline import PipelineError, run_research_pipeline


LIST_URL = "https://m.stock.naver.com/api/research/stock/005930"
SPA_URL = "https://stock.naver.com/research/company"


async def _run(body: AnalyzeRequest):
    async with httpx.AsyncClient(follow_redirects=FOLLOW_REDIRECTS) as http:
        return await run_research_pipeline(body, http_client=http, gemini_client=None)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(200, content=b""),
        httpx.Response(200, json=[{"id": 1, "researchTitle": "필드명 변경", "writeDate": "2026-09-22"}]),
    ],
    ids=["server_error", "empty_body", "schema_drift"],
)
@respx.mock
async def test_collection_failure_surfaces_as_502_not_dart_fallback(response):
    respx.get(LIST_URL).mock(return_value=response)

    with pytest.raises(PipelineError) as exc_info:
        await _run(AnalyzeRequest(ticker="005930", name="삼성전자"))

    assert exc_info.value.status_code == 502
    assert exc_info.value.code == "SCRAPE_FAILED"


@respx.mock
async def test_legacy_redirect_to_spa_surfaces_as_502():
    """장애 당시의 실제 응답 형태 — 302 → SPA HTML."""
    respx.get(LIST_URL).mock(return_value=httpx.Response(302, headers={"location": SPA_URL}))
    respx.get(SPA_URL).mock(return_value=httpx.Response(200, html="<html><body>SPA</body></html>"))

    with pytest.raises(PipelineError) as exc_info:
        await _run(AnalyzeRequest(ticker="005930", name="삼성전자"))

    assert exc_info.value.status_code == 502
