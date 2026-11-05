# 미루기 재판소

> 2026 바이브 코딩 해커톤 팀 BAO의 협업 프로젝트

미루는 이유를 AI 변호인과 검사의 공방으로 드러내고, 판사가 맞춤 처방을 제안하는 웹 앱입니다. 사용자는 판결을 수용한 경우에만 브라우저에 기록하고, 체크리스트와 타이머로 실행합니다.

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| 서버·언어 | Python 3.12, FastAPI |
| AI | GitHub Copilot SDK, Microsoft Agent Framework |
| 화면 | 정적 HTML, CSS, JavaScript |
| 스트리밍 | SSE |
| 기록 | 브라우저 `localStorage` (서버 저장소·데이터베이스 없음) |
| 배포 | Azure Container Apps, Docker, `azd` |
| 테스트 | pytest |

## 프로젝트 구조

```text
vibe-dev/
├── src/app/                 # FastAPI, 입력 검증, 안전·요청 한도
├── src/agents/              # 에이전트, 재판 진행, 판결 검증
│   └── prompts/             # 역할별 프롬프트
├── web/                     # 정적 UI와 예시 사건
├── tests/                   # pytest 테스트
├── infra/                   # Azure 배포 인프라
├── docs/                    # API·저장·개발 문서
├── PRD.md                   # 제품 요구사항과 인수 조건
├── TRD.md                   # 기술 구조와 결정
└── AGENTS.md                # AI 에이전트 작업 규칙
```

`backend/`, `frontend/`, `database/`는 이전 기술 계획에서 남은 폴더이며 현재 구현 위치가 아닙니다. 실제 구현 경로는 [TRD.md](./TRD.md)를 기준으로 합니다.

## 시작하기

개발 환경과 명령은 [개발 규칙](./docs/DEVELOPMENT_RULES.md)을 참고하세요. Python 의존성 파일과 앱 코드가 준비된 뒤 아래 명령으로 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8000
```

## 문서

- [제품 요구사항 및 인수 조건](./PRD.md)
- [기술 설계 및 배포](./TRD.md)
- [아이디어 배경](./docs/IDEA.md)
- [문서 색인과 변경 규칙](./docs/README.md)
