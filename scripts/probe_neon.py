"""Probe Neon via PRA_PG_* (Grafana path). Prints no secrets."""

from __future__ import annotations

from dotenv import dotenv_values
import psycopg

e = dotenv_values(".env")
raw_host = e.get("PRA_PG_HOST") or ""
user = e.get("PRA_PG_USER")
password = e.get("PRA_PG_PASSWORD")
db = e.get("PRA_PG_DB")
ssl = e.get("PRA_PG_SSLMODE") or "require"

host = raw_host
port = 5432
if ":" in raw_host:
    h, p = raw_host.rsplit(":", 1)
    if p.isdigit():
        host, port = h, int(p)

ok = all([host, user, password, db])
print("neon_config_ok=", ok)
print("host_suffix=", host[-36:] if host else None)
if not ok:
    raise SystemExit(1)

conninfo = (
    f"host={host} port={port} dbname={db} user={user} "
    f"password={password} sslmode={ssl}"
)
with psycopg.connect(conninfo, connect_timeout=15) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        print("neon_connect=", cur.fetchone()[0])
        cur.execute("SELECT to_regclass('public.conversation_logs')")
        print("conversation_logs=", cur.fetchone()[0])
