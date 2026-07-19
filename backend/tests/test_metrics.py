from app.services.metrics import enrich_quarters


def test_enrich_quarters_calculates_margins_cash_flow_and_growth():
    quarters = [
        {
            "period": "2024 1Q",
            "revenue": 100,
            "gross_profit": 40,
            "operating_income": 20,
            "net_income": 10,
            "cfo": 30,
            "capex": -8,
            "short_term_debt": 20,
            "long_term_debt": 30,
            "cash": 15,
        },
        {"period": "2024 2Q", "revenue": 120, "operating_income": 18},
        {"period": "2024 3Q", "revenue": 90, "operating_income": -5},
        {"period": "2024 4Q", "revenue": 110, "operating_income": 11},
        {"period": "2025 1Q", "revenue": 150, "operating_income": 30},
    ]

    enriched = enrich_quarters(quarters)

    assert enriched[0]["gpm"] == 40.0
    assert enriched[0]["opm"] == 20.0
    assert enriched[0]["npm"] == 10.0
    assert enriched[0]["fcf"] == 22
    assert enriched[0]["net_debt"] == 35
    assert enriched[1]["revenue_qoq"] == 20.0
    assert enriched[4]["revenue_yoy"] == 50.0
    assert enriched[4]["oi_yoy"] == 50.0
    assert quarters[0].get("gpm") is None


def test_enrich_quarters_handles_zero_and_missing_values():
    enriched = enrich_quarters([
        {"period": "2025 1Q", "revenue": 0, "cfo": None, "cash": None},
        {"period": "2025 2Q", "revenue": 10, "cfo": 5, "capex": None},
    ])

    assert enriched[0]["opm"] is None
    assert enriched[0]["fcf"] is None
    assert enriched[0]["net_debt"] is None
    assert enriched[1]["revenue_qoq"] is None
    assert enriched[1]["fcf"] == 5
