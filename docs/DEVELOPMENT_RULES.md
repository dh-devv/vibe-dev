# 개발 규칙

팀원과 AI 코딩 에이전트(GitHub Copilot)가 함께 지키는 규칙이다.
AI에게 작업을 시킬 때는 항상 [AGENTS.md](../AGENTS.md), [PRD.md](../PRD.md), [TRD.md](../TRD.md), [API_SPEC.md](./API_SPEC.md), [DATABASE.md](./DATABASE.md)를 읽게 한다.

## 1. 개발 환경

### 1.1 필요한 도구

| 도구 | 용도 | 상태 |
| --- | --- | --- |
| Python 3.12 | 서버 | 설치됨 (3.12.10) |
| Node.js LTS + npm | React·TypeScript PWA 개발·빌드 | 팀원별 설치 |
| Git | 버전 관리 | 설치됨 |
| VS Code + GitHub Copilot | 개발 (대회 규정상 이 도구만 허용) | 각자 준비 |
| Azure CLI (`az`) | Azure 로그인 | **미설치** (담당: 변동헌) |
| Azure Developer CLI (`azd`) | 배포 | **미설치** (담당: 변동헌) |
| Docker Desktop | 로컬 PostgreSQL 실행·앱 컨테이너 빌드 | **미확인** (담당: 변동헌) |

백엔드 개발에는 Python과 Git, 프런트엔드 개발에는 Node.js와 npm이 필요하다. 전체 로컬 테스트에는 Docker가 필요하다. Azure 도구는 배포 담당만 필요하다. "설치됨" 표시는 변동헌의 PC 기준이며, 다른 팀원은 각자 확인한다.

### 1.2 처음 시작하기

```powershell
git clone https://github.com/dh-devv/vibe-dev.git
cd vibe-dev
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env      # 로컬 DB 연결값과 비밀 설정은 .env에만 둔다
pip install -r requirements.txt  # requirements.txt는 백엔드가 만든다
```

### 1.3 자주 쓰는 명령

아래 명령은 해당 코드가 만들어진 뒤에 동작한다.

| 하는 일 | 명령 |
| --- | --- |
| 서버 실행 | `uvicorn src.app.main:app --reload --port 8000` |
| 프런트엔드 개발 | `cd frontend; npm install; npm run dev` |
| 프런트엔드 검사·빌드 | `cd frontend; npm run typecheck; npm run build` |
| 로컬 DB | [DATABASE.md](./DATABASE.md)의 Docker 명령 |
| 화면 확인 | Vite 주소 또는 배포 미리보기 주소 |
| 헬스 체크 | `curl http://localhost:8000/health` |
| 테스트 | `pytest` |

## 2. 폴더 구조와 담당

```text
vibe-dev/
├── src/
│   ├── app/              FastAPI, 라우트, 입력 검증, 한도, safety.py
│   └── agents/           에이전트 정의, 재판 진행, 판결 검증기
│       └── prompts/      역할별 프롬프트 (변호인, 검사, 판사)
├── frontend/             React·TypeScript PWA (Vite)
│   ├── src/              기능별 화면, API, 타입, 스타일
│   └── public/           manifest, 아이콘, samples.json
├── tests/                pytest
├── infra/                azd 설정과 Bicep
├── database/migrations/  Alembic 마이그레이션
├── docs/                 명세 문서
├── AGENTS.md, PRD.md, TRD.md
├── .env.example, .gitignore
└── azure.yaml, Dockerfile, requirements.txt (구현 시 생성)
```

| 담당 | 폴더·파일 |
| --- | --- |
| 이채혁 (프런트엔드) | `frontend/` |
| 김승운 (백엔드) | `src/app/`, `src/agents/` |
| 최성은 | `src/app/safety.py`, `frontend/public/samples.json`, `tests/`, `database/migrations/`, `docs/DATABASE.md` |
| 변동헌 (인프라) | `infra/`, `Dockerfile`, `azure.yaml`, 통합 테스트, 저장소 관리 |

담당은 기존 README의 역할을 새 구조에 맞춰 제안한 것이다. 바꾸려면 팀이 합의해 이 표를 고친다.
다른 사람의 폴더를 고칠 때는 먼저 담당자에게 알린다.

