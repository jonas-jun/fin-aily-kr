import hashlib

import pytest

from app.services.report_analyzer import (
    _build_dart_block,
    _build_dart_only_prompt,
    _build_full_report_prompt,
    _build_is_table,
    _fmt,
    _fmt_eok,
    _inject_is_table,
    _parse_json_response,
)


def test_number_formatters_preserve_current_output():
    assert _fmt(None) == "N/A"
    assert _fmt(1234, "원") == "1,234원"
    assert _fmt(-3.25) == "-3.2%"
    assert _fmt_eok(150_000_000) == "2억"


def test_is_table_and_dart_block_golden_output():
    data = [{
        "period": "2025 1Q",
        "revenue": 10_000_000_000,
        "operating_income": 1_000_000_000,
        "net_income": 500_000_000,
        "cfo": 800_000_000,
        "capex": -200_000_000,
    }]

    table = _build_is_table(data)
    dart_block = _build_dart_block(data)

    assert table == "\n".join([
        "*연결재무제표 기준*",
        "",
        "| 분기 | 매출액(억) | 영업이익(억) | OPM | 순이익(억) | NPM |",
        "|------|----------:|------------:|----:|----------:|----:|",
        "| 2025 1Q | 100억 | 10억 | +10.0% | 5억 | +5.0% |",
    ])
    assert "| 2025 1Q | 10,000,000,000원 | N/A | N/A | 1,000,000,000원" in dart_block
    assert "| 2025 1Q | 800,000,000원 | 200,000,000원 | 600,000,000원" in dart_block


def test_inject_is_table_places_table_after_section_two_header():
    report = "## 1. 요약\n내용\n\n## 2. 사업 및 재무 성과 분석\n분석 본문"

    result = _inject_is_table(report, "TABLE")

    assert result == "## 1. 요약\n내용\n\n## 2. 사업 및 재무 성과 분석\n\nTABLE\n\n분석 본문"
    assert _inject_is_table("헤더 없음", "TABLE") == "헤더 없음"


@pytest.mark.parametrize("raw", [
    '{"value": 1}',
    '```json\n{"value": 1}\n```',
    '```\n{"value": 1}\n```',
])
def test_parse_json_response_accepts_current_fence_formats(raw):
    assert _parse_json_response(raw) == {"value": 1}


def test_prompt_strings_are_character_for_character_golden():
    full = _build_full_report_prompt("테스트기업", "REPORTS", "DART", "FILINGS", True)
    dart_only = _build_dart_only_prompt("테스트기업", "DART", "FILINGS")

    assert len(full) == 2181
    assert hashlib.sha256(full.encode()).hexdigest() == "1e581572dd7eeef55a10d921dce8657e4fe058d518e2445fbc2476f9c92d5775"
    assert len(dart_only) == 1334
    assert hashlib.sha256(dart_only.encode()).hexdigest() == "34eb6f506818393bf7d8ce94f19d96987b582d2cfa0a610d18e1bb4d6a7b4c22"
