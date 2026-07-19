import asyncio
import logging
from typing import Any, Protocol

import httpx
from google import genai

from app.models.schemas import AnalyzeResponse, ReportInput, ReportMeta
from app.services.dart_service import fetch_dart_data, fetch_dart_filing_texts
from app.services.naver_scraper import fetch_reports_with_pdf
from app.services.pdf_extractor import extract_text_from_pdf_url
from app.services.price_fetcher import fetch_current_price
from app.services.report_analyzer import analyze_reports
from app.services.ticker_resolver import search_tickers

logger = logging.getLogger(__name__)

PDF_EXTRACTION_CONCURRENCY = 2


class AnalyzeRequestData(Protocol):
    query: str | None
    ticker: str | None
    name: str | None
    n: int
    days_limit: int
    reports: list[Any] | None


class PipelineError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


async def resolve_ticker(
    body: AnalyzeRequestData,
    client: httpx.AsyncClient,
) -> tuple[str, str]:
    if body.query:
        results = await search_tickers(body.query, limit=1, client=client)
        if not results:
            raise PipelineError(
                404,
                "NOT_FOUND",
                f"'{body.query}'에 해당하는 종목을 찾을 수 없습니다.",
            )
        return results[0]["ticker"], results[0]["name"]

    if body.ticker and body.name:
        return body.ticker, body.name

    raise PipelineError(
        422,
        "MISSING_FIELDS",
        "'query' 또는 'ticker'+'name'을 제공해야 합니다.",
    )


async def collect_reports(
    body: AnalyzeRequestData,
    ticker: str,
    client: httpx.AsyncClient,
) -> list[ReportMeta]:
    if body.reports is not None and not body.query:
        return [
            ReportMeta(**report.model_dump())
            for report in body.reports
        ]

    try:
        return await fetch_reports_with_pdf(
            ticker,
            body.n,
            body.days_limit,
            client=client,
        )
    except Exception as exc:
        logger.error("리포트 수집 실패: %s", exc)
        raise PipelineError(502, "SCRAPE_FAILED", "리포트 수집에 실패했습니다.") from exc


async def run_research_pipeline(
    body: AnalyzeRequestData,
    http_client: httpx.AsyncClient,
    gemini_client: genai.Client | None,
) -> AnalyzeResponse:
    ticker, name = await resolve_ticker(body, http_client)
    reports = await collect_reports(body, ticker, http_client)

    if not reports:
        dart_data, dart_filings, current_price = await asyncio.gather(
            fetch_dart_data(ticker, client=http_client),
            fetch_dart_filing_texts(ticker, client=http_client),
            fetch_current_price(ticker, client=http_client),
        )
        if not dart_data and not dart_filings:
            raise PipelineError(
                404,
                "NO_DATA",
                f"최근 {body.days_limit}일 내 발행된 리포트가 없고 "
                "DART 공시 데이터도 조회되지 않았습니다.",
            )
        report_inputs: list[ReportInput] = []
        dart_only = True
    else:
        semaphore = asyncio.Semaphore(PDF_EXTRACTION_CONCURRENCY)

        async def extract_with_limit(url: str) -> str:
            async with semaphore:
                return await extract_text_from_pdf_url(url, client=http_client)

        fetched_texts, current_price, dart_data, dart_filings = await asyncio.gather(
            asyncio.gather(*[extract_with_limit(report.pdf_url) for report in reports]),
            fetch_current_price(ticker, client=http_client),
            fetch_dart_data(ticker, client=http_client),
            fetch_dart_filing_texts(ticker, client=http_client),
        )
        report_inputs = [
            ReportInput(**report.model_dump(), text=text)
            for report, text in zip(reports, fetched_texts)
        ]
        dart_only = False

    try:
        analysis = await analyze_reports(
            ticker=ticker,
            name=name,
            reports=report_inputs,
            current_price=current_price,
            dart_data=dart_data or None,
            dart_filings=dart_filings or None,
            dart_only=dart_only,
            client=gemini_client,
        )
    except Exception as exc:
        logger.error("Gemini 분석 실패: %s", exc)
        raise PipelineError(503, "ANALYSIS_FAILED", "보고서 생성에 실패했습니다.") from exc

    return analysis
