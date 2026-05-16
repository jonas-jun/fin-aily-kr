# [구현 계획] fin-Aily-kr 기능 개선 — krx_aily_plan.md 기반

> 작성 기준일: 2026-05-17  
> 참고 문서: `krx_aily_plan.md`

---

## 현황 파악 (구현 전 코드 상태)

| 구분 | 현재 상태 | 필요 작업 |
|---|---|---|
| `dart_service.py` | 매출액·영업이익만 추출, 당기순이익 미수집 | `net_income` 필드 추가 |
| `research_router.py` | `Opinions` 모델 존재, `SourceItem`에 개별 목표가 없음, 분기 재무 응답 없음 | Opinions 제거, `target_price` 추가, `QuarterlyFinancialItem` 추가 |
| `report_analyzer.py` | Gemini 프롬프트에 opinions 포함, 소스별 목표가 미반환 | 프롬프트 개편, `report_target_prices` 파싱 추가 |
| `frontend/lib/api.ts` | `Opinions` 인터페이스 존재, `SourceItem`에 목표가 없음 | 타입 구조 동기화 |
| `frontend/app/report/[ticker]/page.tsx` | `<OpinionBadge>` 렌더링 중 | 호출부 제거 |
| `frontend/components/report/SourceList.tsx` | 소스별 목표가 미표시 | `target_price` 렌더링 추가 |
| `QuarterlyFinancialsTable.tsx` | 미존재 | 신규 생성 |

---

## 구현 순서 (의존성 기준 권장 순서)

```
[1] dart_service.py — net_income 추가
[2] report_analyzer.py — 프롬프트 개편 (opinions 제거 + report_target_prices 추가)
[3] research_router.py — 모델 개편 (Opinions 삭제, SourceItem 확장, QuarterlyFinancialItem 추가)
[4] frontend/lib/api.ts — 타입 동기화
[5] frontend/components — SourceList 수정, QuarterlyFinancialsTable 신규, OpinionBadge 제거
[6] frontend/app/report/[ticker]/page.tsx — 레이아웃 조정
```

---

## [기능 1] 소스별 개별 목표주가 표시

### 백엔드

**`backend/app/services/report_analyzer.py`**

1. `_build_prompt()` 내 응답 JSON 스키마에 `"report_target_prices"` 필드 추가:
   ```json
   "report_target_prices": [85000, null, 95000]
   ```
   - 분석한 리포트 순서대로 배열, 미제시·파악 불가 시 `null`
   - 기존 `"opinions"` 블록은 이 단계에서 함께 제거 ([기능 2] 참조)

2. `_build_prompt()` 지시사항 1번 수정:
   - 기존: "투자의견(매수/중립/매도)과 목표주가를 파악"
   - 변경: "각 리포트의 **목표주가만** 파악. 미제시 시 null"

3. `analyze_reports()` 파싱 로직 수정:
   ```python
   report_target_prices = parsed.get("report_target_prices", [])
   sources = [
       {
           "firm": r.firm,
           "title": r.title,
           "date": r.date,
           "pdf_url": r.pdf_url,
           "target_price": report_target_prices[i] if i < len(report_target_prices) else None,
       }
       for i, r in enumerate(reports)
   ]
   ```

4. `AnalysisResult` 데이터클래스: `sources` 항목에 `target_price` 자동 포함됨 (별도 변경 불필요)

**`backend/app/routers/research_router.py`**

5. `SourceItem` 모델에 필드 추가:
   ```python
   class SourceItem(BaseModel):
       firm: str
       title: str
       date: str
       pdf_url: str
       target_price: int | None = None   # 추가
   ```

### 프론트엔드

**`frontend/lib/api.ts`**

6. `SourceItem` 인터페이스 수정:
   ```ts
   export interface SourceItem {
     firm: string;
     title: string;
     date: string;
     pdf_url: string;
     target_price: number | null;   // 추가
   }
   ```

**`frontend/components/report/SourceList.tsx`**

