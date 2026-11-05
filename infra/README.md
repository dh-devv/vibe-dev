# 배포 인프라

Azure Container Apps 배포 설정을 관리합니다. 기술 선택과 리소스 범위는 [TRD.md](../docs/TRD.md)를 기준으로 하며, `azd`와 Docker를 사용합니다.

## 만들어지는 리소스

리소스 그룹 하나에 아래만 만듭니다. 정의는 [main.bicep](./main.bicep)과 [resources.bicep](./resources.bicep)에 있습니다.

| 리소스 | 설정 |
| --- | --- |
| Container Apps 환경, 앱 1개 | 0.5 vCPU, 1GiB, 복제본 최소 0·최대 1 |
| Azure Container Registry | Basic, 관리자 계정 끔, 관리 ID로 이미지 가져오기 |
| Azure Database for PostgreSQL | Burstable B1ms, 버전 16, 32GiB |
| Log Analytics | 보관 30일 |

앱 이미지는 화면(`frontend/dist`)과 API를 한 컨테이너에서 제공합니다. 시작할 때 `RUN_MIGRATIONS=true`이면 마이그레이션을 먼저 적용합니다.

## 배포 순서

```powershell
az login
azd auth login
azd env new <환경이름>
azd env set AZURE_LOCATION koreacentral
azd env set COPILOT_GITHUB_TOKEN <토큰>
azd env set POSTGRES_PASSWORD <영문·숫자 24자 이상>
azd env set SESSION_SECRET_KEY <32자 이상 무작위 문자열>
azd up
```

- 비밀 값은 `azd env set`으로만 넣습니다. 파일, 커밋, 채팅에 붙이지 않습니다.
- `POSTGRES_PASSWORD`는 연결 주소에 들어가므로 영문·숫자만 씁니다.
- 로그인(OIDC) 값은 설정하기 전까지 비워 둡니다. 비어 있으면 재판 요청이 인증 오류로 거절됩니다.
  `azd env set OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`을 설정한 뒤 `azd provision`을 다시 실행합니다.
- 첫 배포의 리소스 생성 단계에는 기본 샘플 이미지가 올라가고, 이어지는 배포 단계에서 이 앱 이미지로 바뀝니다.

## 배포 뒤 확인

1. 출력된 `SERVICE_WEB_URI`의 `/health`가 200인지 봅니다.
2. Entra External ID 앱 등록에 `<SERVICE_WEB_URI>/auth/callback`을 리디렉션 URI로 추가합니다.
3. 배포 URL에서 가입, 재판, 수용, 기록 조회, 삭제를 직접 실행합니다.
4. 프록시 뒤 IP 한도는 미확인입니다. `TRUSTED_PROXY_IPS`는 비워 두었으므로 실제 동작을 확인한 뒤 정합니다.

## 삭제

`azd down`은 리소스 그룹의 모든 리소스와 DB 데이터를 지웁니다. 사용자 확인 후에만 실행합니다.
