import json
import logging

from google import genai

from app.services.analysis.formatting import (
    _build_dart_block,
    _build_dart_filings_block,
    _build_is_table,
    _build_reports_block,
    _has_usable_broker_texts,
    _inject_is_table,
)
from app.services.analysis.prompts import (
    _build_dart_only_prompt,
    _build_full_report_prompt,
    _build_target_price_prompt,
)

logger = logging.getLogger(__name__)

EMPTY_TARGET_PRICES = {
    "report_target_prices": [],
    "target_price": {"avg": None, "min": None, "max": None},
}


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
        return EMPTY_TARGET_PRICES
    try:
        return _parse_json_response(response.text)
    except Exception:
        logger.warning("목표주가 JSON 파싱 실패 — 기본값 반환")
        return EMPTY_TARGET_PRICES


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
    dart_filings_block = _build_dart_filings_block(dart_filings or [])

    if dart_only:
        prompt = _build_dart_only_prompt(name, dart_block, dart_filings_block)
    else:
        reports_block = _build_reports_block(reports)
        prompt = _build_full_report_prompt(
            name,
            reports_block,
            dart_block,
            dart_filings_block,
            _has_usable_broker_texts(reports),
        )

    response = await client.aio.models.generate_content(model=model, contents=prompt)
    text = response.text or None
    if text and dart_data:
        text = _inject_is_table(text, _build_is_table(dart_data))
    return text
