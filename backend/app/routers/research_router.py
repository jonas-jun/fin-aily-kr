import logging

from fastapi import APIRouter, HTTPException, Query, Request, status
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ReportItem,
    TickerItem,
)
from app.services.naver_scraper import fetch_reports_with_pdf
from app.services.research_pipeline import PipelineError, run_research_pipeline
from app.services.ticker_resolver import search_tickers

logger = logging.getLogger(__name__)
router = APIRouter(tags=["research"])


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.get("/search", response_model=list[TickerItem], summary="종목명 검색")
async def search(
    request: Request,
    q: str = Query(..., min_length=1, description="검색할 종목명"),
    limit: int = Query(default=10, ge=1, le=30),
):
    """종목명 부분 일치 검색. 네이버 증권 자동완성 API 기반."""
    results = await search_tickers(q, limit=limit, client=request.app.state.http)
    if not results:
        raise _http_error(
            status.HTTP_404_NOT_FOUND,
            "NOT_FOUND",
            f"'{q}'에 해당하는 종목을 찾을 수 없습니다.",
        )
    return results


@router.get("/reports/{ticker}", response_model=list[ReportItem], summary="리포트 목록 수집")
async def get_reports(
    request: Request,
    ticker: str,
    n: int = Query(default=5, ge=1, le=20, description="수집할 리포트 수"),
    days_limit: int = Query(default=90, ge=1, description="리포트 발행 기간 제한 (일)"),
):
    """네이버 증권 리서치에서 해당 종목의 최신 리포트 목록과 PDF URL을 수집한다."""
    try:
        reports = await fetch_reports_with_pdf(ticker, n, days_limit, client=request.app.state.http)
    except Exception as e:
        logger.error("리포트 수집 실패 (ticker=%s): %s", ticker, e)
        raise _http_error(
            status.HTTP_502_BAD_GATEWAY,
            "SCRAPE_FAILED",
            "리포트 수집에 실패했습니다.",
        )

    if not reports:
        raise _http_error(
            status.HTTP_404_NOT_FOUND,
            "NO_REPORTS",
            f"최근 {days_limit}일 내 발행된 리포트가 없습니다.",
        )

    return [
        ReportItem(**report.model_dump())
        for report in reports
    ]


@router.post("/analyze", response_model=AnalyzeResponse, summary="AI 통합 보고서 생성")
async def analyze(body: AnalyzeRequest, request: Request):
    """
    리포트 목록 수집 → PDF 텍스트 추출 → Gemini 통합 분석 보고서 생성.

    - `query`를 제공하면 종목 검색 후 상위 1개 종목으로 자동 진행한다.
    - `ticker` + `name`을 직접 제공해도 된다.
    - `reports`를 함께 넣으면 스크래핑을 건너뛴다.
    """
    try:
        result = await run_research_pipeline(
            body,
            http_client=request.app.state.http,
            gemini_client=request.app.state.gemini,
        )
    except PipelineError as exc:
        raise _http_error(exc.status_code, exc.code, exc.message) from exc

    return result
