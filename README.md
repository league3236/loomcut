# loomcut
AI 챗봇형 동영상 생성 서비스 — 프롬프트와 이미지를 입력하면 AI 모델(Seedance 2.0 등)로 영상을 생성해주는 서비스. FastAPI 백엔드, 회원가입/로그인, 크레딧 선불 결제 포함

## 구조
```
app/
  main.py            # FastAPI 앱, CORS, /health
  config.py          # 환경변수 설정
  database.py        # SQLAlchemy (로컬 SQLite / Render Postgres)
  models.py          # User, VideoJob, CreditTransaction, PaymentOrder
  schemas.py         # 요청/응답 스키마
  security.py        # bcrypt 비밀번호, JWT 인증
  billing.py         # 충전 패키지, 크레딧 차감/환불, 어드민 판별
  providers/         # 영상 생성 제공자 (모델 비종속 인터페이스)
    base.py
    atlas.py         # Atlas Cloud (Seedance 2.0)
  routers/
    auth.py          # /auth/*
    videos.py        # /videos/*
    payments.py      # /payments/* (토스페이먼츠)
render.yaml          # Render Blueprint (웹 서비스 + Postgres)
```

## 과금 방식
- 선불 크레딧: 충전한 크레딧에서 영상 생성마다 차감 (1크레딧 = 1원)
- 차감액 = 영상 길이(초) × `PRICE_PER_SECOND` (기본 400원) → 기본 5초 영상 2,000원
- 생성 실패 시 자동 환불
- `ADMIN_EMAILS`에 등록된 계정은 차감 없이 무료

| 패키지 | 결제 금액 | 지급 크레딧 | 5초 영상 |
|---|---|---|---|
| 베이직 | 10,000원 | 10,000 | 5편 |
| 스탠다드 | 30,000원 | 31,500 (+5%) | 15편 |
| 프로 | 50,000원 | 55,000 (+10%) | 27편 |

## API
| Method | Path | 설명 |
|---|---|---|
| POST | /auth/signup | 회원가입 (email, password) |
| POST | /auth/login | 로그인 (form: username=email, password) → JWT |
| GET | /auth/me | 내 정보 (크레딧 잔액, 어드민 여부) |
| POST | /videos | 영상 생성 (prompt, image_url?, model?, duration? 4~15초). 잔액 부족 시 402 |
| GET | /videos | 내 영상 작업 목록 |
| GET | /videos/{id} | 상태 조회 (진행 중이면 제공자에 최신 상태 확인) |
| GET | /payments/config | 토스 클라이언트 키, 가격, 패키지 목록 |
| POST | /payments/orders | 충전 주문 생성 (package_id) |
| POST | /payments/confirm | 결제 승인 (payment_key, order_id, amount) → 크레딧 지급 |
| GET | /payments/transactions | 크레딧 충전/사용/환불 내역 |
| GET | /health | 헬스체크 |

### 결제 흐름 (토스페이먼츠)
1. `POST /payments/orders`로 주문 생성 → `order_id`, `amount` 받음
2. 프론트엔드에서 토스 결제창 호출 (클라이언트 키 사용)
3. 결제 성공 리다이렉트로 받은 `paymentKey`, `orderId`, `amount`를 `POST /payments/confirm`으로 전달
4. 서버가 금액 검증 후 토스 승인 API 호출 → 크레딧 지급

## 로컬 실행
```bash
pip install -r requirements.txt
cp .env.example .env   # 키 입력
uvicorn app.main:app --reload
```
`http://localhost:8000/docs`에서 Swagger UI로 테스트할 수 있습니다.

## 다음 단계
- 챗봇형 프론트엔드 (토스 결제창 포함)
- 이미지 업로드(파일 저장소 연동)
- Alembic 마이그레이션
