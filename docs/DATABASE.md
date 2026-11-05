# 인증·데이터 명세

## 1. 결정

이 앱은 여러 사용자가 가입해 각자 재판을 받고 자신의 기록을 다시 보는 서비스다. 따라서 브라우저에만 저장하지 않고 **Azure Database for PostgreSQL**에 사용자별 기록을 저장한다. 스키마는 Alembic 마이그레이션으로 버전 관리한다. 마이그레이션을 만들기 전의 초안은 [database/schema.sql](../database/schema.sql)이다.
Azure Database for PostgreSQL은 Dockerfile로 만드는 이미지가 아니라 Azure가 운영하는 관리형 서비스다. 개발·테스트용 PostgreSQL은 Docker 컨테이너로 실행할 수 있지만, 배포 환경의 DB로 컨테이너를 쓰지는 않는다. 앱 `Dockerfile`은 FastAPI와 프런트엔드 빌드 결과를 이미지로 만들고, 로컬 DB 컨테이너는 Docker Compose로 별도 관리한다.

### 로컬 개발용 PostgreSQL

Docker Desktop이 설치된 개발 PC에서 아래 내용을 저장소 루트의 `compose.yaml`로 두고 PostgreSQL을 실행한다. 버전은 Azure 서버와 같은 주 버전으로 맞추고, 비밀번호는 로컬 전용으로만 사용한다.

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: vibe_dev
      POSTGRES_USER: vibe_dev
      POSTGRES_PASSWORD: local-dev-only
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

실행·중지는 `docker compose up -d postgres`, `docker compose stop postgres`를 쓴다. `docker compose down`은 컨테이너만 내리고 named volume의 개발 데이터는 유지한다. `docker compose down -v`는 로컬 DB 데이터를 삭제하므로 초기화할 때만 쓴다. 운영 배포는 Azure Database for PostgreSQL의 연결 정보를 앱 컨테이너에 비밀로 주입한다. PostgreSQL 컨테이너를 Azure Container Apps의 로컬 파일 시스템에 두면 영속성·백업·복구·고가용성을 보장하기 어려우므로 운영 DB로 사용하지 않는다.

로컬 `.env`의 연결 주소는 `postgresql://vibe_dev:local-dev-only@localhost:5432/vibe_dev`를 쓴다. 이 개발용 비밀번호를 Azure나 커밋에 사용하지 않는다.

가입·로그인은 Microsoft Entra External ID가 처리한다. 앱은 비밀번호를 받거나 저장하지 않으며, 검증된 OIDC `issuer`와 `subject`를 사용자 식별자로 쓴다. 이메일은 소유권 키로 쓰지 않는다.

재판 입력은 모델 제공자에게 전송된다. 사용자가 판결을 수용하기 전에는 DB에 기록하지 않는다. 수용 시 사건 내용·마감일·판결·집행 진행을 저장하되, 공방 발언은 저장하지 않는다. 이 처리와 보관을 재판 전에 사용자에게 알린다.

## 2. 데이터 위치·수명

| 데이터 | 위치 | 생성 시점 | 삭제 시점 |
| --- | --- | --- | --- |
| OIDC 계정 자격 증명·로그인 정보 | 관리형 인증 제공자 | 회원가입·로그인 | 제공자 정책에 따름 |
| 앱 사용자 연결 정보 | PostgreSQL `app_users` | 해당 OIDC 계정의 첫 앱 로그인 | 앱 계정 삭제 시 |
| 수용한 재판 기록 | PostgreSQL `trials` | 사용자가 판결을 수용할 때 | 사용자가 기록 또는 앱 계정을 삭제할 때 |
| 진행 중인 재판·공방 발언 | 서버 요청 메모리 | 재판 중 | 요청 종료·실패·취소 시 |
| IP·계정별 요청 한도 집계 | 서버 프로세스 메모리 | 요청 시 | 기간 만료·프로세스 재시작 시 |
| 예시 사건 | 정적 파일 `frontend/public/samples.json` | 배포물에 포함 | 새 배포로 교체할 때 |
| 사용자 입력·판결·토큰·IP 로그 | 저장하지 않음 | — | — |

## 3. PostgreSQL 스키마

### 3.1 `app_users`

| 필드 | 형식 | 규칙 |
| --- | --- | --- |
| `id` | UUID | 기본 키. 앱 내부 사용자 ID |
| `oidc_issuer` | text | 검증된 토큰의 `iss` |
| `oidc_subject` | text | 검증된 토큰의 `sub` |
| `created_at` | timestamptz | 앱에 처음 로그인한 시각 |

