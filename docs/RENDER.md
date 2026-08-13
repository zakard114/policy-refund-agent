# Deploy on Render (official public face)

Product + Insights run on **Render**. Streamlit Community Cloud is a **secondary** prototype only.

## Blueprint

1. Push `main` to GitHub.
2. [Render](https://dashboard.render.com/) → **New** → **Blueprint** → select this repo (`render.yaml`).
3. Create services:
   - `policy-refund-agent` — Product (Streamlit interim; FastAPI Product comes in polish Phase 1–2)
   - `policy-refund-agent-grafana` — Insights (Grafana → Neon)
4. Fill **sync: false** env vars in the Dashboard (never commit secrets):

| Service | Required |
|---------|----------|
| Product | `CEREBRAS_API_KEY`, `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| Grafana | `GF_SECURITY_ADMIN_PASSWORD`, `PRA_PG_HOST` (e.g. `ep-….neon.tech:5432`), `PRA_PG_USER`, `PRA_PG_PASSWORD`, `PRA_PG_DB` |

`POSTGRES_SSLMODE` / `PRA_PG_SSLMODE` default to `require` in the blueprint.

5. After first deploy, set GitHub **About → Homepage** to the Product URL.
6. Keep Ops (Kestra / local Postgres `:5435` / Grafana `:3002`) off the public internet.

## Health checks

- Product: `/_stcore/health`
- Grafana: `/api/health`

## Notes

- Free-tier sleeps; first request after idle may be slow.
- Grafana meta-DB on Render uses SQLite (see `grafana/docker-entrypoint.sh`). Dashboard **data** still comes from Neon via `PRA_PG_*`.
- Local Compose is unchanged: Streamlit `:8502`, Grafana Ops `:3002`.
