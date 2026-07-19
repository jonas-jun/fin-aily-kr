import httpx
import pytest

from app.main import app
from app.routers import research_router
from app.services.naver_scraper import ReportMeta
from app.services.report_analyzer import AnalysisResult


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def app_clients():
    app.state.http = object()
    app.state.gemini = None


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def _analysis_result(*, dart_only: bool = False) -> AnalysisResult:
    return AnalysisResult(
        ticker="005930",
        name="삼성전자",
        report_count=0 if dart_only else 1,
        analyzed_at="2026-07-19",
        target_price={"avg": None, "min": None, "max": None},
        sources=[] if dart_only else [{
            "firm": "테스트증권",
            "title": "테스트",
            "date": "2026-07-18",
            "pdf_url": "https://example.com/report.pdf",
            "target_price": None,
        }],
        model_version="test-model",
        full_report="## 1. 투자 요약",
        dart_only=dart_only,
    )


async def test_analyze_normal_flow_preserves_response(monkeypatch):
    reports = [ReportMeta("1", "테스트", "테스트증권", "2026-07-18", "detail", "pdf")]
    monkeypatch.setattr(research_router, "fetch_reports_with_pdf", _async_return(reports))
    monkeypatch.setattr(research_router, "extract_text_from_pdf_url", _async_return("본문"))
    monkeypatch.setattr(research_router, "fetch_current_price", _async_return(70_000.0))
    monkeypatch.setattr(research_router, "fetch_dart_data", _async_return([]))
    monkeypatch.setattr(research_router, "fetch_dart_filing_texts", _async_return([]))
    monkeypatch.setattr(research_router, "analyze_reports", _async_return(_analysis_result()))

    response = await _request("POST", "/api/analyze", json={"ticker": "005930", "name": "삼성전자"})

    assert response.status_code == 200
    assert response.json() == {
        "ticker": "005930",
        "name": "삼성전자",
        "report_count": 1,
        "analyzed_at": "2026-07-19",
        "target_price": {"avg": None, "min": None, "max": None, "current_price": 70_000.0},
        "sources": [{
            "firm": "테스트증권",
            "title": "테스트",
            "date": "2026-07-18",
            "pdf_url": "https://example.com/report.pdf",
            "target_price": None,
        }],
        "model_version": "test-model",
        "full_report": "## 1. 투자 요약",
        "dart_only": False,
    }


async def test_analyze_uses_dart_fallback(monkeypatch):
    monkeypatch.setattr(research_router, "fetch_reports_with_pdf", _async_return([]))
    monkeypatch.setattr(research_router, "fetch_current_price", _async_return(10_000.0))
    monkeypatch.setattr(research_router, "fetch_dart_data", _async_return([{"period": "2025 1Q"}]))
    monkeypatch.setattr(research_router, "fetch_dart_filing_texts", _async_return([]))
    monkeypatch.setattr(research_router, "analyze_reports", _async_return(_analysis_result(dart_only=True)))

    response = await _request("POST", "/api/analyze", json={"ticker": "005930", "name": "삼성전자"})

    assert response.status_code == 200
    assert response.json()["dart_only"] is True
    assert response.json()["report_count"] == 0


@pytest.mark.parametrize(("payload", "status_code", "code"), [
    ({}, 422, "MISSING_FIELDS"),
    ({"ticker": "005930"}, 422, "MISSING_FIELDS"),
])
async def test_analyze_rejects_missing_identity(payload, status_code, code):
    response = await _request("POST", "/api/analyze", json=payload)

    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == code


async def test_analyze_returns_not_found_for_unknown_query(monkeypatch):
    monkeypatch.setattr(research_router, "search_tickers", _async_return([]))

    response = await _request("POST", "/api/analyze", json={"query": "없는회사"})

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "NOT_FOUND",
        "message": "'없는회사'에 해당하는 종목을 찾을 수 없습니다.",
    }


async def test_analyze_returns_no_data_when_all_sources_empty(monkeypatch):
    monkeypatch.setattr(research_router, "fetch_reports_with_pdf", _async_return([]))
    monkeypatch.setattr(research_router, "fetch_current_price", _async_return(None))
    monkeypatch.setattr(research_router, "fetch_dart_data", _async_return([]))
    monkeypatch.setattr(research_router, "fetch_dart_filing_texts", _async_return([]))

    response = await _request(
        "POST", "/api/analyze", json={"ticker": "000001", "name": "테스트", "days_limit": 30}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "NO_DATA",
        "message": "최근 30일 내 발행된 리포트가 없고 DART 공시 데이터도 조회되지 않았습니다.",
    }


async def test_analyze_maps_scrape_and_analysis_failures(monkeypatch):
    async def fail(*args, **kwargs):
        raise RuntimeError("failure")

    monkeypatch.setattr(research_router, "fetch_reports_with_pdf", fail)
    response = await _request("POST", "/api/analyze", json={"ticker": "005930", "name": "삼성전자"})
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "SCRAPE_FAILED"

    reports = [ReportMeta("1", "테스트", "증권", "2026-07-18", "detail", "pdf")]
    monkeypatch.setattr(research_router, "fetch_reports_with_pdf", _async_return(reports))
    monkeypatch.setattr(research_router, "extract_text_from_pdf_url", _async_return("본문"))
    monkeypatch.setattr(research_router, "fetch_current_price", _async_return(None))
    monkeypatch.setattr(research_router, "fetch_dart_data", _async_return([]))
    monkeypatch.setattr(research_router, "fetch_dart_filing_texts", _async_return([]))
    monkeypatch.setattr(research_router, "analyze_reports", fail)
    response = await _request("POST", "/api/analyze", json={"ticker": "005930", "name": "삼성전자"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ANALYSIS_FAILED"


def _async_return(value):
    async def inner(*args, **kwargs):
        return value

    return inner