## 3. 먼저 정해 둔 약속 (바꾸려면 문서 먼저)

| 약속 | 문서 |
| --- | --- |
| API 경로, 요청·응답, 이벤트, 오류 코드 | [API_SPEC.md](./API_SPEC.md) |
| 판결문 JSON 형식과 길이 규칙 | [API_SPEC.md](./API_SPEC.md) 5.5절 |
| 사용자 인증·기록 소유권·DB 스키마 | [DATABASE.md](./DATABASE.md), [API_SPEC.md](./API_SPEC.md) |
| 기능 범위와 인수 조건 | [PRD.md](../PRD.md) |
| 에이전트 역할과 금지 사항 | [TRD.md](../TRD.md) 3절 |

**변경 절차**: ① 문서를 고친다 → ② 팀 채팅에 알린다 → ③ 영향받는 담당자가 확인한다 → ④ 코드를 고친다.
UI와 서버는 이 문서의 규격만 보고 따로 개발한다. 서버가 완성되기 전에는 UI 테스트에서 가짜 SSE 응답을 사용할 수 있다. 가짜 응답은 API_SPEC 5.4절의 이벤트 순서를 따라야 하며, 배포 빌드에 포함하지 않는다.

## 4. 코딩 규칙

### 공통

- 이름은 영어, 주석과 사용자에게 보이는 문구는 한국어로 쓴다.
- 주석은 이유가 분명하지 않은 부분에만 단다.
- 사용하지 않는 코드, 디버그 출력(`print`, `console.log`)을 남기지 않는다.
- 비밀(토큰, 키)을 코드, 로그, 문서, 커밋에 넣지 않는다.

### Python

- 함수의 인자와 반환값에 타입 힌트를 쓴다.
- 네트워크·모델 호출은 `async`로 쓰고 **타임아웃**을 둔다 (PRD 8절, DATABASE.md 환경 변수).
- 사용자 입력 검증은 Pydantic 모델로 한다.
- 예외 메시지와 로그에 사건 내용을 넣지 않는다.
- 모든 기록 쿼리는 인증된 OIDC 사용자의 서버 검증 ID로 범위를 제한한다. 클라이언트가 보낸 사용자 ID를 신뢰하지 않는다.
- DB 연결은 TLS를 사용하고 비밀은 환경 변수/관리형 비밀로 주입한다. SQL은 바인딩 파라미터를 쓴다.
- 스키마 변경은 Alembic 마이그레이션으로 관리하며, 배포 시 정해진 순서로 적용한다.
- 파일 하나는 300줄 안팎으로 유지한다.

### TypeScript / React / CSS

- UI는 React, TypeScript, Vite를 사용하고 PWA manifest·서비스 워커를 설정한다.
- React의 일반 텍스트 렌더링을 사용한다. **`dangerouslySetInnerHTML`을 쓰지 않는다.**
- 인증 토큰은 `localStorage`에 저장하지 않는다. OIDC 공급자의 안전한 세션 흐름을 따른다.
- 스트림은 `fetch`와 `ReadableStream`으로 읽는다 (POST이므로 `EventSource`를 쓸 수 없다).
- 서비스 워커는 앱 셸과 공개 파일만 캐시한다. `/api/**`, `/auth/**`와 사용자 기록은 캐시하지 않는다.
- 모든 입력란에 `<label>`을 달고, 버튼은 키보드로 조작할 수 있게 한다.
- 360px 너비를 기준으로 먼저 만들고 넓은 화면으로 확장한다.
- 글자와 배경의 대비를 4.5:1 이상으로 한다.
- 모든 AI 생성 글 옆에 "AI 생성" 표시를 붙이고, 화면에 면책 문구를 둔다.

## 5. AI(Copilot)에게 일을 시키는 방법

