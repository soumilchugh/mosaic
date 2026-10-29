# Database Migrations

Mosaic uses Alembic for ordered PostgreSQL schema changes. The migration URL is read
from `MOSAIC_DATABASE_URL`; local development falls back to the PostgreSQL service in
`docker-compose.yml`.

```bash
alembic upgrade head
alembic downgrade -1
alembic current
```

Historical migrations must remain self-contained. Do not make an existing migration
depend on current ORM model definitions.
