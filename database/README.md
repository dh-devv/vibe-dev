# 데이터베이스

회원별 재판 기록을 저장하기 위해 Azure Database for PostgreSQL을 사용합니다.
스키마, 소유권, 보존·삭제 규칙은 [데이터 명세](../docs/DATABASE.md)를 따릅니다.

- [schema.sql](./schema.sql)은 초기 스키마 초안입니다. Alembic 마이그레이션(`migrations/`)을 만들면 그 기준으로 옮깁니다.
- 로컬 PostgreSQL은 저장소 루트의 `compose.yaml`로 실행합니다. 명령은 [데이터 명세](../docs/DATABASE.md) 1절을 참고하세요.
