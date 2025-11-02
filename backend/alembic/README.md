# Migrations & Database Notes (Backend)

This document focuses on the database and Alembic migration decisions used in the backend.

## Key decisions

- Primary key type: INT (SQLAlchemy `Integer`).
  - Rationale: project prefers 32-bit integers for IDs (smaller storage). If you expect >2.1B rows, switch to `BigInteger` and generate migrations accordingly.
- `file_size` is left as `BigInteger` because file sizes can exceed INT range.

## How to run migrations (PowerShell)

1. Ensure your virtualenv is active and dependencies are installed.
2. Ensure `.env` has a valid `DATABASE_URL` (example present in `.env`).
3. Run the migrations:

```powershell
# upgrade to head
alembic upgrade head

# generate an autogenerate migration (safe to run, will be empty if no changes)
alembic revision --autogenerate -m "autogenerate: sync models"
```

## Common troubleshooting

### 1) Multiple heads

If you see "Multiple head revisions are present" it means there are more than one independent revision files (often because two initial migrations were created). Fix options:

- Preferred: keep a single initial migration file (the one that actually created the schema) and remove or convert the other(s).
- Safe quick fix (used in this repository): set the `down_revision` of the duplicate file to the existing initial revision and make it a no-op (or delete the duplicate file). Deleting is fine when you control all environments.

### 2) `alembic_version` points to a missing revision

If `alembic` complains it "Can't locate revision identified by 'XXXX'", check the DB table `alembic_version` and correct it to point at the real head revision. A small helper script is provided in `scripts/fix_alembic_version.py` which:
- reads `DATABASE_URL` from .env
- inspects `alembic_version`
- updates it to `7bea168f7920` (the repository head used at the time this doc was written) if needed

Run it like this (PowerShell):

```powershell
python scripts\fix_alembic_version.py
```

You can also inspect the table manually with your MySQL client:

```powershell
# using mysql client (example) - replace credentials/db
mysql -u <user> -p -h <host> -P <port> -e "SELECT * FROM <database>.alembic_version;"
```

If you need to set the version manually (careful):

```sql
-- update to known revision
UPDATE alembic_version SET version_num = '7bea168f7920';
```

### 3) Alembic autogenerate imports

`alembic/env.py` must import all model modules so SQLAlchemy's `MetaData` sees every table/column. In this repo the `env.py` imports:

```python
from app.models.base import Base
import app.models.task
import app.models.media
import app.models.story
import app.models.system

target_metadata = Base.metadata
```

Keep imports even if unused — this ensures `autogenerate` is accurate.

### 4) SQLAlchemy compatibility

This project supports both SQLAlchemy 1.x and 2.x styles for declarative base. See `src/app/db/base.py` which prefers `DeclarativeBase` when available and falls back to `declarative_base()` for older versions. No action is needed unless you intentionally upgrade/downgrade SQLAlchemy.

## Safety: wiping the DB (destructive)

Only do this in development. Example (PowerShell + mysql client):

```powershell
mysql -u <user> -p -h <host> -P <port> -e "DROP DATABASE IF EXISTS `<database>`; CREATE DATABASE `<database>` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
# then run migrations
alembic upgrade head
```

Or drop all tables and re-run migrations:

```powershell
mysql -u <user> -p -h <host> -P <port> <database> -e "SET FOREIGN_KEY_CHECKS=0; DROP TABLE IF EXISTS task_logs, files, task_steps, scenes, tasks; SET FOREIGN_KEY_CHECKS=1;"
alembic upgrade head
```

## Notes & recommendations

- When changing PK types (INT <-> BIGINT), always make a coordinated change: update models first, then generate/inspect migrations, and apply them in environments where data is preserved. If converting existing production data, test `ALTER TABLE ... MODIFY COLUMN` on a copy first and ensure signed/unsigned consistency.