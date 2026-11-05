# 데이터베이스

회원별 재판 기록을 저장하기 위해 Azure Database for PostgreSQL을 사용합니다.
스키마, 소유권, 보존·삭제 규칙은 [데이터 명세](../docs/DATABASE.md)를 따릅니다.

- [migrations/](./migrations/)의 Alembic 마이그레이션이 실제 스키마 변경의 기준입니다. [schema.sql](./schema.sql)은 이를 읽기 쉽게 정리한 스키마 참고 자료입니다.
- 로컬 PostgreSQL은 저장소 루트의 `compose.yaml`로 실행합니다. 명령은 [데이터 명세](../docs/DATABASE.md) 1절을 참고하세요.