`(oidc_issuer, oidc_subject)`는 고유해야 한다. 사용자 ID는 인증된 토큰으로 서버가 조회하며, 클라이언트가 보낸 사용자 ID나 이메일로 정하지 않는다. 이름·이메일 등 기능에 필요하지 않은 프로필은 저장하지 않는다.

### 3.2 `trials`

| 필드 | 형식 | 규칙 |
| --- | --- | --- |
| `id` | UUID | 기본 키 |
| `owner_id` | UUID | `app_users.id` 외래 키, 사용자 삭제 시 연쇄 삭제 |
| `case_text` | text | 수용한 재판의 사건 내용 (5~300자) |
| `deadline` | date, nullable | 사용자가 입력한 마감일 |
| `verdict` | jsonb | 수용한 판결의 `summary`, `cause`, `prescriptions` |
| `checks` | jsonb | 처방별 단계 완료 상태 |
| `submitted_at` | timestamptz | 재판 요청 시각 |
| `accepted_at` | timestamptz | 사용자가 수용한 시각. 서버 시각으로 기록 |
| `first_checked_at` | timestamptz, nullable | 첫 체크 시각 |
| `completed_at` | timestamptz, nullable | 모든 단계를 완료한 시각 |
| `created_at` | timestamptz | 레코드 생성 시각 |
| `updated_at` | timestamptz | 마지막 변경 시각 |

인덱스는 `(owner_id, accepted_at DESC)`에 둔다. `verdict`에는 API 판결문 중 `evidence`를 제외해 저장한다. 근거 번호는 저장하지 않는 공방 발언을 가리키므로 기록 조회에 쓸 수 없다.

## 4. 저장·조회 규칙

1. 사용자가 판결을 수용한 뒤에만 `trials`에 생성한다. 기각·오류·진행 중인 재판은 저장하지 않는다.
2. 재판 기록에는 사건 원문, 선택적 마감일, 판결 요약·원인 추정·처방, 체크 상태, 지표용 시각을 저장한다.
3. 변호인·검사 발언, 인증 토큰, IP, 모델 프롬프트, 거부·오류 응답은 DB에 저장하지 않는다.
4. 기록 목록·상세·수정·삭제 쿼리는 항상 서버가 인증 토큰에서 확인한 `owner_id`로 제한한다. 사용자 A가 사용자 B의 ID를 알아도 조회·수정·삭제할 수 없어야 한다.
5. 다른 사용자의 기록 ID에 대한 조회·변경 응답은 존재 여부를 노출하지 않도록 `404`로 통일한다.
6. 목록은 `accepted_at DESC` 순으로 페이지 조회한다. 페이지 크기는 기본 20개, 최대 50개다.
7. 집행 진척 변경은 해당 소유자의 `checks`, `first_checked_at`, `completed_at`만 갱신한다.
8. 앱 계정 삭제 시 해당 앱 사용자와 소유한 재판 기록을 삭제하고 세션을 종료한다. 외부 인증 제공자 계정 자체는 삭제하지 않는다는 점을 안내한다.
9. 사용자가 기록을 개별 삭제하거나 전체 삭제할 수 있게 한다.

## 5. 보안·개인정보 규칙

- 인증은 관리형 OIDC Authorization Code 흐름을 사용한다. ID 토큰의 서명, 발급자, 대상, 만료를 서버에서 검증한다.
- 로그인 시작과 콜백에는 `state`, `nonce`, PKCE를 적용하고 등록된 redirect URI만 허용한다. 세션을 만들 때 세션 ID를 교체한다.
- 인증 토큰을 URL이나 `localStorage`에 저장하지 않는다. 세션 쿠키를 쓸 경우 `Secure`, `HttpOnly`, 적절한 `SameSite` 속성 및 CSRF 방어를 적용한다.
- 앱과 DB 연결은 TLS를 사용한다. DB 자격 증명은 Azure 관리형 비밀로 주입한다. SQL은 바인딩 파라미터를 쓴다.
- PostgreSQL은 공개 네트워크 접근을 열어 두지 않는다. 앱에서 오는 연결만 허용하는 네트워크·방화벽 규칙을 적용한다.
- DB 저장 시 Azure의 저장 암호화 설정을 확인한다. 백업 암호화와 보존 기간도 배포 전에 정하고 사용자에게 고지한다.
- 사건 입력은 외부 AI 모델로 전송됨을 재판 전에 알린다. 모델 제공자의 데이터 사용·보관 조건은 배포 전 확인한다.
- 애플리케이션 로그와 분석 도구에 사건, 판결, 인증 토큰, IP를 기록하지 않는다. 서버 기본 접근 로그도 IP를 보관하지 않도록 끄거나 익명화한다. 단계명, 요청 ID, 소요 시간, 오류 코드만 남긴다.
- DB에서 불러온 문자열도 신뢰하지 않고 화면에 `textContent`로 출력한다.