7. 각 소스 항목 우측에 목표주가 표시:
   - `target_price` 존재 시: `{target_price.toLocaleString("ko-KR")}원` (빨간 계열 텍스트)
   - `null`이면: `not_rated` (텍스트, `text-slate-300` 톤)
   - PDF 링크와 같은 `flex-shrink-0` 영역 내 수직 배치

---

## [기능 2] 매수/매도 의견 집계(OpinionBadge) 제거

### 백엔드

**`backend/app/services/report_analyzer.py`**

1. `_build_prompt()` JSON 스키마에서 `"opinions"` 블록 삭제
2. 지시사항에서 "투자의견(매수/중립/매도) 파악" 문구 삭제
3. `AnalysisResult` 데이터클래스에서 `opinions: dict` 필드 삭제
4. `analyze_reports()` 반환부에서 `opinions=parsed.get("opinions", ...)` 라인 삭제

**`backend/app/routers/research_router.py`**

5. `Opinions` Pydantic 모델 클래스 전체 삭제
6. `AnalyzeResponse`에서 `opinions: Opinions` 필드 삭제
7. `analyze()` 함수 반환부에서 `opinions=Opinions(**result.opinions)` 라인 삭제

### 프론트엔드

**`frontend/lib/api.ts`**

8. `Opinions` 인터페이스 전체 삭제
9. `AnalyzeResponse`에서 `opinions: Opinions;` 필드 삭제

**`frontend/app/report/[ticker]/page.tsx`**

10. `import { OpinionBadge } from "@/components/report/OpinionBadge"` 삭제
11. `<OpinionBadge opinions={data.opinions} />` 렌더링 줄 삭제

**`frontend/components/report/OpinionBadge.tsx`**

12. 파일 삭제 (사용처 제거 후 진행)

---

## [기능 3] 최근 4개 분기 재무 테이블

### 백엔드

**`backend/app/services/dart_service.py`**

1. `_fetch_quarter_financials()` 내 당기순이익 추출 추가:
   ```python
   revenue = operating_income = net_income = None
   for row in data.get("list", []):
       account = row.get("account_nm", "")
       amount_str = row.get("thstrm_amount", "").replace(",", "").replace("-", "")
       try:
           amount = int(amount_str) if amount_str else None
       except ValueError:
           amount = None

       if "매출" in account and revenue is None:
           revenue = amount
       if "영업이익" in account and operating_income is None:
           operating_income = amount
       if "당기순이익" in account and net_income is None:   # 추가
           net_income = amount
   ```

2. 반환 딕셔너리에 `net_income` 추가:
   ```python
   return {
       "period": f"{year} {label}",
       "revenue": revenue,
       "operating_income": operating_income,
       "net_income": net_income,   # 추가
   }
   ```

3. `_build_dart_block()` in `report_analyzer.py` — 당기순이익 표시 추가 (LLM 컨텍스트용):
   ```python
   ni = f"{q['net_income']:,}" if q.get("net_income") is not None else "N/A"
   lines.append(f"- {q['period']}: 매출액 {rev}원, 영업이익 {op}원, 당기순이익 {ni}원")
   ```

**`backend/app/routers/research_router.py`**

4. `QuarterlyFinancialItem` Pydantic 모델 추가 (기존 모델 정의 블록에):
   ```python
   class QuarterlyFinancialItem(BaseModel):
       quarter: str                      # 예: "2025 3Q"
       revenue: int | None
       operating_profit: int | None
       net_income: int | None
   ```

5. `AnalyzeResponse`에 필드 추가:
   ```python
   quarterly_financials: list[QuarterlyFinancialItem] = []
   ```

6. `analyze()` 함수 응답 빌드부에서 `dart_data` → `quarterly_financials` 변환:
   ```python
   quarterly_financials = [
       QuarterlyFinancialItem(
           quarter=q["period"],
           revenue=q.get("revenue"),
           operating_profit=q.get("operating_income"),
           net_income=q.get("net_income"),
       )
       for q in (dart_data or [])
   ]

   return AnalyzeResponse(
       ...
       quarterly_financials=quarterly_financials,
   )
   ```

