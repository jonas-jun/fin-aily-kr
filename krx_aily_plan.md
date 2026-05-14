# KRX-Aily 기획안

## 1. 개요

**KRX-Aily** — 한국 상장 주식을 종목명으로 검색하면 네이버 증권 리서치의 최신 애널리스트 리포트를 수집하고, Gemini AI가 통합 분석 보고서를 생성해주는 웹 서비스.

fin-Aily가 글로벌 주식(Yahoo Finance + 영문 뉴스)을 다루는 것에 대응하여,  
KRX-Aily는 한국 상장 주식(네이버 증권 + 한국어 리서치 리포트)에 집중한다.

| | fin-Aily | KRX-Aily |
|---|---|---|
| 대상 시장 | 글로벌 (US 중심) | 한국 (KOSPI/KOSDAQ) |
| 데이터 소스 | Yahoo Finance | 네이버 증권 리서치 |
| 콘텐츠 | 뉴스 요약 | 애널리스트 리포트 분석 |
| 검색 방식 | 티커 (AAPL, TSLA) | 종목명 (삼성전자, 카카오) |
| AI 모델 | Gemini | Gemini |

---

## 2. 서비스명 / 브랜딩

```
KRX-Aily
```

- **KRX**: 한국거래소(Korea Exchange) 약어. 한국 주식 서비스임을 직관적으로 전달
- **Aily**: fin-Aily 브랜드 공유. "AI + daily" 의미
- 아이콘: 📊 (fin-Aily의 📈와 같은 계열, 리포트·분석 뉘앙스)
- 색상: fin-Aily와 동일한 Blue 계열 (`blue-600`, `slate-*`) — 즉각적으로 같은 패밀리 서비스임을 인지

---

## 3. 기술 스택

### Backend

| 구성요소 | 선택 | 비고 |
|---|---|---|
| 웹 프레임워크 | FastAPI | fin-Aily 백엔드와 동일 |
| 종목 검색 | 네이버 자동완성 API | `ac.stock.naver.com/ac?q={}&target=stock` |
| 스크래핑 | `httpx` + `BeautifulSoup4` | 네이버 증권 리서치 |
| PDF 파싱 | `pdfplumber` | 리포트 본문 텍스트 추출 |
| AI 분석 | `google-genai` (Gemini) | fin-Aily 백엔드와 동일 |
| 환경변수 | `python-dotenv` | |

### Frontend

| 구성요소 | 선택 | 비고 |
|---|---|---|
| 프레임워크 | Next.js 14 (App Router) | fin-Aily 프론트엔드와 동일 |
| 스타일 | Tailwind CSS | fin-Aily와 동일 config |
| 언어 | TypeScript | |
| 폰트 | Inter (Google Fonts) | fin-Aily와 동일 |
| 배포 | Vercel | |

---

## 4. 디렉토리 구조

```
krx-aily/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── model_config.yaml
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── research_router.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── ticker_resolver.py    # 네이버 자동완성 API 기반 종목명 검색
│   │       ├── naver_scraper.py      # 네이버 리서치 리포트 목록 + PDF URL 수집
│   │       ├── pdf_extractor.py      # pdfplumber PDF 텍스트 추출
│   │       └── report_analyzer.py   # Gemini 보고서 생성
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── layout.tsx               # Header + Inter 폰트 + max-w-3xl 레이아웃
│   │   ├── globals.css
│   │   ├── page.tsx                 # 메인: 종목명 검색
│   │   └── report/
│   │       └── [ticker]/
│   │           └── page.tsx         # 분석 결과 페이지
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Header.tsx           # fin-Aily Header와 동일 구조
│   │   │   └── StockSearch.tsx      # 한국 종목명 자동완성 검색
│   │   └── report/
│   │       ├── ReportSkeleton.tsx   # 로딩 스켈레톤
│   │       ├── OpinionBadge.tsx     # 매수/중립/매도 뱃지
│   │       ├── TargetPriceCard.tsx  # 목표주가 카드
│   │       ├── KeyPointsList.tsx    # 핵심 포인트 목록
│   │       ├── RisksList.tsx        # 리스크 목록
│   │       └── SourceList.tsx       # 출처 리포트 목록
│   ├── lib/
│   │   ├── api.ts                   # API 호출 유틸리티
│   │   └── utils.ts                 # 공통 유틸
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── package.json
│   └── .env.local.example
├── docker-compose.yml
└── README.md
```

