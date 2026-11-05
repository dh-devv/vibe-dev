# 프런트엔드 개발 안내

## 1. 결정

이 프로젝트의 클라이언트는 설치할 수 있는 반응형 웹 앱(PWA)으로 만든다.

| 항목 | 선택 |
| --- | --- |
| 언어 | TypeScript |
| UI | React |
| 개발 서버·빌드 | Vite |
| 스타일 | CSS |
| 설치·앱 셸 | Web App Manifest와 서비스 워커 (`vite-plugin-pwa`) |
| 서버 연동 | 같은 출처의 FastAPI REST API와 SSE |

React와 TypeScript는 로그인, 재판 스트림, 판결 수용, 집행 상태, 기록 조회 등 화면 상태와 API 데이터가 많은 UI에 적합하다. Vite는 빠른 개발 서버와 정적 빌드를 제공한다. 네이티브 앱은 이번 범위가 아니다. PWA는 브라우저에서 설치할 수 있지만, 재판과 동기화된 기록은 온라인 연결이 필요하다.

## 2. 프로젝트 구조

```text
frontend/
├── public/
│   ├── manifest.webmanifest
│   ├── icons/
│   └── samples.json
├── src/
│   ├── app/             앱 시작, 라우트, 전역 레이아웃
│   ├── components/     공통 UI
│   ├── features/
│   │   ├── auth/        로그인·로그아웃
│   │   ├── trial/       접수·공방·판결
│   │   └── records/     기록 목록·상세·집행
│   ├── api/             REST 호출과 SSE 파서
│   ├── types/           API 데이터 타입
│   └── styles/          전역 스타일·토큰
├── tests/
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

`frontend/dist/`는 Vite 빌드 산출물이며 저장소에 커밋하지 않는다. FastAPI는 배포 이미지에 포함된 `frontend/dist/`를 `/`에서 제공한다. 예시 사건은 `/samples.json`으로 제공한다.

## 3. 개발 흐름

Node.js LTS와 npm을 준비한 뒤 프런트엔드 폴더에서 실행한다.

```powershell
cd frontend
npm install
npm run dev
```

Vite 개발 서버는 `/api`와 `/auth` 요청을 로컬 FastAPI 서버(`http://localhost:8000`)로 프록시한다. 같은 출처처럼 호출해 인증 쿠키와 SSE를 로컬에서도 확인한다. 배포 전에는 정적 빌드와 타입 검사를 실행한다.

```powershell
npm run typecheck
npm run build
npm run preview
```

프로젝트 설정에서 위 스크립트를 제공한다. 컴포넌트 테스트에는 Vitest와 React Testing Library를 사용한다.

## 4. 화면과 서버 연결

- React Router로 로그인, 새 재판, 기록 목록, 기록 상세 화면을 나눈다.
- API 요청은 `frontend/src/api/`의 공통 함수에서 처리한다. 상태 변경 요청에는 API 명세의 CSRF 방어를 적용한다.
- `/api/me`로 로그인 상태를 확인한다. 로그인·가입은 `/auth/login`, 로그아웃은 `/auth/logout`으로 이동한다.
- 사용자 기록은 PostgreSQL의 서버 데이터다. 클라이언트 메모리 캐시는 화면 표시용이며 영구 저장소로 취급하지 않는다.
- 판결 결과는 사용자가 **수용**을 누를 때만 `POST /api/records`로 저장한다. 기각하면 기록 API를 호출하지 않는다.
- 공방은 `fetch`의 `ReadableStream`으로 SSE 이벤트를 읽는다. 연결을 취소하면 서버의 남은 모델 호출도 중단한다.
- API 데이터의 TypeScript 타입은 FastAPI OpenAPI 스키마에서 생성하거나, 스키마 변경과 함께 갱신한다. 서버의 유효성 검사를 대체하지 않는다.
- 사용자에게 보여 주는 오류는 한국어로 안내한다. 저장 실패를 성공처럼 처리하지 않고 다시 시도할 수 있게 한다.

## 5. 보안·개인정보

- 인증 토큰이나 사용자 재판 기록을 `localStorage`, 서비스 워커 캐시, URL, 콘솔 로그에 저장하지 않는다.
- 세션은 서버가 설정한 `HttpOnly`, `Secure`, 적절한 `SameSite` 쿠키로 사용한다. 상태 변경 요청은 CSRF 방어를 거친다.
- React의 일반 텍스트 렌더링을 사용한다. `dangerouslySetInnerHTML`을 쓰지 않는다.
- 서비스 워커는 앱 셸과 공개 정적 자산만 캐시한다. `/api/**`, `/auth/**`, 사용자별 응답은 캐시하지 않는다.
- 사용자는 재판 입력이 AI 제공자에게 전송되고, 수용하면 사건·마감일·판결·집행 기록이 계정에 저장됨을 접수 전에 확인할 수 있어야 한다.

## 6. PWA·접근성

- 유효한 manifest, 앱 이름·아이콘·테마 색, HTTPS 환경을 제공해 설치 가능하게 한다.
- 오프라인에서는 앱 셸만 열 수 있다. 로그인, 재판 진행, 기록 조회·저장은 온라인 상태를 요구하며, 오프라인 작업을 서버와 자동 병합하지 않는다.
- 360px 화면부터 반응형으로 만든다. 키보드 조작, 명확한 포커스, 입력 라벨, 4.5:1 이상의 글자 대비를 확인한다.
- AI 발언과 판결에는 "AI 생성" 표시와 제품 면책 문구를 노출한다.

## 7. 배포

Docker 다단계 빌드에서 Node.js 이미지로 `npm ci`와 `npm run build`를 실행하고, 산출물만 Python 앱 이미지에 복사한다. 최종 컨테이너는 FastAPI와 정적 UI를 한 출처로 제공한다. Node 개발 도구와 `node_modules`는 최종 런타임 이미지에 넣지 않는다.
