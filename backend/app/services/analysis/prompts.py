from app.services.analysis.formatting import _build_reports_block


_DATA_ABSENCE_RULE = """\
4. 각 섹션은 해당 섹션에 필요한 데이터가 입력에 포함된 경우에만 작성한다.
   데이터가 없는 섹션은 제목 아래에 '데이터 없음 — [이유]' 한 줄만 기재하고,
   일반 지식이나 추론으로 내용을 채우지 않는다."""

_SECTION_ABSENCE = {
    "broker":   "데이터 없음 — 증권사 리포트 미제공 또는 본문 추출 실패",
    "dart_fin": "데이터 없음 — DART 재무 데이터 미수집",
    "dart_doc": "데이터 없음 — 공시 원문 미수집",
}


def _build_full_report_prompt(
    name: str,
    reports_block: str,
    dart_block: str,
    dart_filings_block: str,
    broker_texts_available: bool,
) -> str:
    extra_rules = []
    if not broker_texts_available:
        extra_rules.append(
            "5. 증권사 리포트 본문이 모두 추출되지 않았다. "
            "§6(증권사 뷰)·§7(기대치 검증) 섹션에 "
            f"'{_SECTION_ABSENCE['broker']}' 한 줄만 기재하라."
        )
    if not dart_block.strip():
        extra_rules.append(
            "6. DART 재무 데이터가 제공되지 않았다. "
            "§2(재무 성과)·§3(현금흐름)·§4(사업부문) 섹션에 "
            f"'{_SECTION_ABSENCE['dart_fin']}' 한 줄만 기재하라."
        )
    if not dart_filings_block.strip():
        extra_rules.append(
            "7. DART 공시 원문이 제공되지 않았다. "
            "§5(공시 변화) 섹션에 "
            f"'{_SECTION_ABSENCE['dart_doc']}' 한 줄만 기재하라."
        )
    extra = ("\n" + "\n".join(extra_rules)) if extra_rules else ""

    return f"""당신은 대한민국 상장 기업 전문 기관투자자급 주식 리서치 애널리스트입니다.
제공된 데이터만을 근거로 심층 투자 리포트를 한국어로 작성하라.

[기업명] {name}

데이터 원칙
1. 분석 근거는 제공된 DART 재무 데이터와 증권사 리포트로 한정한다.
2. 수치는 입력 데이터에 명시된 검증 가능한 숫자만 인용하며, 확인 불가한 사항은 "제공 데이터 내 확인 불가"로 명시한다.
3. [공시 기반 사실(Fact)], [증권사 시각(Market View)], [분석(Analysis)]을 명확히 구분하여 기술한다.
{_DATA_ABSENCE_RULE}{extra}

보고서 구성 (반드시 아래 10개 섹션을 순서대로 작성)

## 1. 투자 요약 (Investment Summary)
- 공시와 리포트를 통해 확인된 핵심 투자 논지(Thesis)와 리스크를 3줄 이내로 요약한다.
- 이용 가능한 데이터 범위 내에서만 작성하고, 없는 정보는 '확인 불가'로 표기한다.

## 2. 사업 및 재무 성과 분석
- 재무 테이블은 자동 삽입되므로 직접 작성하지 말 것.
- 제공된 DART 재무 데이터를 기반으로 매출·영업이익·순이익 변동 원인과 트렌드 분석 텍스트만 서술하라.

## 3. 현금흐름 및 운전자본 분석
- 제공된 영업CF, CapEx, FCF, 재고자산, 매출채권, 순차입금 데이터를 분석한다.
- 순이익 대비 영업CF 괴리가 있다면 이익의 질(earnings quality) 관점에서 해석한다.
- 재고·매출채권 증가는 수요 둔화·회수 지연 리스크와 연결하여 해석한다.

## 4. 사업부문 및 성장 투자 분석
- 공시 원문의 주요 제품·서비스, 매출 및 수주상황 섹션을 바탕으로 세그먼트 변화를 분석한다.
- CapEx, R&D 비용 변화를 성장 투자 강도의 지표로 해석한다.
- 수주잔고가 있다면 향후 매출 가시성 관점에서 분석한다.

## 5. 공시 변화 분석 (Filing Delta)
- 최신 공시를 이전 공시와 비교하여 **새롭게 추가·삭제·수정된 핵심 문구**를 포착하라.
- [사업의 내용] 내 신규 사업·고객사 변동, [재무제표 주석]의 우발부채·소송, [투자자 보호 사항]의 리스크·전략 변화를 중점 분석한다.
- 변경 항목은 표(섹션 | 변경유형 | 이전 문구 | 최신 문구 | 해석 | 중요도)로 정리한다.

## 6. 증권사 뷰 및 컨센서스 분석
- 증권사별 투자의견, 목표주가, 직전 대비 변화, 핵심 투자 포인트를 표로 정리한다.
- 공통 투자 포인트, 의견 차이, 핵심 가정(성장률·마진·멀티플)을 분석한다.
- **목표주가 자체보다 목표주가를 만든 핵심 가정이 무엇인지 분석하라.**

## 7. 공시 데이터 vs 증권사 기대치 검증
- **비교 대상은 DART 재무 데이터의 최신 1개 분기**로 한정한다.
- 증권사 리포트에서 해당 분기에 대한 수치 추정(매출액, 영업이익, 순이익 등)을 추출하고, DART 실제값과 비교하라.
- 판정 형식: 수치 비교가 가능한 항목은 반드시 '**+n.n% 상회**' 또는 '**-n.n% 하회**' 형태로 계산하여 표기한다. 수치 비교가 불가한 항목은 '**확인 불가**'로 표기한다.
- 표(증권사 추정 | 실제(DART) | 판정)로 정리한다.

## 8. 핵심 리스크 요인
- DART 공시와 증권사 리포트에서 확인된 리스크를 표(리스크 | 출처 | 심각도 | 근거 | 투자 영향)로 정리한다.
- 심각도: High / Medium / Low, 출처: DART / Broker Report / Both

## 9. 다음 분기 체크포인트
- 현재 분석에서 가장 불확실한 항목 3~5개를 선정한다.
- 각각에 대해 표(체크포인트 | 확인 이유 | 긍정 신호 | 부정 신호)로 정리한다.

## 10. 최종 종합 평가
- 공시 펀더멘탈과 증권사 기대치 간의 간극을 종합하여 결론을 제시한다.
- 투자 관점: 긍정 / 중립 / 주의 중 하나로 명시하고, 조건부 판단 기준을 함께 제시한다.

작성 지침
- 단순 수치 나열을 지양하고 변화의 원인과 투자 의미 중심으로 서술한다.
- 핵심 문장은 볼드(**) 처리한다.
- 범용 산업 설명은 배제하고 이 기업 고유 데이터에만 집중한다.

{dart_block}
{dart_filings_block}
## 증권사 리포트 데이터
{reports_block}"""


