# API 명세

백엔드(FastAPI)와 웹 UI가 지키는 통신 규칙이다. 구현이 이 문서와 다르면 **문서를 먼저 고치고** 팀에 알린 뒤 코드를 고친다.
요구사항 기준은 [PRD.md](./PRD.md), 구조 기준은 [TRD.md](./TRD.md)다.

## 1. 공통 규칙

| 항목 | 값 |
| --- | --- |
| 기본 주소 | 로컬 `http://localhost:8000`, 배포 `https://<앱>.<환경>.<지역>.azurecontainerapps.io` |
| 인증 | 관리형 OAuth/OIDC 로그인. 서버는 콜백에서 ID 토큰을 검증하고 세션을 만든다. `/api/**` 경로는 인증이 필요하다. `/health`, `/auth/login`, `/auth/callback`은 비인증 경로다 |
| 세션 | `Secure`, `HttpOnly`, 적절한 `SameSite` 속성을 설정한 쿠키를 사용하고 상태 변경 요청에는 CSRF 방어를 적용한다. 토큰은 브라우저 `localStorage`에 저장하지 않는다 |
| 소유권 | 서버가 세션의 검증된 `issuer`·`subject`로 소유자를 결정한다. 사용자 ID를 요청에서 받지 않는다 |
| 형식 | 요청은 `application/json; charset=utf-8`, 응답은 아래 각 절의 형식 |
| 시간 | ISO 8601 (예: `2026-11-05T14:30:00Z`), 마감일은 `YYYY-MM-DD` |
| 문자 수 | 공백 포함, 유니코드 문자 수 기준 (Python `len`, JavaScript `[...str].length`) |
| CORS | 사용하지 않는다. UI와 API가 같은 주소에서 제공된다 |

## 2. 엔드포인트 목록

| 메서드 | 경로 | 설명 | 우선순위 |
| --- | --- | --- | --- |
| GET | `/health` | 헬스 체크 (비인증) | P0 |
| GET | `/auth/login` | OIDC 로그인/가입 시작 | P0 |
| GET | `/auth/callback` | OIDC 인증 콜백 | P0 |
| POST | `/auth/logout` | 로그아웃 | P0 |
| GET | `/api/me` | 현재 사용자 요약 | P0 |
| POST | `/api/trial` | 재판 진행 (SSE 스트림) | P0 |
| POST | `/api/records` | 수용한 재판 기록 생성 | P0 |
| GET | `/api/records` | 현재 사용자의 기록 목록 조회 | P0 |
| GET | `/api/records/{record_id}` | 현재 사용자의 기록 상세 조회 | P0 |
| PATCH | `/api/records/{record_id}` | 집행 체크 상태 변경 | P0 |
| DELETE | `/api/records/{record_id}` | 현재 사용자의 기록 삭제 | P0 |
| DELETE | `/api/records` | 현재 사용자의 기록 전체 삭제 | P0 |
| DELETE | `/api/account` | 앱 계정과 해당 기록 삭제 | P0 |
| POST | `/api/appeal` | 항소 (SSE 스트림) | P1 (구현 전에는 404) |

PWA 정적 UI는 `/`에서 제공한다 (`frontend/dist/index.html`). API·인증 경로가 아닌 클라이언트 화면 경로는 SPA 진입점으로 돌려보낸다. 예시 사건은 `/samples.json`으로 제공하며 소스 파일은 `frontend/public/samples.json`이다. 가입·로그인은 Microsoft Entra External ID가 처리한다. 인증 제공자에서 자체 가입을 허용한다.

모든 상태 변경 요청에는 CSRF 방어를 적용한다. 인증 누락·만료는 `401`, 잘못된 CSRF 검증은 `403`으로 응답한다. 다른 사용자의 기록 ID를 지정한 경우 존재 여부를 감추기 위해 `404`를 반환한다.

## 3. GET /health

응답 `200`

```json
{ "status": "ok" }
```

모델을 호출하지 않는다. 항상 빠르게 응답해야 한다.

## 4. GET /api/me

현재 인증된 사용자 요약을 반환한다. `id`는 앱 내부 식별자이며 클라이언트가 권한 확인에 사용하지 않는다.

```json
{ "id": "uuid", "authenticated": true }
```

세션이 없거나 유효하지 않으면 `401`이다.

## 5. POST /api/trial

### 5.1 요청

```json
{
  "case": "보고서를 3일째 못 쓰고 있다. 금요일까지다.",
  "deadline": "2026-11-07"
}
```

