# fin-Aily KR

한국 상장 종목의 최신 애널리스트 리포트를 AI가 한 페이지로 정리해주는 서비스입니다.
종목명을 검색하면 네이버 증권에서 리포트를 자동 수집하고, Gemini AI가 투자의견·목표주가·핵심 포인트·리스크를 통합 분석합니다.

**🌐 서비스 URL**

| | URL |
|---|---|
| Frontend | https://fin-aily-kr.vercel.app |
| Backend API | https://krx-aily-backend-pqbhq3dqna-du.a.run.app/docs |

---

## 주요 기능

- **종목 검색** — 네이버 증권 자동완성 기반 실시간 종목명 검색
- **리포트 자동 수집** — 네이버 증권 리서치에서 최신 리포트 및 PDF 자동 수집 (기본 90일 이내, 최대 5건)
- **AI 통합 분석** — Gemini AI가 여러 증권사 리포트를 읽고 아래 항목을 정리
  - 목표주가 (평균·최저·최고) 및 현재가 대비 괴리율
  - 투자의견 집계 (매수 / 중립 / 매도)
  - 핵심 투자 포인트 및 주요 리스크
  - 근거로 쓰인 리포트 출처 목록
- **DART 폴백** — 최근 리포트가 없는 종목은 금감원 DART 공시 데이터(재무제표·사업보고서)로 대체 분석

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.13 |
| AI 분석 | Google Gemini (`google-genai`) |
| 데이터 수집 | httpx + BeautifulSoup4 (네이버 증권), DART Open API |
| PDF 파싱 | pdfplumber |
| 배포 | Frontend: Vercel · Backend: Google Cloud Run |

---

## 로컬 실행

**사전 요구사항:** Python 3.11+, Node.js 18+, [Gemini API 키](https://aistudio.google.com/app/apikey), DART API 키

### Backend

```bash
cd backend
cp .env.example .env        # GEMINI_API_KEY, DART_API_KEY 입력
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Swagger UI → http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local   # 기본값(http://localhost:8000/api)으로 사용 가능
npm install
npm run dev
# 브라우저 → http://localhost:3000
```

### Docker Compose (한 번에 실행)

```bash
# backend/.env 파일 준비 후 실행
docker compose up --build
```

---

## API

| Method | Endpoint | 설명 |
|---|---|---|
| `GET` | `/api/search?q={종목명}` | 종목명 자동완성 검색 |
| `GET` | `/api/reports/{ticker}` | 리포트 목록 + PDF URL 수집 |
| `POST` | `/api/analyze` | AI 통합 분석 보고서 생성 |
| `GET` | `/health` | 헬스체크 |

---

## 관련 프로젝트

- [fin-Aily](https://github.com/jonas-jun/fin-Aily) — 글로벌 주식 AI 뉴스 분석 (Yahoo Finance + 영문 뉴스)