---

## 5. 화면 구성

### 5-1. 메인 페이지 (`/`)

```
┌─────────────────────────────────────────────────────┐
│ 📊 KRX-Aily                                    홈   │  ← Header (sticky, white/90 backdrop-blur)
├─────────────────────────────────────────────────────┤
│                                                     │
│              📊                                     │
│        KRX-Aily                                     │  ← Hero (pt-24, text-center)
│   한국 상장 종목의 최신 애널리스트 리포트를           │
│   AI가 통합 분석해드립니다.                          │
│                                                     │
│  ┌─────────────────────────────────┐               │
│  │  종목명 검색 (예: 삼성전자, 카카오) │  [검색]      │  ← StockSearch
│  └─────────────────────────────────┘               │
│    ┌──────────────────────────────────┐            │
│    │  삼성전자   005930   코스피       │            │  ← 자동완성 드롭다운
│    │  삼성전자우  005935   코스피       │            │
│    └──────────────────────────────────┘            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**동작 흐름**
1. 종목명 입력 시 300ms 디바운스 → 네이버 자동완성 API 호출
2. 드롭다운: 종목명 + 종목코드 + 시장(코스피/코스닥) 표시
3. 종목 선택 → `/report/{ticker}?name={종목명}&n=5` 로 이동

---

### 5-2. 분석 결과 페이지 (`/report/[ticker]`)

```
┌─────────────────────────────────────────────────────┐
│ 📊 KRX-Aily                                    홈   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ← 뒤로                                             │
│  삼성전자 (005930)                                   │  ← 종목명 + 코드
│  코스피 · 리포트 5개 기반 · 2026-05-15 분석          │  ← 메타 정보
│                                                     │
│  ┌─── 증권사 의견 ──────────────────────────────┐   │
│  │  매수 ●●●●●   4     중립 ●   1   매도   0   │   │  ← OpinionBadge
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌─── 목표주가 ─────────────────────────────────┐   │
│  │     평균  ₩88,000                            │   │  ← TargetPriceCard
│  │   최저 ₩80,000    최고 ₩95,000               │   │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌─── 핵심 포인트 ──────────────────────────────┐   │
│  │  1  HBM4 양산 일정 앞당겨짐 → 점유율 확대     │   │  ← KeyPointsList
│  │  2  DS 부문 흑자 전환 가시화                  │   │
│  │  3  ...                                      │   │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌─── 리스크 ───────────────────────────────────┐   │
│  │  •  PC/스마트폰 수요 둔화 지속 가능성          │   │  ← RisksList
│  │  •  중국 경쟁사 추격                          │   │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌─── 분석 근거 리포트 ─────────────────────────┐   │
│  │  미래에셋증권  중장기 사업 가시성 확보  2026-05-11  PDF↗  │  ← SourceList
│  │  삼성증권     2Q26 실적 Preview          2026-05-09  PDF↗  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**로딩 상태**: 분석에 10–30초 소요 → 스켈레톤 + "AI가 리포트를 분석하고 있습니다..." 문구

---

## 6. API 설계

Backend base URL: `http://localhost:8000/api` (dev) / `https://api.krx-aily.com/api` (prod)

| Method | Endpoint | 설명 |
|---|---|---|
| `GET` | `/api/search?q={종목명}&limit={n}` | 네이버 자동완성 기반 종목 검색 |
| `GET` | `/api/reports/{ticker}?n={n}` | 리포트 목록 + PDF URL 수집 |
| `POST` | `/api/analyze` | 리포트 수집 → PDF 추출 → Gemini 분석 |
| `GET` | `/health` | 헬스체크 |

### Request / Response 예시

**`GET /api/search?q=삼성전자`**
```json
[
  { "ticker": "005930", "name": "삼성전자", "market": "코스피" },
  { "ticker": "005935", "name": "삼성전자우", "market": "코스피" }
]
```