1. 작업 하나를 작게 쪼개서 시킨다. (예: "`/api/trial`의 입력 검증만 만들어 줘")
2. 읽어야 할 문서와 파일을 직접 알려 준다.
3. 하지 말아야 할 일을 함께 말한다. (예: "명세에 없는 필드를 추가하지 마")
4. 결과는 **실행해서 확인**한다. 테스트가 있으면 테스트를 시킨다.
5. 명세와 다르게 만들었으면 코드를 고치게 한다. 문서를 AI가 임의로 바꾸지 못하게 한다.
6. 중요한 코드(보안, 한도, 판결 검증)는 사람이 한 번 더 읽는다.
7. 생성한 코드를 이해하지 못하면 커밋하지 않고 AI에게 설명을 시킨다.

프롬프트 틀

```text
읽을 문서: AGENTS.md, docs/API_SPEC.md 5절
할 일: (한 가지)
만들 파일: (경로)
하지 말 것: 명세에 없는 필드·기능 추가, 로그에 사건 내용 출력
끝났다는 기준: (확인 방법)
```

## 6. Git 규칙

| 항목 | 규칙 |
| --- | --- |
| 기본 브랜치 | `main`. 항상 실행 가능한 상태를 유지한다 |
| 작업 브랜치 | `feat/<담당>-<내용>` (예: `feat/web-trial-view`) |
| 병합 | 작은 단위로 자주 `main`에 병합한다. 충돌이 나면 담당자와 함께 해결한다 |
| 커밋 메시지 | 한국어 한 줄, 변경 이유를 쓴다. 접두어: `feat`, `fix`, `docs`, `test`, `chore` |
| 금지 | `git push --force`, 비밀이 든 커밋, 남의 폴더를 알리지 않고 대량 수정 |
| 제출 | 심사용 커밋 해시는 변동헌이 정하고 팀에 공유한다 |

커밋 전 확인: `.env`가 포함되지 않았는지, 토큰 문자열이 없는지, `pytest`가 통과하는지.

## 7. 보안 체크리스트 (병합 전)

- [ ] 토큰·키가 코드, 로그, 커밋에 없다
- [ ] 사건 내용, 발언, 판결, 인증 정보를 로그에 남기지 않는다
- [ ] 모델 출력과 DB에서 읽은 값을 안전한 React 텍스트 렌더링으로 표시한다
- [ ] 기록 API의 사용자 간 접근 차단 테스트가 있다
- [ ] 사용자 ID는 검증된 인증 정보에서만 가져온다
- [ ] Copilot 에이전트에 `calc_deadline` 외 도구를 승인하지 않는다 (`approve_all` 금지)
- [ ] 사용자 입력은 `<case>` 태그로 감싸고 지시로 취급하지 않는다
- [ ] 모델 호출에 타임아웃이 있다
- [ ] 한도와 입력 길이 검증이 동작한다

## 8. 완료 기준

기능 하나가 끝났다고 말하려면 다음을 모두 만족해야 한다.

1. PRD의 해당 요구사항과 인수 조건을 충족한다.
2. API_SPEC과 DATABASE 명세와 일치한다.
3. 테스트가 있고 통과한다 (화면은 수동 확인).
4. 7절 체크리스트를 통과한다.
5. 배포 URL에서도 동작한다 (배포 담당이 확인).

## 9. 작업 우선순위

PRD 10절의 개발 순서와 우선순위를 따른다. P0을 완료하기 전에는 P1을 시작하지 않는다.
기록 화면을 단순화하더라도 회원 인증, 사용자 간 데이터 격리, 기록 저장·삭제는 생략하지 않는다. **끝까지 동작하는 것이 기능을 늘리는 것보다 우선이다.**

## 10. 문제가 생겼을 때

| 상황 | 할 일 |
| --- | --- |
| Copilot 호출이 실패 | 토큰 권한과 만료를 확인하고 변동헌에게 알린다. 해결이 막히면 TRD 9절의 대안으로 전환한다 |
| 명세가 모호하거나 모순 | 코드를 추측해서 짜지 말고 문서 담당(변동헌)에게 묻는다 |
| 일정이 밀림 | PRD 우선순위(P0, P1)를 기준으로 범위를 줄인다 |
| 토큰이 노출됨 | 즉시 폐기하고 새로 발급한 뒤 변동헌에게 알린다 |

## 11. 변경 기록

| 날짜 | 내용 | 작성자 |
| --- | --- | --- |
| 2026-11-05 | 최초 작성 | |
