import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from google import genai

from app.config import get_feature_config, get_settings
from app.services.naver_scraper import ReportMeta

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    ticker: str
    name: str
    report_count: int
    analyzed_at: str
    target_price: dict    # {"avg": n, "min": n, "max": n} — 없으면 None
    key_points: list[str]
    risks: list[str]
    sources: list[dict]   # [{"firm", "title", "date", "pdf_url", "target_price"}]
    model_version: str
    corporate_filings_analysis: dict | None = None  # DART 공시 분석 결과


def _build_dart_block(dart_data: list[dict]) -> str:
    if not dart_data:
        return ""
    lines = ["## DART 공시 재무 데이터 (최근 분기)"]
    for q in dart_data:
        rev = f"{q['revenue']:,}" if q.get("revenue") is not None else "N/A"
        op = f"{q['operating_income']:,}" if q.get("operating_income") is not None else "N/A"
        ni = f"{q['net_income']:,}" if q.get("net_income") is not None else "N/A"
        lines.append(f"- {q['period']}: 매출액 {rev}원, 영업이익 {op}원, 당기순이익 {ni}원")
    return "\n".join(lines) + "\n"


def _build_prompt(ticker: str, name: str, reports: list[dict], dart_data: list[dict] | None = None) -> str:
    reports_block = ""
    for i, r in enumerate(reports, 1):
        text = r.get("text") or "(본문 추출 실패 — 제목과 메타데이터만 사용)"
        reports_block += (
            f"[리포트 {i}]\n"
            f"증권사: {r['firm']}\n"
            f"날짜: {r['date']}\n"
            f"제목: {r['title']}\n"
            f"본문:\n{text}\n\n"
        )

    dart_block = _build_dart_block(dart_data or [])
    has_dart = bool(dart_block)

    dart_instruction = ""
    dart_schema = ""
    if has_dart:
        dart_instruction = (
            "5. DART 공시 재무 데이터를 바탕으로 다음을 분석하세요:\n"
            "   - 분기별 매출 구조의 변화 트렌드\n"
            "   - 분기별 영업이익 증감율 및 실적 흐름\n"
            "   - 애널리스트 리포트 내용과 공시 데이터 간의 일치 여부 또는 차이점\n"
        )
        dart_schema = """,
  "corporate_filings_analysis": {{
    "revenue_structure_change": "매출 구조 및 비중 변화 내용 설명",
    "profit_trend": "분기별 이익 증감율 및 실적 흐름 요약",
    "key_changes": ["리포트-공시 간 차이점 또는 주목할 변화 포인트"]
  }}"""

    return f"""당신은 한국 주식 리서치 분석 전문가입니다.
아래 {name}({ticker})에 대한 {len(reports)}개의 증권사 리포트를 분석하여 투자자에게 유용한 통합 보고서를 작성하세요.

## 지시사항
1. 각 리포트의 목표주가를 파악하세요. 명시되지 않은 경우 null로 처리하세요.
2. 공통적으로 언급되는 핵심 투자 포인트를 중요도 순으로 정리하세요.
3. 주요 리스크 요인을 정리하세요.
4. 한국어로 작성하세요.
{dart_instruction}
## 응답 형식 (반드시 아래 JSON만 출력)
{{
  "report_target_prices": [null],
  "target_price": {{"avg": null, "min": null, "max": null}},
  "key_points": ["포인트1", "포인트2", "포인트3"],
  "risks": ["리스크1", "리스크2"]{dart_schema}
}}

참고: "report_target_prices"는 리포트 순서대로 목표주가를 배열로 반환 (미제시 시 null)

## 리포트 데이터
{reports_block}{dart_block}"""


def _parse_response(raw: str) -> dict:
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    return json.loads(raw.strip())


async def analyze_reports(
    ticker: str,
    name: str,
    reports: list[ReportMeta],
    texts: list[str],
    dart_data: list[dict] | None = None,
) -> AnalysisResult:
    settings = get_settings()
    feat = get_feature_config("krx_report")

    report_dicts = [
        {
            "firm": r.firm,
            "date": r.date,
            "title": r.title,
            "text": texts[i] if i < len(texts) else "",
        }
        for i, r in enumerate(reports)
    ]

    prompt = _build_prompt(ticker, name, report_dicts, dart_data=dart_data)

    client = genai.Client(api_key=settings.gemini_api_key)
    response = await client.aio.models.generate_content(
        model=feat.model,
        contents=prompt,
    )

    if not response.text:
        raise ValueError("Gemini returned empty response (possible safety filter or empty input)")

    parsed = _parse_response(response.text)

    target = parsed.get("target_price", {}) or {}
    target_price = {
        "avg": target.get("avg"),
        "min": target.get("min"),
        "max": target.get("max"),
    }

    report_target_prices = parsed.get("report_target_prices", [])
    sources = [
        {
            "firm": r.firm,
            "title": r.title,
            "date": r.date,
            "pdf_url": r.pdf_url,
            "target_price": report_target_prices[i] if i < len(report_target_prices) else None,
        }
        for i, r in enumerate(reports)
    ]

    filings_raw = parsed.get("corporate_filings_analysis")
    corporate_filings_analysis = (
        {
            "revenue_structure_change": filings_raw.get("revenue_structure_change", ""),
            "profit_trend": filings_raw.get("profit_trend", ""),
            "key_changes": filings_raw.get("key_changes", []),
        }
        if isinstance(filings_raw, dict)
        else None
    )

    return AnalysisResult(
        ticker=ticker,
        name=name,
        report_count=len(reports),
        analyzed_at=datetime.now(timezone(timedelta(hours=9))).date().isoformat(),
        target_price=target_price,
        key_points=parsed.get("key_points", []),
        risks=parsed.get("risks", []),
        sources=sources,
        model_version=feat.model,
        corporate_filings_analysis=corporate_filings_analysis,
    )