**`POST /api/analyze`**
```json
// Request
{ "ticker": "005930", "name": "삼성전자", "n": 5 }

// Response
{
  "ticker": "005930",
  "name": "삼성전자",
  "report_count": 5,
  "analyzed_at": "2026-05-15",
  "opinions": { "buy": 4, "neutral": 1, "sell": 0 },
  "target_price": { "avg": 88000.0, "min": 80000.0, "max": 95000.0 },
  "key_points": ["HBM4 양산 일정 앞당겨짐", "DS 부문 흑자 전환 가시화"],
  "risks": ["PC/스마트폰 수요 둔화", "중국 경쟁사 추격"],
  "sources": [
    { "firm": "미래에셋증권", "title": "중장기 사업 가시성 확보", "date": "2026-05-11", "pdf_url": "..." }
  ],
  "model_version": "gemini-3.1-flash-lite"
}
```

---

## 7. 컴포넌트 설계

### `StockSearch.tsx`
- 입력: 한국어 종목명
- 자동완성: 종목코드 + 종목명 + 시장 표시
- 선택 시 `/report/{ticker}?name={name}` push

### `OpinionBadge.tsx`
- buy / neutral / sell 카운트를 도트(●) 게이지로 시각화
- 색상: buy=emerald, neutral=slate, sell=red

### `TargetPriceCard.tsx`
- 평균 목표주가 크게, min/max 작게
- null이면 "목표주가 없음" 표시

### `KeyPointsList.tsx`
- 번호 목록 (1, 2, 3…)
- fin-Aily DigestCard의 Market Pulse 스타일 참조

### `RisksList.tsx`
- bullet 목록
- 배경: `bg-red-50 border-red-200` (fin-Aily Negative sentiment 스타일)

### `SourceList.tsx`
- 증권사명 + 리포트 제목 + 날짜 + PDF 링크
- `↗` 외부 링크 아이콘

---

## 8. 환경변수

### Backend (`.env`)
```
GEMINI_API_KEY=
APP_ENV=development
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend (`.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

---

## 9. model_config.yaml

```yaml
features:
  krx_report:
    provider: gemini
    model: gemini-3.1-flash-lite
    max_tokens: 2048

defaults:
  provider: gemini
  model: gemini-3.1-flash-lite
  max_tokens: 2048
```

---

## 10. requirements.txt (Backend)

```
fastapi
uvicorn[standard]
pydantic
pydantic-settings
google-genai
httpx
beautifulsoup4
pdfplumber
python-dotenv
pyyaml
lxml
```

---

## 11. package.json 주요 의존성 (Frontend)

```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "tailwindcss": "^3.0.0",
    "autoprefixer": "^10.0.0",
    "postcss": "^8.0.0",
    "@types/node": "^20.0.0",
    "@types/react": "^18.0.0"
  }
}
```

---

## 12. 개발 단계

### Phase 1 — Backend (기존 krx_reporter 재사용)
- [ ] `backend/` 디렉토리 초기화 (krx_reporter 코드 이식)
- [ ] `config.py` — Supabase 없이 GEMINI_API_KEY만으로 단순화
- [ ] CORS 설정 (Next.js dev 주소 허용)
- [ ] 로컬 테스트 (`uvicorn app.main:app --reload --port 8000`)

### Phase 2 — Frontend
- [ ] Next.js 프로젝트 초기화 (`npx create-next-app@latest`)
- [ ] Tailwind CSS 설정 (fin-Aily config 동일하게)
- [ ] `Header.tsx` — KRX-Aily 로고/네비
- [ ] `StockSearch.tsx` — 종목명 자동완성
- [ ] `app/page.tsx` — 메인 검색 페이지
- [ ] `app/report/[ticker]/page.tsx` — 분석 결과 페이지
- [ ] 분석 결과 컴포넌트 5종 (`OpinionBadge`, `TargetPriceCard`, `KeyPointsList`, `RisksList`, `SourceList`)
- [ ] 로딩 스켈레톤 (`ReportSkeleton`)

### Phase 3 — 배포
- [ ] Backend: Railway / Render / Fly.io
- [ ] Frontend: Vercel
- [ ] 환경변수 설정 + CORS 업데이트
- [ ] 도메인 연결 (선택)

---

## 13. 서버 실행

```bash
# Backend
cd krx-aily/backend
conda activate finaily   # 또는 python venv
uvicorn app.main:app --reload --port 8000

# Frontend
cd krx-aily/frontend
npm install
npm run dev    # http://localhost:3000
```

Swagger UI: `http://localhost:8000/docs`
