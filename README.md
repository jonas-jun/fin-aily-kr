# 📊 KRX-Aily

한국 상장 종목의 최신 애널리스트 리포트를 AI가 통합 분석해주는 웹 서비스.

종목명을 검색하면 네이버 증권 리서치의 최신 리포트를 자동 수집하고, Gemini AI가 투자의견·목표주가·핵심 포인트·리스크를 한 페이지로 정리해드립니다.

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
| AI 분석 | Google Gemini (google-genai) |
| Frontend | Next.js 14 (App Router), TypeScript |
| 스타일 | Tailwind CSS |
| 배포 | Backend: Google Cloud Run · Frontend: Vercel |

---

## 디렉토리 구조

```
krx-aily/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── model_config.yaml
│   │   ├── routers/
│   │   │   └── research_router.py
│   │   └── services/
│   │       ├── ticker_resolver.py   # 네이버 자동완성 API
│   │       ├── naver_scraper.py     # 리포트 목록 + PDF URL 수집
│   │       ├── pdf_extractor.py     # PDF 텍스트 추출
│   │       └── report_analyzer.py  # Gemini 분석
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # 메인 검색 페이지
│   │   └── report/[ticker]/page.tsx # 분석 결과 페이지
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Header.tsx
│   │   │   └── StockSearch.tsx
│   │   └── report/
│   │       ├── OpinionBadge.tsx
│   │       ├── TargetPriceCard.tsx
│   │       ├── KeyPointsList.tsx
│   │       ├── RisksList.tsx
│   │       └── SourceList.tsx
│   └── lib/
│       └── api.ts
└── docker-compose.yml
```

---

## 시작하기

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- [Google Gemini API 키](https://aistudio.google.com/app/apikey)

### Backend 실행

```bash
cd backend

# 환경변수 설정
cp .env.example .env
# .env 파일에서 GEMINI_API_KEY 입력

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`

### Frontend 실행

```bash
cd frontend

# 환경변수 설정
cp .env.local.example .env.local

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

브라우저에서 `http://localhost:3000` 접속

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

### Backend (`.env`)

```
GEMINI_API_KEY=your-gemini-api-key
APP_ENV=development
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend (`.env.local`)

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

---

## 관련 프로젝트

- [fin-Aily](https://github.com/jonas-jun/fin-Aily) — 글로벌 주식 AI 뉴스 분석 (Yahoo Finance + 영문 뉴스)
