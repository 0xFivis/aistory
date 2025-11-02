"""Check and (optionally) fix alembic_version in the database.
This script reads DATABASE_URL from .env and will update the alembic_version
row to '7bea168f7920' if it currently references the missing '0f49690850e3'.
"""
import os
import sys

from sqlalchemy import create_engine, text

BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(BACKEND_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from app.core.env import load_env  # type: ignore[import-not-found]

load_env()
url = os.getenv('DATABASE_URL')
if not url:
    print('DATABASE_URL not found in environment')
    raise SystemExit(1)

engine = create_engine(url)
with engine.begin() as conn:
    try:
        res = conn.execute(text('SELECT version_num FROM alembic_version'))
        rows = list(res)
        print('alembic_version rows:', rows)
        if rows:
            cur = rows[0][0]
            print('Current version:', cur)
            if cur == '0f49690850e3':
                print('Found old revision, updating to 7bea168f7920')
                conn.execute(text("UPDATE alembic_version SET version_num='7bea168f7920'"))
                print('Updated')
        else:
            print('No alembic_version row found, inserting 7bea168f7920')
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('7bea168f7920')"))
            print('Inserted')
    except Exception as e:
        print('Error querying alembic_version:', e)
        raise
