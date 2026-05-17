# 최종 보고서 프롬프트 전환 계획

## 목표

`krx_aily_plan.md`의 기관투자자급 애널리스트 프롬프트로 최종 보고서를 대체한다.

**유지하는 카드**
- 목표주가/현재주가 카드 (`TargetPriceCard`)
- 분기별 주요 재무 카드 (`QuarterlyFinancialsTable`)
- 분석 근거 리포트 카드 (`SourceList`)

**제거하는 카드**
- 핵심 투자 포인트 (`KeyPointsList`)
- 리스크 (`RisksList`)
- 공시 분석 요약 (`FilingsAnalysisCard`)

**추가하는 카드**
- 전문 통합 보고서 (`FullReportCard`) — 마크다운 렌더링

---

## 변경 범위

### 1. `backend/app/services/report_analyzer.py`

#### 현재 구조
- `_build_prompt()` → 단일 Gemini 호출 → JSON 응답  
  (`report_target_prices`, `target_price`, `key_points`, `risks`, `corporate_filings_analysis`)

#### 변경 후 구조 — LLM 호출 2단계로 분리 (asyncio.gather로 병렬 실행)

**Call 1 — 목표주가 추출 (기존 유지, 경량화)**

```
목적: report_target_prices, target_price(avg/min/max) 추출
응답 형식: JSON
프롬프트: 기존 _build_prompt에서 dart_instruction/dart_schema/key_points/risks 제거
```

**Call 2 — 전문 보고서 생성 (신규)**

```
목적: 마크다운 형식의 기관투자자급 통합 보고서 생성
응답 형식: 마크다운 텍스트 (JSON 아님)
프롬프트: krx_aily_plan.md의 프롬프트 그대로 사용
  - {company_name} → f-string으로 실제 기업명 삽입
  - 보고서 블록: 기존 reports_block과 동일
  - DART 블록: 기존 dart_block과 동일 (분기 재무 수치 제공)
```

#### `AnalysisResult` dataclass 변경

```python
# 제거
key_points: list[str]
risks: list[str]
corporate_filings_analysis: dict | None

# 추가
full_report: str | None = None  # 마크다운 전문 보고서
```

#### `analyze_reports()` 변경

```python
# asyncio.gather로 두 LLM 호출 병렬 실행
target_price_result, full_report_text = await asyncio.gather(
    _extract_target_prices(client, model, report_dicts, dart_data),
    _generate_full_report(client, model, name, report_dicts, dart_data),
)
```

---

### 2. `backend/app/routers/research_router.py`

#### `AnalyzeResponse` 변경

```python
# 제거
key_points: list[str]
risks: list[str]
corporate_filings_analysis: CorporateFilingsAnalysis | None

# 추가
full_report: str | None = None
```

#### `CorporateFilingsAnalysis` Pydantic 모델 제거

#### `analyze()` 핸들러에서 응답 구성 변경

```python
return AnalyzeResponse(
    ...
    full_report=result.full_report,
    # key_points, risks, corporate_filings_analysis 제거
)
```

---

### 3. `frontend/lib/api.ts`

```typescript
// AnalyzeResponse에서 제거
key_points: string[];
risks: string[];
corporate_filings_analysis: CorporateFilingsAnalysis | null;

// AnalyzeResponse에 추가
full_report: string | null;

// CorporateFilingsAnalysis 인터페이스 제거
```

---

### 4. `frontend/components/report/FullReportCard.tsx` (신규 파일)

- `react-markdown` + `remark-gfm`으로 마크다운 렌더링
  - `remark-gfm`: GFM 표(Table) 지원 — 보고서 내 재무 표 렌더링에 필수
- `@tailwindcss/typography` prose 클래스로 스타일링
- `full_report`가 null이면 null 반환

```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function FullReportCard({ report }: { report: string | null }) {
  if (!report) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <div className="prose prose-slate prose-sm max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
      </div>
    </div>
  );
}
```

#### 패키지 추가 필요

```bash
npm install react-markdown remark-gfm
npm install -D @tailwindcss/typography
```

`tailwind.config.js`에 `require("@tailwindcss/typography")` 플러그인 추가

---

### 5. `frontend/app/report/[ticker]/page.tsx`

```tsx
// 제거 imports
import { FilingsAnalysisCard } from "@/components/report/FilingsAnalysisCard";
import { KeyPointsList } from "@/components/report/KeyPointsList";
import { RisksList } from "@/components/report/RisksList";

// 추가 import
import { FullReportCard } from "@/components/report/FullReportCard";

// JSX — 카드 순서
<TargetPriceCard targetPrice={data.target_price} />
<QuarterlyFinancialsTable financials={data.quarterly_financials} />
<FullReportCard report={data.full_report} />
<SourceList sources={data.sources} />   {/* 분석 근거 리포트 유지 */}
```

---

## 삭제 예정 파일

- `frontend/components/report/FilingsAnalysisCard.tsx`
- `frontend/components/report/KeyPointsList.tsx`
- `frontend/components/report/RisksList.tsx`

---

## 작업 순서

1. `report_analyzer.py` — Call 1/2 분리, `AnalysisResult` 수정
2. `research_router.py` — 응답 모델 수정
3. `frontend/lib/api.ts` — 타입 수정
4. 패키지 설치 (`react-markdown`, `remark-gfm`, `@tailwindcss/typography`)
5. `tailwind.config.js` — typography 플러그인 추가
6. `FullReportCard.tsx` 신규 생성
7. `page.tsx` — 컴포넌트 교체
8. 불필요 컴포넌트 파일 삭제
9. 로컬 테스트 (백엔드 + 프론트엔드 동시)

---

## 유의사항

- Call 1과 Call 2는 서로 다른 응답 형식(JSON vs 마크다운)이므로 `_parse_response()`를 Call 1에만 사용한다.
- DART 분기 재무 데이터는 LLM에게 텍스트로 제공하지만, `QuarterlyFinancialsTable`은 DART 원본 데이터를 직접 사용하므로 변경 없다.
- 목표주가 추출(Call 1)과 전문 보고서 생성(Call 2)을 병렬로 실행해 레이턴시를 최소화한다.
- 보고서 생성 모델은 기존 `feat.model` (Gemini) 그대로 사용한다.
