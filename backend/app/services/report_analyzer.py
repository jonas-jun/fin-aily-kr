import asyncio
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
    sources: list[dict]   # [{"firm", "title", "date", "pdf_url", "target_price"}]
    model_version: str
    full_report: str | None = None  # 마크다운 전문 보고서
    dart_only: bool = False         # 증권사 리포트 없이 DART 데이터만으로 생성된 경우


def _build_reports_block(reports: list[dict]) -> str:
    block = ""
    for i, r in enumerate(reports, 1):
        text = r.get("text") or "(본문 추출 실패 — 제목과 메타데이터만 사용)"
        block += (
            f"[리포트 {i}]\n"
            f"증권사: {r['firm']}\n"
            f"날짜: {r['date']}\n"
            f"제목: {r['title']}\n"
            f"본문:\n{text}\n\n"
        )
    return block


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


def _build_target_price_prompt(reports: list[dict]) -> str:
    reports_block = _build_reports_block(reports)
    return f"""아래 증권사 리포트에서 각 리포트의 목표주가만 추출하세요.

## 응답 형식 (반드시 아래 JSON만 출력)
{{
  "report_target_prices": [null],
  "target_price": {{"avg": null, "min": null, "max": null}}
}}

참고: "report_target_prices"는 리포트 순서대로 목표주가를 배열로 반환 (미제시 시 null)

## 리포트 데이터
{reports_block}"""


def _build_dart_filings_block(dart_filings: list[dict]) -> str:
    if not dart_filings:
        return ""
    lines = ["## DART 공시 문서 원문 (최근 정기공시)"]
    for i, f in enumerate(dart_filings, 1):
        lines.append(f"\n[공시 {i}: {f['title']} ({f['date']})]\n{f['text']}")
    return "\n".join(lines) + "\n"


def _build_dart_only_prompt(name: str, dart_block: str, dart_filings_block: str) -> str:
    return f"""당신은 대한민국 상장 기업 전문 기관투자자급 주식 리서치 애널리스트입니다.
증권사 리포트가 제공되지 않아, DART 공시 재무 데이터 및 공시 문서 원문만을 바탕으로 심층 투자 리포트를 한국어로 작성하라.

[기업명] {name}

데이터 원칙
1. 분석 근거는 제공된 DART 분기별 재무 데이터 및 공시 문서 원문으로 한정한다.
2. 수치는 원본 데이터에 명시된 검증 가능한 숫자만 인용하며, 확인 불가한 사항은 "제공 데이터 내 확인 불가"로 명시한다.
3. 증권사 리포트가 없으므로 컨센서스·목표주가 분석은 생략하고, 해당 항목에 그 사실을 명시한다.

보고서 구성
1. 투자 요약 (Investment Summary)
   - DART 공시를 통해 확인된 기업의 핵심 투자 논지(Thesis)와 리스크 요약 (3줄 이내)

2. 사업 및 재무 성과 분석 (DART 공시 기준)
   - 최근 분기별 매출액, 영업이익, 순이익, 마진율(OPM) 추이 분석 (반드시 표(Table) 활용)
   - 주요 세그먼트 변화 및 특이사항 (자본지출, 연구개발비 등)

3. 공시 변화 분석 (Filing Delta)
   - 최신 공시를 이전 공시와 비교하여 **새롭게 추가·삭제되거나 수정된 핵심 문구**를 포착하라.
   - **[사업의 내용]** 내 신규 사업 추진이나 주요 고객사 변동, **[재무제표 주석]**의 우발부채/소송 사건, **[투자자 보호를 위한 사항]** 섹션의 잠재적 리스크나 전략 변화를 암시하는 문장 변동을 찾아 의미를 해석하라.

4. 증권사 뷰 및 컨센서스 분석
   - 증권사 리포트가 제공되지 않아 본 섹션은 작성 불가. 이 사실을 명시하고 해당 데이터 부재로 인한 분석 한계를 설명하라.

5. 핵심 리스크 요인 (Risk Factors)
   - DART 공시에서 확인된 실질적 위험 요인

6. 최종 종합 평가
   - 공시 펀더멘탈 기준 결론 (시장 컨센서스 부재 명시)

작성 지침
- 단순 수치 나열을 지양하고, '시간에 따른 변화(Trend)'와 '전분기 대비/전년동기 대비 변동 원인' 중심으로 서술하라.
- 가독성을 위해 핵심 문장은 볼드(**) 처리하고, 수치 비교는 표(Table)를 적극 활용하라.

{dart_block}
{dart_filings_block}"""


