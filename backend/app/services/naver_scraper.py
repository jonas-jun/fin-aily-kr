import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from app.models.schemas import ReportMeta
from app.services.http_client import NAVER_HEADERS, client_scope

logger = logging.getLogger(__name__)

# 레거시 finance.naver.com/research/*.naver 페이지는 stock.naver.com SPA로 이관되어
# 302만 돌려주므로(2026-09 확인), 종목별 리포트는 모바일 JSON API로 조회한다.
_LIST_URL = "https://m.stock.naver.com/api/research/stock/{ticker}"
_DETAIL_URL = "https://m.stock.naver.com/api/research/company/{nid}"
_WEB_DETAIL_URL = "https://stock.naver.com/research/company/{nid}"
_REQUEST_TIMEOUT = 15
# 상류 API에 그대로 넘어가는 값이므로 호출부 검증과 무관하게 여기서도 상한을 둔다.
_MAX_PAGE_SIZE = 20
_KST = ZoneInfo("Asia/Seoul")


class ReportFetchError(Exception):
    """리포트 수집 자체가 실패한 경우. '최근 리포트가 없음'과 반드시 구분한다."""


async def fetch_report_list(
    ticker: str,
    n: int = 5,
    days_limit: int = 90,
    client: httpx.AsyncClient | None = None,
) -> list[ReportMeta]:
    """
    네이버 증권 리서치 API에서 특정 종목의 최신 리포트 목록을 수집한다.

    수집에 실패하면 ReportFetchError를 던진다. 빈 리스트는 "days_limit 이내에
    발행된 리포트가 실제로 없다"는 의미로만 쓰인다 — 수집 실패를 빈 리스트로
    뭉개면 호출부가 DART 폴백으로 조용히 넘어가버린다. 응답이 왔는데 단 하나도
    해석하지 못한 경우도 0건이 아니라 수집 실패로 취급한다.
    """
    url = _LIST_URL.format(ticker=ticker)
    # pageSize에 n을 그대로 넘겨 1페이지로 끝낸다 (레거시의 3페이지 순회가 불필요해졌다).
    params = {"pageSize": min(n, _MAX_PAGE_SIZE), "page": 1}

    async with client_scope(client) as http:
        try:
            resp = await http.get(
                url, params=params, headers=NAVER_HEADERS, timeout=_REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            raise ReportFetchError(f"리포트 목록 조회 실패 (ticker={ticker}): {e}") from e

    if not isinstance(payload, list):
        raise ReportFetchError(
            f"리포트 목록 응답 형식이 예상과 다름 (ticker={ticker}): {type(payload).__name__}"
        )

    cutoff = datetime.now(_KST).date() - timedelta(days=days_limit)
    reports: list[ReportMeta] = []
    skipped = 0
    for item in payload:
        parsed = _parse_item(item)
        if parsed is None:
            skipped += 1
            logger.warning(
                "리포트 항목 파싱 실패 — 응답 스키마 변경 의심 (ticker=%s, item=%s)",
                ticker,
                sorted(item) if isinstance(item, dict) else type(item).__name__,
            )
            continue
        report, report_date = parsed

        # 응답은 발행일 역순이지만 그 전제에 기대지 않는다 (정렬이 바뀌면 조용히 누락된다).
        # pageSize로 이미 n건 이내라 전체를 훑어도 비용이 없다.
        if report_date < cutoff:
            continue

        reports.append(report)
        if len(reports) >= n:
            break

    if payload and not reports and skipped == len(payload):
        raise ReportFetchError(
            f"응답 {len(payload)}건을 모두 파싱하지 못함 — 스키마 변경 의심 (ticker={ticker})"
        )

    return reports


async def fetch_pdf_url(nid: str, client: httpx.AsyncClient | None = None) -> str:
    """
    리포트 상세 API에서 첨부 파일 URL(현재는 PDF만 관측됨)을 추출한다.

    실패해도 예외를 올리지 않는다 — 본문이 없으면 제목·증권사·날짜만으로 프롬프트가
    구성되고, 분석 쪽(_has_usable_broker_texts)이 증권사 뷰·기대치 검증 섹션을
    "데이터 없음"으로 낮춰 처리한다. 리포트 1건이 통째로 빠지는 것보다 본문 없이
    가는 쪽이 낫다는 판단이다. 전건 실패는 fetch_reports_with_pdf가 집계해 남긴다.
    """
    url = _DETAIL_URL.format(nid=nid)

    async with client_scope(client) as http:
        try:
            resp = await http.get(url, headers=NAVER_HEADERS, timeout=_REQUEST_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("리포트 상세 조회 실패 (nid=%s): %s", nid, e)
            return ""

    if not isinstance(payload, dict):
        logger.warning(
            "리포트 상세 응답 형식이 예상과 다름 (nid=%s): %s", nid, type(payload).__name__
        )
        return ""

    content = payload.get("researchContent")
    if not isinstance(content, dict):
        logger.warning("researchContent 누락 (nid=%s, keys=%s)", nid, sorted(payload))
        return ""

    attach_url = content.get("attachUrl") or ""
    if not attach_url:
        logger.info("PDF 첨부 없음 — 메타데이터만으로 분석 (nid=%s)", nid)
    return attach_url


async def fetch_reports_with_pdf(
    ticker: str,
    n: int = 5,
    days_limit: int = 90,
    client: httpx.AsyncClient | None = None,
) -> list[ReportMeta]:
    """리포트 목록 수집 후 각 리포트의 PDF URL까지 채워서 반환한다."""
    async with client_scope(client) as http:
        reports = await fetch_report_list(ticker, n, days_limit, client=http)
        for report in reports:
            report.pdf_url = await fetch_pdf_url(report.nid, client=http)

    missing = [report.nid for report in reports if not report.pdf_url]
    if reports and len(missing) == len(reports):
        # 전건 실패는 개별 리포트의 사정이 아니라 상세 API 스키마 변경 신호다.
        logger.error(
            "리포트 %d건 전부 PDF URL 없음 — 상세 API 스키마 변경 의심 (ticker=%s, nids=%s)",
            len(reports),
            ticker,
            missing,
        )

    return reports


def _parse_item(item: dict) -> tuple[ReportMeta, date] | None:
    """
    리서치 API 응답 항목을 (메타데이터, 발행일)로 변환한다.

    필수 필드가 없거나 발행일을 읽을 수 없으면 None을 반환한다 — 나이를 모르는
    항목은 days_limit 판정이 불가능하므로 "최근 리포트"로 통과시키지 않는다.
    호출부는 전 항목이 None이면 스키마 변경으로 보고 수집 실패를 올린다.
    """
    if not isinstance(item, dict):
        return None

    research_id = item.get("researchId")
    title = item.get("title")
    if research_id is None or not title:
        return None

    write_date = str(item.get("writeDate") or "")
    try:
        report_date = date.fromisoformat(write_date)
    except ValueError:
        logger.warning(
            "writeDate 파싱 실패 (researchId=%s, writeDate=%r)", research_id, write_date
        )
        return None

    nid = str(research_id)
    return (
        ReportMeta(
            nid=nid,
            title=title,
            firm=item.get("brokerName") or "",
            # date.fromisoformat은 "20260922" 같은 축약 형식도 받으므로 정규화해서 담는다
            # (그대로 두면 응답·프롬프트·UI에 원문이 그대로 노출된다).
            date=report_date.isoformat(),
            detail_url=_WEB_DETAIL_URL.format(nid=nid),
        ),
        report_date,
    )
