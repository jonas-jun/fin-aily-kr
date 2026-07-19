import asyncio
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from google import genai

from app.config import get_feature_config, get_settings
from app.services.analysis.gemini import _extract_target_prices, _generate_full_report
from app.services.naver_scraper import ReportMeta


@dataclass
class AnalysisResult:
    ticker: str
    name: str
    report_count: int
    analyzed_at: str
    target_price: dict
    sources: list[dict]
    model_version: str
    full_report: str | None = None
    dart_only: bool = False


async def analyze_reports(
    ticker: str,
    name: str,
    reports: list[ReportMeta],
    texts: list[str],
    dart_data: list[dict] | None = None,
    dart_filings: list[dict] | None = None,
    dart_only: bool = False,
    client: genai.Client | None = None,
) -> AnalysisResult:
    settings = get_settings()
    feature = get_feature_config("krx_report")
    report_dicts = [
        {
            "firm": report.firm,
            "date": report.date,
            "title": report.title,
            "text": texts[index] if index < len(texts) else "",
        }
        for index, report in enumerate(reports)
    ]
    client = client or genai.Client(api_key=settings.gemini_api_key)

    if dart_only:
        full_report = await _generate_full_report(
            client,
            feature.model,
            name,
            [],
            dart_data,
            dart_filings,
            dart_only=True,
        )
        target_price = {"avg": None, "min": None, "max": None}
        sources = []
    else:
        target_parsed, full_report = await asyncio.gather(
            _extract_target_prices(client, feature.model, report_dicts),
            _generate_full_report(
                client,
                feature.model,
                name,
                report_dicts,
                dart_data,
                dart_filings,
            ),
        )
        target = target_parsed.get("target_price", {}) or {}
        target_price = {
            "avg": target.get("avg"),
            "min": target.get("min"),
            "max": target.get("max"),
        }
        report_target_prices = target_parsed.get("report_target_prices", [])
        sources = [
            {
                "firm": report.firm,
                "title": report.title,
                "date": report.date,
                "pdf_url": report.pdf_url,
                "target_price": (
                    report_target_prices[index]
                    if index < len(report_target_prices)
                    else None
                ),
            }
            for index, report in enumerate(reports)
        ]

    return AnalysisResult(
        ticker=ticker,
        name=name,
        report_count=len(reports),
        analyzed_at=datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
        target_price=target_price,
        sources=sources,
        model_version=feature.model,
        full_report=full_report,
        dart_only=dart_only,
    )