| 필드 | 형식 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `case` | string | 예 | 앞뒤 공백을 제거한 뒤 5~300자 |
| `deadline` | string \| null | 아니오 | `YYYY-MM-DD`. 오늘(UTC 기준 날짜)부터 365일 이내. 생략하거나 `null`이면 마감 없음 |

그 밖의 필드는 무시한다.

### 5.2 사전 검사와 오류 응답

유효한 로그인 세션을 먼저 확인한 뒤, 스트림을 시작하기 **전에** 아래 순서로 검사한다. 실패하면 일반 JSON으로 응답하고 스트림을 열지 않는다.

| 순서 | 검사 | HTTP | `code` |
| --- | --- | --- | --- |
| 1 | JSON 형식, 필드 규칙 | 422 | `INVALID_INPUT` |
| 2 | 위기 신호 (PRD 6절) | 422 | `CRISIS_SIGNAL` |
| 3 | IP별 분당·일일 한도 | 429 | `RATE_LIMITED` |
| 4 | 사용자별 분당·일일 한도 | 429 | `RATE_LIMITED` |
| 5 | 전체 일일 한도 | 429 | `DAILY_LIMIT` |

인증된 사용자별 한도도 적용한다: 분당 3회, UTC 하루 20회. 한도 집계는 IP별·사용자별 수치를 모두 확인한다.

오류 본문 형식 (모든 JSON 오류 공통)

```json
{
  "code": "INVALID_INPUT",
  "message": "사건 내용은 5자 이상 300자 이하로 입력해 주세요.",
  "retryable": false
}
```

| 필드 | 설명 |
| --- | --- |
| `code` | 이 문서의 오류 코드 값 |
| `message` | 사용자에게 그대로 보여 줄 한국어 문장. 내부 정보나 사용자 입력을 포함하지 않는다 |
| `retryable` | 같은 요청을 다시 보내도 되는지 |

`CRISIS_SIGNAL`은 본문에 `helplines`를 더한다. 화면은 이 목록을 그대로 보여 준다.

```json
{
  "code": "CRISIS_SIGNAL",
  "message": "지금은 재판보다 도움이 먼저입니다. 아래 상담 전화로 바로 연락해 주세요.",
  "retryable": false,
  "helplines": [
    { "name": "자살예방 상담전화", "phone": "109", "hours": "24시간" },
    { "name": "정신건강 위기상담전화", "phone": "1577-0199", "hours": "24시간" },
    { "name": "긴급 상황", "phone": "119", "hours": "24시간" }
  ]
}
```

`RATE_LIMITED`와 `DAILY_LIMIT`은 `Retry-After` 헤더(초)를 함께 보낸다. `DAILY_LIMIT`은 다음 UTC 자정까지 남은 초다.
상담전화 번호는 제출 전에 공식 안내로 다시 확인한다 (미확인).

### 5.3 성공 응답

`200 OK`, `Content-Type: text/event-stream; charset=utf-8`, `Cache-Control: no-cache`.
각 이벤트는 `event: <이름>` 줄, `data: <한 줄 JSON>` 줄, 빈 줄로 구성한다.
브라우저의 `EventSource`는 POST를 지원하지 않으므로 UI는 `fetch`로 스트림을 읽는다.

```text
event: trial_started
data: {"submittedAt":"2026-11-05T14:30:00Z"}

event: stage
data: {"stage":"defense","n":1}

event: statement
data: {"n":1,"role":"defense","delta":"미루는 데에는 "}
```

### 5.4 이벤트

| 이벤트 | `data` | 설명 |
| --- | --- | --- |
| `trial_started` | `{"submittedAt": string}` | 서버가 재판 접수 시각을 알린다. 수용 기록의 시작 시간 지표에 사용한다 |
| `stage` | `{"stage": string, "n": number \| null}` | 단계가 바뀔 때 한 번. `stage`는 `defense`, `prosecution`, `rebuttal`, `judging`, `retry` 중 하나. `n`은 발언 번호(1~3), 그 밖에는 `null` |
| `statement` | `{"n": 1\|2\|3, "role": string, "delta": string}` | 발언의 일부 글자. 이어 붙이면 발언 전체가 된다. `role`은 `defense`(변호인) 또는 `prosecution`(검사) |
| `statement_done` | `{"n": 1\|2\|3, "role": string, "text": string}` | 발언 하나가 끝났을 때. `text`는 완성된 전체 발언 |
| `verdict` | 판결문 (5.5절) | 검증을 통과한 판결문. 한 번만 보낸다 |
| `error` | `{"code": string, "message": string, "retryable": boolean}` | 스트림 도중 오류. 보낸 뒤 스트림을 닫는다 |
| `done` | `{}` | 정상 종료. `verdict` 다음에 한 번 |

