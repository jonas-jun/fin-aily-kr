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
- **AI 통합 분석** — Gemini AI가 DART 공시·증권사 리포트를 종합해 아래 10개 섹션으로 보고서 생성
  1. **투자 요약** — 핵심 투자 논지(Thesis)와 리스크 3줄 요약
  2. **재무 성과 분석** — 매출·영업이익·순이익 변동 원인과 트렌드 (분기별 연결재무제표 자동 삽입)
  3. **현금흐름 및 운전자본** — 영업CF·CapEx·FCF·재고·매출채권·순차입금 분석 및 이익 질 평가
  4. **사업부문 및 성장 투자** — 세그먼트 변화, CapEx·R&D 강도, 수주잔고 분석
  5. **공시 변화 분석(Filing Delta)** — 최신 vs 이전 공시 핵심 문구 변화 비교 표
  6. **증권사 뷰 및 컨센서스** — 증권사별 투자의견·목표주가·핵심 가정 분석
  7. **기대치 검증** — DART 실제 실적 vs 증권사 추정치 괴리율 비교 표
  8. **핵심 리스크** — 리스크별 출처·심각도(High/Medium/Low)·투자 영향 정리 표
  9. **다음 분기 체크포인트** — 주요 불확실 항목의 긍정·부정 신호 표
  10. **최종 종합 평가** — 투자 관점(긍정/중립/주의) 명시 및 조건부 판단 기준
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

- [fin-Aily-us](https://github.com/jonas-jun/fin-aily-us) — 글로벌 주식 AI 뉴스 분석 (Yahoo Finance + 영문 뉴스)
