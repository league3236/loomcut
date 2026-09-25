# loomcut
AI 챗봇형 동영상 생성 서비스 — 프롬프트와 이미지를 입력하면 AI 모델(Seedance 2.0 등)로 영상을 생성해주는 서비스. FastAPI 백엔드, 회원가입/로그인 포함

## 구조
```
app/
  main.py            # FastAPI 앱, CORS, /health
  config.py          # 환경변수 설정
  database.py        # SQLAlchemy (로컬 SQLite / Render Postgres)
  models.py          # User, VideoJob
  schemas.py         # 요청/응답 스키마
  security.py        # bcrypt 비밀번호, JWT 인증
  providers/         # 영상 생성 제공자 (모델 비종속 인터페이스)
    base.py
    atlas.py         # Atlas Cloud (Seedance 2.0)
  routers/
    auth.py          # /auth/signup, /auth/login, /auth/me
    videos.py        # /videos 생성·목록·상태조회
render.yaml          # Render Blueprint (웹 서비스 + Postgres)
```

## API
| Method | Path | 설명 |
|---|---|---|
| POST | /auth/signup | 회원가입 (email, password) |
| POST | /auth/login | 로그인 (form: username=email, password) → JWT |
| GET | /auth/me | 내 정보 |
| POST | /videos | 영상 생성 요청 (prompt, image_url?, model?, duration?) |
| GET | /videos | 내 영상 작업 목록 |
| GET | /videos/{id} | 상태 조회 (진행 중이면 제공자에 최신 상태 확인) |
| GET | /health | 헬스체크 |

`image_url`이 있으면 image-to-video, 없으면 text-to-video 모델을 기본으로 사용합니다.

## 로컬 실행
```bash
pip install -r requirements.txt
cp .env.example .env   # ATLAS_API_KEY 입력
uvicorn app.main:app --reload
```
`http://localhost:8000/docs`에서 Swagger UI로 테스트할 수 있습니다.

## Render 배포
1. Render 대시보드 → New → Blueprint → 이 레포 선택 (`render.yaml` 사용)
2. `ATLAS_API_KEY` 값 입력
3. 배포 후 `https://<서비스명>.onrender.com/docs` 확인

## 다음 단계
- 이미지 업로드(파일 저장소 연동)
- 챗봇형 프론트엔드
- Alembic 마이그레이션