## 6. 기록 지표

지표는 SQL 집계 또는 서버에서 인증 사용자의 기록만 대상으로 계산한다.

| 지표 | 계산 |
| --- | --- |
| 수용 건수 | 해당 사용자의 재판 기록 수 |
| 이행률 | `completed_at`이 있는 기록 수 ÷ 전체 기록 수 |
| 시작까지 걸린 시간 | `first_checked_at - submitted_at` 평균 (첫 체크 기록만) |

기록이 없거나 해당 지표의 표본이 없으면 숫자 대신 "기록 없음"을 표시한다.

## 7. 보존·삭제와 운영

- 활성 기록은 사용자가 삭제할 때까지 보관한다. 계정 삭제 시 앱 DB의 사용자 데이터도 삭제한다.
- 관리형 PostgreSQL 백업은 삭제 직후에도 설정된 백업 보존 기간 동안 복원될 수 있다. 백업 보존 기간과 백업에서의 만료 시점을 배포 전에 확정해 개인정보 안내에 공개한다.
- 복구·마이그레이션 권한은 최소 인원에게만 부여하고, 운영 접근을 감사한다.
- Azure PostgreSQL은 상시 비용이 발생할 수 있다. SKU, 백업, 네트워크, 예산 경보를 배포 전에 확인한다.

## 8. 환경 변수

| 이름 | 필수 | 설명 |
| --- | --- | --- |
| `DATABASE_URL` | 예 | PostgreSQL 연결 문자열. 비밀 저장소에서 주입 |
| `OIDC_ISSUER` | 예 | Entra External ID 발급자 URL. 서버가 `/.well-known/openid-configuration`을 조회 |
| `OIDC_CLIENT_ID` | 예 | 앱 등록의 클라이언트 ID |
| `OIDC_CLIENT_SECRET` | 공급자 방식에 따라 | 비밀 클라이언트 앱일 때만 비밀 저장소에서 주입 |
| `SESSION_SECRET_KEY` | 예 | 세션 쿠키 서명 키. 충분히 긴 임의 값으로 만들고 비밀 저장소에서 주입 |
| `PUBLIC_BASE_URL` | 예 | 앱의 외부 기본 주소. OIDC redirect URI `{PUBLIC_BASE_URL}/auth/callback` 생성에 사용 |
| `SESSION_TTL_SECONDS` | 아니오 | 세션 유효 시간(초), 기본값 `28800` |
| `COOKIE_SECURE` | 아니오 | HTTPS 전용 쿠키 여부. 기본값은 `true`; 로컬 HTTP에서만 `false` |
| `TRUSTED_PROXY_IPS` | 아니오 | 전달 IP 헤더를 신뢰할 프록시 IP/CIDR 목록 |
| `COPILOT_GITHUB_TOKEN` | 예 | Copilot 호출 토큰. 비밀 저장소에서 주입 |
| `PORT` | 아니오 | 기본값 `8000` |
| `LOG_LEVEL` | 아니오 | 기본값 `INFO` |
| `IP_PER_MINUTE` | 아니오 | IP별 분당 한도, 기본값 `3` |
| `IP_PER_DAY` | 아니오 | IP별 일일 한도, 기본값 `20` |
| `USER_PER_MINUTE` | 아니오 | 사용자별 분당 한도, 기본값 `3` |
| `USER_PER_DAY` | 아니오 | 사용자별 일일 한도, 기본값 `20` |
| `GLOBAL_PER_DAY` | 아니오 | 전체 일일 한도, 기본값 `300` |
| `MODEL_TIMEOUT_SECONDS` | 아니오 | 기본값 `30` |
| `TRIAL_TIMEOUT_SECONDS` | 아니오 | 기본값 `90` |

`.env.example`에는 비밀이 아닌 변수 이름과 로컬 개발용 자리표시자만 둔다. 실제 비밀을 커밋하지 않는다.

## 9. P1 항소의 데이터 결정

P0에서는 공방 발언을 저장하지 않는다. 항소가 원래 공방을 근거로 판결을 다시 내려야 한다면, 구현 전에 발언 보관의 필요성·기간·사용자 동의를 별도로 정하고 스키마와 개인정보 안내를 갱신한다. 동의 없이 기존 정책을 넓히지 않는다.
