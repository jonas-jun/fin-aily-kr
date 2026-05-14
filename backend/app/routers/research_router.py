import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.services.naver_scraper import ReportMeta, fetch_reports_with_pdf
from app.services.pdf_extractor import extract_text_from_pdf_url
from app.services.report_analyzer import AnalysisResult, analyze_reports
from app.services.ticker_resolver import search_tickers

logger = logging.getLogger(__name__)
router = APIRouter(tags=["research"])


# ── 응답 모델 ──────────────────────────────────────────────────────────────────

class TickerItem(BaseModel):
    ticker: str
    name: str
    market: str = ""


class ReportItem(BaseModel):
    nid: str
    title: str
    firm: str
    date: str
    detail_url: str
    pdf_url: str


class AnalyzeRequest(BaseModel):
    ticker: str
    name: str
    n: int = 5
    reports: list[ReportItem] | None = None


class TargetPrice(BaseModel):
    avg: float | None
    min: float | None
    max: float | None


class Opinions(BaseModel):
    buy: int
    neutral: int
    sell: int


class SourceItem(BaseModel):
    firm: str
    title: str
    date: str
    pdf_url: str


class AnalyzeResponse(BaseModel):
    ticker: str
    name: str
    report_count: int
    analyzed_at: str
    opinions: Opinions
    target_price: TargetPrice
    key_points: list[str]
    risks: list[str]
    sources: list[SourceItem]
    model_version: str


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.get("/search", response_model=list[TickerItem], summary="종목명 검색")
async def search(
    q: str = Query(..., min_length=1, description="검색할 종목명"),
    limit: int = Query(default=10, ge=1, le=30),
):
    """종목명 부분 일치 검색. 네이버 증권 자동완성 API 기반."""
    results = await search_tickers(q, limit=limit)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"'{q}'에 해당하는 종목을 찾을 수 없습니다."},
        )
    return results


@router.get("/reports/{ticker}", response_model=list[ReportItem], summary="리포트 목록 수집")
async def get_reports(
    ticker: str,
    n: int = Query(default=5, ge=1, le=20, description="수집할 리포트 수"),
):
    """네이버 증권 리서치에서 해당 종목의 최신 리포트 목록과 PDF URL을 수집한다."""
    try:
        reports = await fetch_reports_with_pdf(ticker, n)
    except Exception as e:
        logger.error("리포트 수집 실패 (ticker=%s): %s", ticker, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "SCRAPE_FAILED", "message": "리포트 수집에 실패했습니다."},
        )

    if not reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NO_REPORTS", "message": f"'{ticker}' 종목의 리포트를 찾을 수 없습니다."},
        )

    return [
        ReportItem(
            nid=r.nid,
            title=r.title,
            firm=r.firm,
            date=r.date,
            detail_url=r.detail_url,
            pdf_url=r.pdf_url,
        )
        for r in reports
    ]


@router.post("/analyze", response_model=AnalyzeResponse, summary="AI 통합 보고서 생성")
async def analyze(body: AnalyzeRequest):
    """
    리포트 목록 수집 → PDF 텍스트 추출 → Gemini 통합 분석 보고서 생성.

    - `reports` 필드에 `/reports/{ticker}` 결과를 그대로 넣으면 스크래핑을 건너뛴다.
    - `reports`를 생략하면 `ticker` + `n` 기준으로 내부에서 직접 수집한다.
    """
    if body.reports is not None:
        reports: list[ReportMeta] = [
            ReportMeta(
                nid=r.nid,
                title=r.title,
                firm=r.firm,
                date=r.date,
                detail_url=r.detail_url,
                pdf_url=r.pdf_url,
            )
            for r in body.reports
        ]
    else:
        try:
            reports = await fetch_reports_with_pdf(body.ticker, body.n)
        except Exception as e:
            logger.error("리포트 수집 실패: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"code": "SCRAPE_FAILED", "message": "리포트 수집에 실패했습니다."},
            )

    if not reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NO_REPORTS", "message": "분석할 리포트가 없습니다."},
        )

    texts: list[str] = await asyncio.gather(
        *[extract_text_from_pdf_url(r.pdf_url) for r in reports]
    )

    try:
        result: AnalysisResult = await analyze_reports(
            ticker=body.ticker,
            name=body.name,
            reports=reports,
            texts=list(texts),
        )
    except Exception as e:
        logger.error("Gemini 분석 실패: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ANALYSIS_FAILED", "message": "보고서 생성에 실패했습니다."},
        )

    return AnalyzeResponse(
        ticker=result.ticker,
        name=result.name,
        report_count=result.report_count,
        analyzed_at=result.analyzed_at,
        opinions=Opinions(**result.opinions),
        target_price=TargetPrice(**result.target_price),
        key_points=result.key_points,
        risks=result.risks,
        sources=[SourceItem(**s) for s in result.sources],
        model_version=result.model_version,
    )