def _build_full_report_prompt(name: str, reports_block: str, dart_block: str) -> str:
    return f"""당신은 대한민국 상장 기업 전문 기관투자자급 주식 리서치 애널리스트입니다.
제공된 기업의 [최근 4개 분기 보고서/사업보고서(DART)]와 [최근 5개 증권사 리포트]만을 바탕으로, 외부 데이터 없이 오직 내부 1차 출처에만 기반한 심층 투자 리포트를 한국어로 작성하라.

[기업명] {name}

데이터 원칙
1. 분석 근거는 제공된 '최근 4개 분기 공시' 및 '최근 5개 증권사 리포트'로 한정한다.
2. 수치는 원본 데이터에 명시된 검증 가능한 숫자만 인용하며, 확인 불가한 사항은 임의 추정 없이 "제공 데이터 내 확인 불가"로 명시한다.
3. [공시 기반 사실(Fact)], [증권사 시각(Market View)], [본인의 객관적 해석(Analysis)]을 명확히 구분하여 기술한다.

보고서 구성
1. 투자 요약 (Investment Summary)
   - 공시와 리포트를 통해 확인된 기업의 핵심 투자 논지(Thesis)와 리스크 요약 (3줄 이내)

2. 사업 및 재무 성과 분석 (DART 공시 기준)
   - 최근 4개 분기 매출액, 영업이익, 순이익, 마진율(GPM, OPM) 추이 분석 (반드시 표(Table) 활용)
   - 주요 제품/서비스 세그먼트별 매출 비중 변화 및 특이사항 (ex. 자본지출(CapEx) 이나 연구개발비 변동)

3. 공시 변화 분석 (Filing Delta)
   - 최신 공시를 이전 공시(직전 분기 또는 전년 동기)와 비교하여 **새롭게 추가·삭제되거나 수정된 핵심 문구**를 포착하라.
   - 특히 **[사업의 내용]** 내 신규 사업 추진이나 주요 고객사 변동, **[재무제표 주석]**의 우발부채/소송 사건, **[투자자 보호를 위한 사항]** 섹션에서 기업의 잠재적 리스크나 전략 변화를 암시하는 미세한 문장 변동을 찾아내고 그 의미를 해석하라.

4. 증권사 뷰 및 컨센서스 분석 (리포트 5사 기준)
   - 5개 증권사 리포트의 공통 투자 포인트 및 목표주가 추이/의견 변화 추적
   - 시장이 기대하는 향후 성장 동력과 실적 컨센서스의 핵심 가정 사항

5. 핵심 리스크 요인 (Risk Factors)
   - DART 공시와 증권사 리포트에서 공통 또는 개별적으로 지적한 실질적 위험 요인 (ex. 전방 산업 둔화, 고객사 집중도 리스크 등)

6. 최종 종합 평가
   - 외부 노이즈를 제외하고, 공시된 펀더멘탈과 증권사들이 바라보는 시장의 기대치 간의 간극을 종합한 결론

작성 지침
- 단순 수치 나열을 지양하고, '시간에 따른 변화(Trend)'와 '전분기 대비/전년동기 대비 변동 원인' 중심으로 서술하라.
- 가독성을 위해 핵심 문장은 볼드(**) 처리하고, 수치 비교는 표(Table)를 적극 활용하라.
- 범용적인 산업 설명은 배제하고, 이 기업 고유의 데이터와 인사이트에만 집중하라.

## 증권사 리포트 데이터
{reports_block}
{dart_block}"""


def _parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    return json.loads(raw.strip())


async def _extract_target_prices(
    client: genai.Client,
    model: str,
    reports: list[dict],
) -> dict:
    prompt = _build_target_price_prompt(reports)
    response = await client.aio.models.generate_content(model=model, contents=prompt)
    if not response.text:
        return {"report_target_prices": [], "target_price": {"avg": None, "min": None, "max": None}}
    try:
        return _parse_json_response(response.text)
    except Exception:
        logger.warning("목표주가 JSON 파싱 실패 — 기본값 반환")
        return {"report_target_prices": [], "target_price": {"avg": None, "min": None, "max": None}}


async def _generate_full_report(
    client: genai.Client,
    model: str,
    name: str,
    reports: list[dict],
    dart_data: list[dict] | None,
    dart_filings: list[dict] | None = None,
    dart_only: bool = False,
) -> str | None:
    dart_block = _build_dart_block(dart_data or [])
    if dart_only:
        dart_filings_block = _build_dart_filings_block(dart_filings or [])
        prompt = _build_dart_only_prompt(name, dart_block, dart_filings_block)
    else:
        reports_block = _build_reports_block(reports)
        prompt = _build_full_report_prompt(name, reports_block, dart_block)
    response = await client.aio.models.generate_content(model=model, contents=prompt)
    return response.text or None


async def analyze_reports(
    ticker: str,
    name: str,
    reports: list[ReportMeta],
    texts: list[str],
    dart_data: list[dict] | None = None,
    dart_filings: list[dict] | None = None,
    dart_only: bool = False,
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

    client = genai.Client(api_key=settings.gemini_api_key)

    if dart_only:
        full_report = await _generate_full_report(
            client, feat.model, name, [], dart_data, dart_filings, dart_only=True
        )
        target_price = {"avg": None, "min": None, "max": None}
        sources = []
    else:
        target_parsed, full_report = await asyncio.gather(
            _extract_target_prices(client, feat.model, report_dicts),
            _generate_full_report(client, feat.model, name, report_dicts, dart_data),
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
                "firm": r.firm,
                "title": r.title,
                "date": r.date,
                "pdf_url": r.pdf_url,
                "target_price": report_target_prices[i] if i < len(report_target_prices) else None,
            }
            for i, r in enumerate(reports)
        ]

    return AnalysisResult(
        ticker=ticker,
        name=name,
        report_count=len(reports),
        analyzed_at=datetime.now(timezone(timedelta(hours=9))).date().isoformat(),
        target_price=target_price,
        sources=sources,
        model_version=feat.model,
        full_report=full_report,
        dart_only=dart_only,
    )