def _build_dart_only_prompt(
    name: str,
    dart_block: str,
    dart_filings_block: str,
) -> str:
    dart_fin_available = bool(dart_block.strip())
    dart_doc_available = bool(dart_filings_block.strip())

    extra_rules = [
        "5. 증권사 리포트가 제공되지 않았다. §6·§7 섹션에 "
        f"'{_SECTION_ABSENCE['broker']}' 한 줄만 기재하라."
    ]
    if not dart_fin_available:
        extra_rules.append(
            "6. DART 재무 데이터가 제공되지 않았다. §2·§3·§4 섹션에 "
            f"'{_SECTION_ABSENCE['dart_fin']}' 한 줄만 기재하라."
        )
    if not dart_doc_available:
        extra_rules.append(
            "7. DART 공시 원문이 제공되지 않았다. §5 섹션에 "
            f"'{_SECTION_ABSENCE['dart_doc']}' 한 줄만 기재하라."
        )
    extra = "\n" + "\n".join(extra_rules)

    return f"""당신은 대한민국 상장 기업 전문 기관투자자급 주식 리서치 애널리스트입니다.
증권사 리포트가 제공되지 않아 DART 공시 데이터만으로 투자 리포트를 한국어로 작성하라.

[기업명] {name}

데이터 원칙
1. 분석 근거는 제공된 DART 재무 데이터 및 공시 문서 원문으로 한정한다.
2. 수치는 입력 데이터에 명시된 검증 가능한 숫자만 인용하며, 확인 불가한 사항은 "제공 데이터 내 확인 불가"로 명시한다.
3. 증권사 리포트가 없으므로 컨센서스·목표주가 분석은 생략하고, 해당 항목에 그 사실을 명시한다.
{_DATA_ABSENCE_RULE}{extra}

보고서 구성 (반드시 아래 10개 섹션을 순서대로 작성)

## 1. 투자 요약 (Investment Summary)
- DART 공시를 통해 확인된 핵심 투자 논지와 리스크를 3줄 이내로 요약한다.

## 2. 사업 및 재무 성과 분석
- 재무 테이블은 자동 삽입되므로 직접 작성하지 말 것.
- 제공된 DART 재무 데이터를 기반으로 매출·영업이익·순이익 변동 원인과 트렌드 분석 텍스트만 서술하라.

## 3. 현금흐름 및 운전자본 분석
- 영업CF, CapEx, FCF, 재고자산, 매출채권, 순차입금 데이터를 분석한다.
- 이익의 질(영업CF vs 순이익)과 운전자본 리스크를 해석한다.

## 4. 사업부문 및 성장 투자 분석
- 공시 원문의 주요 제품·서비스, 수주상황, CapEx·R&D 변화를 분석한다.

## 5. 공시 변화 분석 (Filing Delta)
- 최신 공시와 이전 공시를 비교하여 핵심 문구 변화를 표로 정리한다.

## 6. 증권사 뷰 및 컨센서스 분석
데이터 없음 — 증권사 리포트 미제공

## 7. 공시 데이터 vs 증권사 기대치 검증
데이터 없음 — 증권사 리포트 미제공

## 8. 핵심 리스크 요인
- DART 공시에서 확인된 실질적 위험 요인을 표로 정리한다.

## 9. 다음 분기 체크포인트
- 가장 불확실한 항목 3~5개를 선정하고, 긍정/부정 신호를 표로 정리한다.

## 10. 최종 종합 평가
- 공시 펀더멘탈 기준 결론과 투자 관점(긍정/중립/주의)을 제시한다.
- 시장 컨센서스 부재 사실을 명시한다.

작성 지침
- 단순 수치 나열을 지양하고 변화의 원인과 투자 의미 중심으로 서술한다.
- 핵심 문장은 볼드(**) 처리한다.

{dart_block}
{dart_filings_block}"""


def _build_target_price_prompt(reports: list[dict]) -> str:
    block = _build_reports_block(reports)
    return f"""아래 증권사 리포트에서 각 리포트의 목표주가만 추출하세요.

## 응답 형식 (반드시 아래 JSON만 출력)
{{
  "report_target_prices": [null],
  "target_price": {{"avg": null, "min": null, "max": null}}
}}

참고: "report_target_prices"는 리포트 순서대로 목표주가를 배열로 반환 (미제시 시 null)

## 리포트 데이터
{block}"""
