import json
from pathlib import Path

from app.services.dart_service import (
    _compute_actual_quarters,
    _first_amount,
    _parse_account_rows,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_first_amount_skips_excluded_and_invalid_rows():
    rows = [
        {"sj_div": "IS", "account_nm": "매출원가", "thstrm_amount": "900"},
        {"sj_div": "IS", "account_nm": "매출액", "thstrm_amount": "invalid"},
        {"sj_div": "IS", "account_nm": "매출", "thstrm_amount": "1,234"},
    ]

    assert _first_amount(rows, ["IS", "CIS"], ["매출액", "매출"], ["원가"]) == 1234


def test_parse_account_rows_supports_revenue_alias_and_cis():
    rows = json.loads((FIXTURES / "dart_accounts.json").read_text())

    result = _parse_account_rows(rows)

    assert result["revenue"] == 1_000_000
    assert result["operating_income"] == 300_000
    assert result["cfo"] == 400_000
    assert result["cash"] == 500_000


def test_compute_actual_quarters_separates_is_cf_and_bs_rules():
    cumulative = {
        "1Q": {"revenue": 100, "cfo": 10, "cash": 1_000},
        "반기": {"revenue": 200, "cfo": 30, "cash": 2_000},
        "3Q": {"revenue": 300, "cfo": 60, "cash": 3_000},
        "연간": {"revenue": 1_000, "cfo": 100, "cash": 4_000},
    }

    quarters = _compute_actual_quarters(cumulative, 2025)

    assert [q["period"] for q in quarters] == ["2025 1Q", "2025 2Q", "2025 3Q", "2025 4Q"]
    assert [q["revenue"] for q in quarters] == [100, 200, 300, 400]
    assert [q["cfo"] for q in quarters] == [10, 20, 30, 40]
    assert [q["cash"] for q in quarters] == [1_000, 2_000, 3_000, 4_000]


def test_compute_actual_quarters_preserves_none_for_missing_cf_base():
    quarters = _compute_actual_quarters(
        {"반기": {"revenue": 200, "cfo": 30}, "연간": {"revenue": 900, "cfo": 100}},
        2025,
    )

    assert quarters[0]["period"] == "2025 2Q"
    assert quarters[0]["cfo"] is None
    assert quarters[1]["period"] == "2025 4Q"
    assert quarters[1]["revenue"] == 900
    assert quarters[1]["cfo"] is None