### 프론트엔드

**`frontend/lib/api.ts`**

7. `QuarterlyFinancialItem` 인터페이스 추가:
   ```ts
   export interface QuarterlyFinancialItem {
     quarter: string;
     revenue: number | null;
     operating_profit: number | null;
     net_income: number | null;
   }
   ```

8. `AnalyzeResponse`에 필드 추가:
   ```ts
   quarterly_financials: QuarterlyFinancialItem[];
   ```

**`frontend/components/report/QuarterlyFinancialsTable.tsx` (신규 생성)**

9. 컴포넌트 스펙:
   - Props: `{ financials: QuarterlyFinancialItem[] }`
   - `financials` 배열이 비어있으면 `null` 반환
   - 테이블 헤더: 분기 | 매출액 | 영업이익 | 당기순이익
   - 금액 포맷: 억 원 단위 변환 (`Math.round(n / 100_000_000)`) + "억원" 표기
   - `null` 값은 `—`으로 표시
   - 디자인: 기존 카드 패턴 (`rounded-xl border border-slate-200 bg-white p-4`) 유지
   - 헤더 라벨: `text-xs font-semibold text-slate-500 uppercase tracking-wide`

**`frontend/app/report/[ticker]/page.tsx`**

10. `QuarterlyFinancialsTable` import 추가
11. `<TargetPriceCard />` 바로 아래에 배치:
    ```tsx
    <TargetPriceCard targetPrice={data.target_price} />
    <QuarterlyFinancialsTable financials={data.quarterly_financials} />
    ```

---

## 파일별 작업 체크리스트

| 파일 | 작업 유형 | 핵심 변경 내용 |
|---|---|---|
| `backend/app/services/dart_service.py` | 수정 | `net_income` 추출 추가 |
| `backend/app/services/report_analyzer.py` | 수정 | Gemini 프롬프트 개편 (opinions 제거, report_target_prices 추가), `_build_dart_block` net_income 추가, `AnalysisResult.opinions` 삭제, sources에 target_price 매핑 |
| `backend/app/routers/research_router.py` | 수정 | `Opinions` 모델 삭제, `SourceItem.target_price` 추가, `QuarterlyFinancialItem` 추가, `AnalyzeResponse` 개편 |
| `frontend/lib/api.ts` | 수정 | `Opinions` 삭제, `SourceItem.target_price` 추가, `QuarterlyFinancialItem` 추가 |
| `frontend/app/report/[ticker]/page.tsx` | 수정 | `OpinionBadge` 제거, `QuarterlyFinancialsTable` 추가 |
| `frontend/components/report/SourceList.tsx` | 수정 | 소스별 `target_price` 표시 (없으면 `not_rated`) |
| `frontend/components/report/QuarterlyFinancialsTable.tsx` | **신규** | 분기 재무 테이블 컴포넌트 |
| `frontend/components/report/OpinionBadge.tsx` | **삭제** | 사용처 제거 후 파일 삭제 |

---

## 주의 사항

- **DART API 분기 코드**: 현재 `_QUARTER_CODES`에 `"11011" (연간)` 포함됨. 테이블에는 연간 데이터가 분기처럼 보일 수 있으므로 `quarter` 필드 레이블을 그대로 사용하되, 프론트에서 시각적으로 구분이 필요한 경우 "연간" suffix 처리 고려
- **`fs_div=CFS` 우선**: 연결재무제표 없을 시 OFS로 폴백하는 로직은 현재 구현 유지
- **금액 단위**: 백엔드는 원 단위 정수로 반환, 프론트에서 억 원으로 변환 (API 스키마 변경 없음)
- **opinions 제거 시 타입 에러**: `OpinionBadge` 삭제 전 page.tsx에서 먼저 import/사용부를 제거해야 빌드 오류 방지
