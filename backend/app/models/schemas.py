from pydantic import BaseModel, Field


class TickerItem(BaseModel):
    ticker: str
    name: str
    market: str = ""


class ReportMeta(BaseModel):
    nid: str
    title: str
    firm: str
    date: str
    detail_url: str
    pdf_url: str = ""


class ReportItem(ReportMeta):
    pdf_url: str


class ReportInput(ReportMeta):
    text: str = ""


class AnalyzeRequest(BaseModel):
    query: str | None = None
    ticker: str | None = None
    name: str | None = None
    # /reports 엔드포인트의 Query 제약과 맞춘다. n은 상류 API의 pageSize로 넘어가므로
    # 무제약이면 리포트 수백 건 × 상세/PDF 왕복이 그대로 요청된다.
    n: int = Field(default=5, ge=1, le=20)
    days_limit: int = Field(default=90, ge=1, le=365)
    reports: list[ReportItem] | None = None


class TargetPrice(BaseModel):
    avg: float | None
    min: float | None
    max: float | None
    current_price: float | None = None


class SourceItem(BaseModel):
    firm: str
    title: str
    date: str
    pdf_url: str
    target_price: int | None = None


class AnalyzeResponse(BaseModel):
    ticker: str
    name: str
    report_count: int
    analyzed_at: str
    target_price: TargetPrice
    sources: list[SourceItem]
    model_version: str
    full_report: str | None = None
    dart_only: bool = False