순서: `trial_started` → `stage(defense)` → `statement`… → `statement_done` → `stage(prosecution)` → … → `stage(rebuttal)` → … → `stage(judging)` → `verdict` → `done`.
판결 검증이 실패해 판사를 다시 부르면 `stage(retry)`를 한 번 보낸 뒤 `stage(judging)`부터 다시 한다. 판사의 출력은 JSON이므로 글자 단위로 보내지 않고 검증 후 `verdict` 하나로 보낸다.
`error`가 나오면 `verdict`와 `done`은 오지 않는다.
클라이언트가 연결을 끊으면 서버는 남은 모델 호출을 중단한다.

### 5.5 판결문 (`verdict`)

```json
{
  "summary": "변호인이 말한 막막함은 받아들이고, 검사가 지적한 마감 압박은 일부만 받아들입니다.",
  "cause": "막막함",
  "prescriptions": [
    {
      "title": "목차부터 만들기",
      "steps": ["보고서 제목을 쓴다", "소제목 3개를 적는다"],
      "minutes": 15,
      "reason": "시작이 막막하다는 변론에 맞춰 첫 단계를 작게 나누었습니다."
    }
  ],
  "evidence": [1, 2]
}
```

| 필드 | 형식 | 규칙 |
| --- | --- | --- |
| `summary` | string | 1~400자 |
| `cause` | string | `막막함`, `완벽주의`, `흥미 상실`, `시간 부족`, `피로` 중 하나 |
| `prescriptions` | array | 1~2개 |
| `prescriptions[].title` | string | 1~30자 |
| `prescriptions[].steps` | string[] | 2~4개, 각 1~80자 |
| `prescriptions[].minutes` | integer | 5~120 |
| `prescriptions[].reason` | string | 1~150자 |
| `evidence` | integer[] | 1~3개, 값은 1~3, 중복 없음 |

서버가 이 규칙을 모두 검증한 뒤에만 보낸다. 클라이언트는 형식이 다르면 `error`로 취급한다.
처방 제목이 겹치지 않게 하는 것은 프롬프트의 책임이며 서버 검증 항목이 아니다.

### 5.6 스트림 오류 코드

| `code` | `retryable` | 의미 | `message` 예 |
| --- | --- | --- | --- |
| `MODEL_ERROR` | true | 모델 호출 실패 | 법정에 문제가 생겼습니다. 잠시 후 다시 시도해 주세요. |
| `TIMEOUT` | true | 모델 호출 30초 또는 재판 전체 90초 초과 | 재판이 너무 오래 걸려 중단했습니다. 다시 시도해 주세요. |
| `VERDICT_INVALID` | true | 판결 검증이 재시도 후에도 실패 | 판결문을 만들지 못했습니다. 다시 시도해 주세요. |
| `INTERNAL` | false | 예상하지 못한 오류 | 알 수 없는 오류가 발생했습니다. |

## 6. 재판 기록 API

모든 경로는 인증이 필요하다. 서버가 세션에서 사용자 소유자를 구한다. 클라이언트가 보낸 `owner_id`, 사용자 ID, 이메일은 무시하고 권한 판단에 쓰지 않는다.

### 6.1 POST /api/records

사용자가 판결을 수용한 경우에만 호출한다. 서버는 요청을 검증한 뒤 인증 사용자 소유의 기록으로 저장하고 `201 Created`를 반환한다. `statements`, `evidence`는 저장하지 않는다.

```json
{
  "case": "보고서를 3일째 못 쓰고 있다.",
  "deadline": null,
  "submittedAt": "2026-11-05T14:30:00Z",
  "verdict": {
    "summary": "첫 단계를 작게 나누는 처방이 적절합니다.",
    "cause": "막막함",
    "prescriptions": [
      { "title": "목차부터 만들기", "steps": ["보고서 제목을 쓴다", "소제목 3개를 적는다"], "minutes": 15, "reason": "시작 부담을 줄입니다." }
    ]
  }
}
```

`acceptedAt`, 초기 `checks`, ID는 서버가 생성한다. `submittedAt`은 해당 사용자의 지표용 값이며 미래 시각은 거부한다. 저장 실패 시 오류를 반환하고 성공 응답처럼 처리하지 않는다.
`verdict`는 5.5절과 같은 검증 규칙을 적용하되, 저장 시에는 `evidence`를 제외한다. 생성 응답은 저장된 레코드의 전체 표현을 돌려준다.

### 6.2 GET /api/records

현재 사용자 기록만 반환한다. 기본 `limit=20`, 최대 50, 정렬은 `acceptedAt` 내림차순이며 `cursor`로 페이지를 넘긴다.

