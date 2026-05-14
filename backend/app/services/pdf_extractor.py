import io
import logging

import httpx
import pdfplumber

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://finance.naver.com/",
}
MAX_CHARS = 8000  # 리포트 1개당 최대 추출 글자 수


async def extract_text_from_pdf_url(pdf_url: str) -> str:
    """
    PDF URL에서 텍스트를 추출한다.
    실패 시 빈 문자열 반환 (호출부에서 메타데이터 폴백 처리).
    """
    if not pdf_url:
        return ""

    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=30) as client:
            resp = await client.get(pdf_url)
            resp.raise_for_status()
            pdf_bytes = resp.content
    except httpx.HTTPError as e:
        logger.warning("PDF 다운로드 실패 (%s): %s", pdf_url, e)
        return ""

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            full_text = "\n".join(pages_text)
            return full_text[:MAX_CHARS]
    except Exception as e:
        logger.warning("PDF 텍스트 추출 실패 (%s): %s", pdf_url, e)
        return ""
