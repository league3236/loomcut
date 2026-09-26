# CLAUDE.md

이 파일은 Claude Code가 세션 시작 시 읽는 프로젝트 맥락 문서입니다. 결정 사항이 바뀌면 이 파일도 함께 갱신하세요.

## 프로젝트 개요
loomcut — AI 챗봇형 동영상 생성 서비스. 사용자가 프롬프트(와 선택적으로 이미지)를 입력하면 AI 모델로 영상을 생성한다.
- 현재 모델: Seedance 2.0 (Atlas Cloud API 경유)
- 모델 비종속 설계: 새 모델/업체는 `app/providers/`에 `VideoProvider` 구현을 추가하는 방식으로 확장

## 기술 스택
- Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 (pydantic-settings)
- DB: 로컬 SQLite, 운영 Render Postgres (`database.py`에서 `postgres://` → `postgresql+psycopg://` 변환)
- 인증: 이메일+비밀번호, bcrypt 해싱, JWT(PyJWT). 로그인은 OAuth2 폼(`username`=이메일)
- 결제: 토스페이먼츠 (결제 승인 API `/v1/payments/confirm`, Basic auth = base64("시크릿키:"))
- 배포: Render (`render.yaml` Blueprint: 웹 서비스 + Postgres)
- 스키마는 시작 시 `create_all`로 생성 (Alembic 미도입 — 컬럼 추가 시 기존 DB에는 반영 안 됨에 주의)

## 코드 구조
```
app/
  main.py          # 앱, CORS, 라우터 등록, /health
  config.py        # 모든 설정은 환경변수 (Settings)
  database.py
  models.py        # User, VideoJob, CreditTransaction, PaymentOrder
  schemas.py
  security.py      # 해싱, JWT, get_current_user
  billing.py       # 패키지 정의, 크레딧 차감/지급/환불, 어드민 판별
  providers/       # base.py(인터페이스), atlas.py(Atlas Cloud)
  routers/         # auth.py, videos.py, payments.py
```

## 과금 정책 (확정)
- 회원가입은 누구나 가능, 가입 시 크레딧 0
- 선불 크레딧 방식: 충전한 크레딧에서 영상 생성 시마다 차감 (1크레딧 = 1원)
- 차감액 = 영상 길이(초) × `PRICE_PER_SECOND` (현재 400원, 기본 5초 → 2,000원). 길이는 4~15초
- 생성 요청 시 선차감 → 제공자 요청 실패 또는 생성 실패 시 자동 환불 (중복 환불 방지 로직 있음)
- 잔액 부족 시 HTTP 402
- 충전 패키지: 베이직 10,000원/10,000크레딧, 스탠다드 30,000원/31,500, 프로 50,000원/55,000
- 어드민(`ADMIN_EMAILS`에 등록된 이메일)은 크레딧 차감 없이 무료 생성
- 참고: 현재 가격은 원가 대비 마진이 매우 낮음(큰 패키지는 적자 가능). 가격 조정은 소유자 결정 사항이므로 임의로 바꾸지 말 것

## 결제 흐름
1. `POST /payments/orders` (package_id) → 서버가 order_id와 금액 저장
2. 프론트엔드에서 토스 결제창/결제위젯 호출 (클라이언트 키)
3. 성공 리다이렉트의 paymentKey/orderId/amount → `POST /payments/confirm`
4. 서버가 저장된 주문 금액과 대조 후 토스 승인 API 호출 → 크레딧 지급 (pending→paid 조건부 업데이트로 중복 지급 방지)
- 카카오페이는 토스페이먼츠 간편결제로 지원 (서버 변경 불필요, 프론트 결제위젯에서 노출)
- 현재 테스트 키 단계. 라이브 전환은 키 교체만으로 가능하도록 유지

## 보안 원칙 (중요)
- 퍼블릭 레포다. API 키, 시크릿, 토큰, 개인 이메일을 코드·문서·커밋에 절대 넣지 말 것
- 모든 비밀값은 환경변수로만 읽는다. `.env`는 gitignore 대상, 예시는 `.env.example`에 키 이름만
- `render.yaml`의 비밀값은 `sync: false` (값은 Render에서 설정), `JWT_SECRET`은 `generateValue`
- 결제 금액은 항상 서버에 저장된 값을 기준으로 검증

## 환경변수
`DATABASE_URL`, `JWT_SECRET`, `ADMIN_EMAILS`, `PRICE_PER_SECOND`, `DEFAULT_DURATION`, `TOSS_CLIENT_KEY`, `TOSS_SECRET_KEY`, `ATLAS_API_KEY`, `ATLAS_BASE_URL`, `DEFAULT_T2V_MODEL`, `DEFAULT_I2V_MODEL`, `CORS_ORIGINS` (전체 목록과 기본값은 `.env.example`, `app/config.py` 참고)

## 작업 방식
- 변경 사항은 main 브랜치에 바로 커밋 (별도 PR 불필요)
- 커밋 메시지는 한국어, `feat:` / `fix:` / `docs:` 등 접두어 사용

## 현재 상태
- 백엔드 API 구현 완료 (인증, 영상 생성/조회, 크레딧 결제)
- 아직 미배포. Render 배포 대기 중 (필요한 값: Atlas API 키, 토스 테스트 클라이언트/시크릿 키, 어드민 이메일)
- Atlas Cloud 상태 조회 응답 형식은 문서 예시 기준으로 구현 — 실제 키로 호출해 필드 검증 필요 (`app/providers/atlas.py`)

## 다음 할 일
1. Render 배포 및 실제 API 동작 검증 (Atlas 응답 형식, 토스 테스트 결제)
2. 챗봇형 프론트엔드 (토스 결제위젯 포함, 카카오페이 노출)
3. 이미지 업로드 (현재는 image_url만 지원 — 파일 저장소 연동 필요)
4. Alembic 마이그레이션 도입