```json
{
  "items": [{ "id": "uuid", "case": "...", "deadline": null, "verdict": {}, "checks": [], "submittedAt": "...", "acceptedAt": "...", "firstCheckedAt": null, "completedAt": null }],
  "nextCursor": "opaque-cursor-or-null"
}
```

### 6.3 GET /api/records/{record_id}

현재 사용자가 소유한 기록만 반환한다. 없거나 다른 사용자 소유이면 `404`.

### 6.4 PATCH /api/records/{record_id}

집행 체크리스트만 갱신한다. `checks`의 차원과 단계 수가 저장된 처방과 다르면 `422`다. `firstCheckedAt`과 `completedAt`은 서버 시각으로 갱신하며, 클라이언트가 보낸 값은 받지 않는다. 소유자가 아니거나 기록이 없으면 `404`.

요청 본문은 `{ "checks": [[true, false]] }` 형식이다. 서버는 첫 단계가 체크된 순간 `firstCheckedAt`을 한 번 기록하고, 모든 단계를 완료한 시각을 `completedAt`에 기록한다. 체크를 모두 해제해도 최초 `firstCheckedAt`은 유지해 시작 시간 통계가 바뀌지 않게 한다.

### 6.5 DELETE /api/records/{record_id}

현재 사용자의 기록을 삭제한다. 다른 사용자 소유이거나 없는 ID는 `404`.

### 6.6 DELETE /api/records

현재 사용자의 재판 기록을 모두 삭제한다. 다른 사용자의 기록은 영향받지 않는다. 성공하면 `204 No Content`를 반환한다.

### 6.7 DELETE /api/account

확인 절차를 거쳐 앱 사용자와 소유한 모든 기록을 삭제하고 세션을 종료한다. 외부 OIDC 제공자의 계정은 삭제하지 않는다는 점을 미리 알린다. DB 백업에서는 설정된 백업 보존 기간이 끝날 때까지 삭제 데이터가 복원될 수 있다.

## 7. POST /api/appeal (P1)

요청

```json
{
  "recordId": "사용자 소유 기록 UUID",
  "newArgument": "새 주장 (5~200자)"
}
```

검사 순서, 한도, 오류 코드는 `/api/trial`과 같다. 위기 신호 검사는 `case`와 `newArgument` 모두에 적용한다.
응답은 `stage(judging)` → `verdict` → `done`이다. 항소도 재판 한도 1회로 센다. 이 엔드포인트는 P0이 모두 끝난 뒤에만 구현한다.
현재는 P0 데이터 정책에서 공방 발언을 저장하지 않으므로 구현하지 않으며, 구현 전에는 `404`를 반환한다. P1을 구현하려면 공방 기록의 별도 동의·보존 기간·삭제 정책과 DB 스키마를 먼저 확정해 관련 문서를 갱신한다. 재판 기록과 공방 기록의 소유권 검증은 필수다.

## 8. 한도

| 항목 | 값 | 기준 |
| --- | --- | --- |
| IP별 분당 | 3회 | 요청 시작 시각 기준 60초 이동 구간 |
| IP별 일일 | 20회 | UTC 날짜 |
| 사용자별 분당 | 3회 | 인증된 사용자 ID, 60초 이동 구간 |
| 사용자별 일일 | 20회 | 인증된 사용자 ID, UTC 날짜 |
| 전체 일일 | 300회 | UTC 날짜. 서버 재시작 시 초기화되는 한계가 있다 |
| 재판 1건의 모델 호출 | 최대 5회 | 공방 3 + 판사 1 + 판사 재시도 1 |

IP는 신뢰하도록 설정한 수신 프록시가 전달한 주소만 사용한다. 클라이언트가 임의로 보낸 `X-Forwarded-For`를 직접 신뢰하지 않는다. 신뢰할 프록시와 실제 헤더 형식은 배포 전에 확인한다.
한도는 사전 검사를 통과한 요청만 센다. `INVALID_INPUT`, `CRISIS_SIGNAL`로 거부된 요청과 한도를 넘긴 요청은 세지 않는다. 프로세스 메모리 기반 한도는 서버 재시작 시 초기화되며 복제본이 여러 개면 정확한 전역 한도가 아니다.

## 9. 로그 규칙

로그에는 단계명, 소요 시간, 오류 코드, 요청 ID만 남긴다. 사건 내용, 발언, 판결문, 인증 토큰, IP 전체는 남기지 않는다.

## 10. 변경 기록

| 날짜 | 내용 | 작성자 |
| --- | --- | --- |
| 2026-11-05 | 최초 작성 | |
