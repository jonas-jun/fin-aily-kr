# fin-Aily-kr

한국 상장 종목의 최신 애널리스트 리포트를 AI가 통합 분석해주는 웹 서비스.

종목명을 검색하면 네이버 증권 리서치에서 최신 리포트를 자동 수집하고, Google Gemini AI가 투자의견·목표주가·핵심 포인트·리스크를 한 페이지로 정리해드립니다.

**🌐 서비스 URL**

| | URL |
|---|---|
| Frontend | https://krx-aily.vercel.app |
| Backend API | https://krx-aily-backend-pqbhq3dqna-du.a.run.app/docs |

---

## 주요 기능

- **종목명 자동완성 검색** — 한국어 종목명 입력 시 네이버 증권 자동완성 API 기반 실시간 검색
- **리포트 자동 수집** — 네이버 증권 리서치에서 최신 애널리스트 리포트 및 PDF 자동 수집
- **AI 통합 분석** — Gemini AI가 여러 증권사 리포트를 종합하여 구조화된 보고서 생성
  - 증권사 의견 집계 (매수 / 중립 / 매도)
  - 평균·최저·최고 목표주가
  - 핵심 투자 포인트
  - 주요 리스크 요인
  - 분석 근거 리포트 출처 목록

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Backend | FastAPI, Python 3.13 |
| 스크래핑 | httpx, BeautifulSoup4 |
| PDF 파싱 | pdfplumber |
| AI 분석 | Google Gemini (`google-genai`) |
| Frontend | Next.js 14 (App Router), TypeScript |
| 스타일 | Tailwind CSS |
| 배포 | Backend: Google Cloud Run · Frontend: Vercel |

---

## 디자인

### 컬러 시스템

| 역할 | 색상 | 값 |
|---|---|---|
| Primary (강조·CTA) | Rose Red | `#EF4444` |
| Brand (헤더·배경) | Navy Blue | `#1E3A5F` |

Tailwind 커스텀 컬러로 등록되어 있어 `text-primary`, `bg-brand` 등으로 바로 사용할 수 있습니다.

### 로고

SVG 컴포넌트(`Logo.tsx`)로 구현되어 있습니다.

- 점 없는 소문자 `ı` + 빨간 삼각형(`▲`) 조합의 "Aily" 워드마크
- 우측 상단 `KR` 배지로 한국 서비스임을 명시
- `size` prop으로 `sm` / `md` / `lg` 세 단계 크기 지원

---

## 디렉토리 구조

```
fin-aily-kr/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI 앱 진입점
│   │   ├── config.py             # 환경변수 설정
│   │   ├── model_config.yaml     # Gemini 모델 파라미터
│   │   ├── routers/
│   │   │   └── research_router.py
│   │   └── services/
│   │       ├── ticker_resolver.py   # 네이버 자동완성 API
│   │       ├── naver_scraper.py     # 리포트 목록 + PDF URL 수집
│   │       ├── pdf_extractor.py     # PDF 텍스트 추출
│   │       └── report_analyzer.py  # Gemini 분석
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                 # 메인 검색 페이지
│   │   └── report/[ticker]/page.tsx # 분석 결과 페이지
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Header.tsx
│   │   │   ├── Logo.tsx
│   │   │   └── StockSearch.tsx
│   │   └── report/
│   │       ├── OpinionBadge.tsx
│   │       ├── TargetPriceCard.tsx
│   │       ├── KeyPointsList.tsx
│   │       ├── RisksList.tsx
│   │       └── SourceList.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   └── utils.ts
│   └── .env.local.example
└── docker-compose.yml
```

---

## 로컬 실행

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- [Google Gemini API 키](https://aistudio.google.com/app/apikey)

### 1. Backend

```bash
cd backend

# 환경변수 설정
cp .env.example .env
# .env 파일에서 GEMINI_API_KEY 값을 입력

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행 (hot-reload)
uvicorn app.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend

# 환경변수 설정
cp .env.local.example .env.local
# 기본값(http://localhost:8000/api)으로 그대로 사용 가능

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

브라우저에서 `http://localhost:3000` 접속

### Docker Compose로 한 번에 실행

```bash
# backend/.env 파일에 GEMINI_API_KEY를 먼저 입력한 후 실행
docker compose up --build
```

| 서비스 | 주소 |
|---|---|
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000/docs` |

---

## API

| Method | Endpoint | 설명 |
|---|---|---|
| `GET` | `/api/search?q={종목명}` | 종목명 자동완성 검색 |
| `GET` | `/api/reports/{ticker}` | 리포트 목록 + PDF URL 수집 |
| `POST` | `/api/analyze` | AI 통합 분석 보고서 생성 |
| `GET` | `/health` | 헬스체크 |

---

## 환경변수

### Backend (`backend/.env`)

```
GEMINI_API_KEY=your-gemini-api-key-here
APP_ENV=development
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend (`frontend/.env.local`)

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

---

## 관련 프로젝트

- [fin-Aily](https://github.com/jonas-jun/fin-Aily) — 글로벌 주식 AI 뉴스 분석 (Yahoo Finance + 영문 뉴스)
