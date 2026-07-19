import re

from app.services.metrics import enrich_quarters


def _has_usable_broker_texts(reports: list[dict]) -> bool:
    return any(
        bool(report.get("text"))
        and report["text"] != "(본문 추출 실패 — 제목과 메타데이터만 사용)"
        for report in reports
    )


def _build_reports_block(reports: list[dict]) -> str:
    block = ""
    for index, report in enumerate(reports, 1):
        text = report.get("text") or "(본문 추출 실패 — 제목과 메타데이터만 사용)"
        block += (
            f"[리포트 {index}]\n"
            f"증권사: {report['firm']}\n"
            f"날짜: {report['date']}\n"
            f"제목: {report['title']}\n"
            f"본문:\n{text}\n\n"
        )
    return block


def _fmt(value: int | float | None, unit: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:+.1f}%"
    return f"{value:,}{unit}"


def _fmt_eok(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{round(value / 1e8, 1):,.0f}억"


def _build_is_table(dart_data: list[dict]) -> str:
    if not dart_data:
        return ""
    enriched = enrich_quarters(dart_data)
    lines = [
        "*연결재무제표 기준*",
        "",
        "| 분기 | 매출액(억) | 영업이익(억) | OPM | 순이익(억) | NPM |",
        "|------|----------:|------------:|----:|----------:|----:|",
    ]
    for quarter in enriched:
        lines.append(
            f"| {quarter['period']}"
            f" | {_fmt_eok(quarter.get('revenue'))}"
            f" | {_fmt_eok(quarter.get('operating_income'))}"
            f" | {_fmt(quarter.get('opm'))}"
            f" | {_fmt_eok(quarter.get('net_income'))}"
            f" | {_fmt(quarter.get('npm'))}"
            f" |"
        )
    return "\n".join(lines)


def _inject_is_table(report_text: str, is_table: str) -> str:
    if not is_table or not report_text:
        return report_text
    match = re.search(r"(##\s*2[\.。．].*?\n)", report_text)
    if not match:
        return report_text
    position = match.end()
    return report_text[:position] + "\n" + is_table + "\n\n" + report_text[position:]


def _build_dart_block(dart_data: list[dict]) -> str:
    if not dart_data:
        return ""
    enriched = enrich_quarters(dart_data)
    lines = [
        "## DART 공시 재무 데이터 (최근 분기)",
        "",
        "### 손익계산서",
        "| 분기 | 매출액 | YoY | QoQ | 영업이익 | OPM | 순이익 | NPM |",
        "|------|-------:|----:|----:|---------:|----:|-------:|----:|",
    ]
    for quarter in enriched:
        lines.append(
            f"| {quarter['period']}"
            f" | {_fmt(quarter.get('revenue'), '원')}"
            f" | {_fmt(quarter.get('revenue_yoy'))}"
            f" | {_fmt(quarter.get('revenue_qoq'))}"
            f" | {_fmt(quarter.get('operating_income'), '원')}"
            f" | {_fmt(quarter.get('opm'))}"
            f" | {_fmt(quarter.get('net_income'), '원')}"
            f" | {_fmt(quarter.get('npm'))}"
            f" |"
        )

    lines.extend([
        "",
        "### 현금흐름 및 운전자본",
        "| 분기 | 영업CF | CapEx | FCF | 재고자산 | 매출채권 | 순차입금 |",
        "|------|-------:|------:|----:|---------:|---------:|---------:|",
    ])
    for quarter in enriched:
        capex_abs = abs(quarter["capex"]) if quarter.get("capex") is not None else None
        lines.append(
            f"| {quarter['period']}"
            f" | {_fmt(quarter.get('cfo'), '원')}"
            f" | {_fmt(capex_abs, '원')}"
            f" | {_fmt(quarter.get('fcf'), '원')}"
            f" | {_fmt(quarter.get('inventory'), '원')}"
            f" | {_fmt(quarter.get('receivables'), '원')}"
            f" | {_fmt(quarter.get('net_debt'), '원')}"
            f" |"
        )

    lines.extend([
        "",
        "### 재무상태표 (기말 기준)",
        "| 분기 | 현금 | 총자산 | 자본총계 | 단기차입금 | 장기차입금 |",
        "|------|-----:|-------:|---------:|-----------:|-----------:|",
    ])
    for quarter in enriched:
        lines.append(
            f"| {quarter['period']}"
            f" | {_fmt(quarter.get('cash'), '원')}"
            f" | {_fmt(quarter.get('total_assets'), '원')}"
            f" | {_fmt(quarter.get('equity'), '원')}"
            f" | {_fmt(quarter.get('short_term_debt'), '원')}"
            f" | {_fmt(quarter.get('long_term_debt'), '원')}"
            f" |"
        )
    return "\n".join(lines) + "\n"


def _build_dart_filings_block(dart_filings: list[dict]) -> str:
    if not dart_filings:
        return ""
    lines = ["## DART 공시 문서 원문 (최근 정기공시)"]
    for index, filing in enumerate(dart_filings, 1):
        lines.append(
            f"\n[공시 {index}: {filing['title']} ({filing['date']})]\n{filing['text']}"
        )
    return "\n".join(lines) + "\n"
