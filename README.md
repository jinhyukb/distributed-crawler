

# 📚 하이브리드 분산형 도서 수집 및 실시간 자동 캐싱 검색 엔진

이 프로젝트는 실무 상용 배포가 가능한 수준의 파이썬 기반 데이터 수집 파이프라인 및 고가용성 REST API 서비스입니다. 단일 크롤러 엔진의 수집 한계를 극복하고, 외부 API의 차단 및 지연 장애를 유연하게 극복하기 위한 **트리플 레이어 백업 우회망(Triple-tier Resilient Architecture)**과 **실시간 자동 데이터 캐싱 시스템**을 탑재했습니다.

---

## 🛠️ 핵심 고도화 아키텍처 (Key Architecture)

이 프로젝트는 단순 크롤링 데이터를 조회하는 단계를 넘어, 로컬 데이터 부재 시 실시간으로 전 세계 오픈 도서망을 탐색해 로컬 데이터베이스를 영구적으로 자동 확장(Auto-Caching)해 나가는 진보된 검색 파이프라인을 가집니다.


               [사용자 검색어 인입 (한글 / 영문 모두 지원)]
                                     │
                                     ▼
                        [실시간 한-영 번역 엔진 가동]
                                     │
                                     ▼
                         [1차 로컬 DB (SQLite) 조회] ───(데이터 존재 시)───> [초고속 API 응답]
                                     │
                                     ▼ (결과 전무: 0건)
                         [2차 Google Books API 호출] ───(성공 시)───> [로컬 DB 자동 캐싱 후 리턴]
                                     │
                                     ▼ (IP 일시 차단: HTTP 429 Too Many Requests)
                         [3차 Open Library API 호출] ───(성공 시)───> [로컬 DB 자동 캐싱 후 리턴]
                                     │
                                     ▼ (비영리 재단망 응답 지연: 15초 초과 타임아웃)
                         [4차 Gutendex 고전도서 API] ───(성공 시)───> [로컬 DB 자동 캐싱 후 리턴]


1. **실시간 한-영 검색어 번역 매칭 (Feature 1)**
   - 사용자가 한글로 검색어(예: `해리포터`, `개츠비`, `기생충`)를 입력하면 시스템이 한글을 자동 감지하여 실시간 번역기(`deep-translator`)를 통해 영어로 교정 후 탐색을 가동합니다.
2. **트리플 공급자 우회 방어선 (Feature 2)**
   - 대량 트래픽 인입에 따른 구글 서버의 호출 제한(`HTTP 429`)을 실시간 감지하면 비영리 도서관망인 `Open Library`로 자동 우회합니다.
   - 오픈 라이브러리 비영리망의 물리적 타임아웃 지연(15초 초과) 발생 시, 구텐베르크 고속 분산망(`Gutendex`)을 즉각 최종 가동하여 어떠한 환경에서도 장애 없이 결과를 도출합니다.
3. **영구적 데이터 자동 캐싱 파이프라인 (Auto-Cache)**
   - 외부 API에서 로드 완료한 유효한 전 세계 실제 서적 정보(표지 이미지, 저자, 원문 정보)는 SQLite 데이터베이스 규격에 맞춰 검증된 후 자동으로 `INSERT OR UPDATE`되어 로컬 데이터베이스를 실시간으로 살찌우게 됩니다.

---

## 📂 디렉터리 구조 및 파일 설명


```
distributed-crawler/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions를 통한 CI/CD 가동 테스트 정의
├── data/
│   └── .gitkeep                # DB가 안전하게 영속화될 로컬 마운트 디렉터리
├── src/
│   ├── __init__.py
│   ├── api.py                  # [최종] 한-영 번역 및 트리플 API 폴백 자동 캐싱 검색 서버
│   ├── database.py             # SQLite DB 벌크 UPSERT 트랜잭션 파이프라인
│   ├── metrics.py              # 모니터링 메트릭 및 Slack 장애 경보 엔진
│   ├── models.py               # Pydantic을 이용한 다중 필드 도서 유효성 스키마
│   ├── queue_manager.py        # Redis 연결 통제 및 중복 차단 관리
│   └── scraper.py              # BeautifulSoup 파서 엔진 및 다중 스레드 워커 구현
├── tests/
│   ├── __init__.py
│   ├── test_pipeline.py        # 유닛 테스트 모음 (확장형 스키마 검증)
│   └── test_search_robustness.py # 100회 무작위 검색 API 스트레스 신뢰성 테스트
├── Dockerfile                  # 가비지 없는 격리된 가상 환경 정의
├── docker-compose.yml          # Redis와 크롤러 앱의 로컬 통합 기동 스펙
├── main.py                     # 수집 작업을 개시하는 실행 시작점
├── main_api.py                 # FastAPI 및 통합 웹서버 구동 시작점
└── requirements.txt            # 가동 필수 의존성 패키지 명세
```

---

## 🛠️ 기동 및 실행 방법

### 방법 1. Docker Compose를 통한 기동 (권장)

```
docker compose up --build
```

---

### 방법 2. 로컬 가상환경에서 수동 기동

1. **가상환경 활성화**
   - **Windows:** `venv\Scripts\activate`
   - **Mac / Linux:** `source venv/bin/activate`
2. **필수 패키지 설치**
   ```
   pip install -r requirements.txt
   ```
3. **로컬 분산 스크래퍼 구동 (기본 수집)**
   ```
   python main.py
   ```
4. **FastAPI 고급 검색 API 서버 가동**
   ```
   python main_api.py
   ```
5. **대화형 API 문서에서 검색 테스트 수행**
   - 웹 브라우저를 열고 `http://127.0.0.1:8000/docs` 에 접속합니다.
   - `/api/v1/books/search` 영역에서 `Try it out` 단추를 누르고, 검색어 입력창에 한글로 `해리포터` 또는 `개츠비`를 입력한 뒤 파란색 `Execute` 단추를 클릭해 실시간 우회 가동 및 적재 결과를 확인합니다.

---

## 🧪 자동화 신뢰성 검증 테스트 실행

구현된 시스템의 안정성을 정밀 검정하기 위해, 가상환경 터미널에서 다음 테스트를 수행합니다.
```
python -m unittest tests/test_pipeline.py tests/test_search_robustness.py
```
- **테스트 결과:** 100가지의 한글/영문/특수문자/오류 쿼리를 주입하여 서버 다운이 발생하지 않음을 전수 검증합니다.
```

---


