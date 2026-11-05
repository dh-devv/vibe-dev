# 미루기 재판소

> 2026 바이브 코딩 해커톤 팀 BAO의 협업 프로젝트

미루는 이유를 AI 변호인과 검사의 공방으로 드러내고, 판사가 맞춤 처방을 제안하는 웹 앱입니다. 가입한 사용자는 판결을 수용한 뒤 계정에 기록하고, 자신의 기록을 다시 조회해 체크리스트와 타이머로 실행합니다.

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| 서버·언어 | Python 3.12, FastAPI |
| AI | GitHub Copilot SDK, Microsoft Agent Framework |
| 화면 | React, TypeScript, CSS, Vite |
| 앱 형태 | 설치 가능한 반응형 웹 앱(PWA) |
| 스트리밍 | SSE |
| 인증 | Microsoft Entra External ID (OIDC) |
| 데이터베이스 | Azure Database for PostgreSQL (로컬 개발 시 Docker PostgreSQL 가능) |
| 배포 | Azure Container Apps, Azure Database for PostgreSQL, Docker, `azd` |
| 테스트 | pytest, Vitest |

## 프로젝트 구조

```text
vibe-dev/
├── src/app/                 # FastAPI, 입력 검증, 안전·요청 한도
├── src/agents/              # 에이전트, 재판 진행, 판결 검증
│   └── prompts/             # 역할별 프롬프트
├── frontend/                # React·TypeScript PWA
│   └── public/samples.json  # 예시 사건
├── tests/                   # pytest 테스트
├── database/migrations/     # Alembic DB 스키마 마이그레이션
├── infra/                   # Azure 배포 인프라
├── docs/                    # API·저장·개발 문서
├── PRD.md                   # 제품 요구사항과 인수 조건
├── TRD.md                   # 기술 구조와 결정
└── AGENTS.md                # AI 에이전트 작업 규칙
```

`backend/`는 초기 계획에서 남은 폴더이며 현재 구현 위치가 아닙니다. 데이터베이스 마이그레이션은 `database/migrations/`에 둡니다. 실제 구현 경로는 [TRD.md](./TRD.md)를 기준으로 합니다.

## 시작하기

개발 환경과 명령은 [개발 규칙](./docs/DEVELOPMENT_RULES.md)을 참고하세요. 실행 전 PostgreSQL, OIDC, 세션 설정을 `.env`에 구성해야 합니다. OIDC 앱의 redirect URI는 `{PUBLIC_BASE_URL}/auth/callback`으로 등록합니다. `SESSION_SECRET_KEY`는 `python -c "import secrets; print(secrets.token_urlsafe(48))"`로 만들고, 운영 비밀은 비밀 저장소에 둡니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
pip install -r requirements.txt
uvicorn src.app.main:app --reload --no-access-log --port 8000
```

로컬 PostgreSQL은 `docker compose up -d postgres`로 실행하고, 스키마는 `alembic upgrade head`로 적용합니다. `GET /health`에서 서버 응답을 확인할 수 있습니다. `.env`는 로컬 설정 전용이며 커밋하지 마세요([데이터 명세](./docs/DATABASE.md)).

## 문서

- [제품 요구사항 및 인수 조건](./PRD.md)
- [기술 설계 및 배포](./TRD.md)
- [아이디어 배경](./docs/IDEA.md)
- [프런트엔드 개발 안내](./docs/FRONTEND.md)
- [문서 색인과 변경 규칙](./docs/README.md)
