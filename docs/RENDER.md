# Deploy on Render (official public face)

Product + Insights run on **Render**. Streamlit Community Cloud is a **secondary** prototype only.

## From your dashboard (step-by-step)

You already see **Ungrouped Services** with old `Notes-Backend` — leave it alone. New services are separate.

### 0) Before Render

1. Repo `zakard114/policy-refund-agent` `main` has `render.yaml` (already pushed for Phase 0).
2. Keep Neon values ready (host / db / user / password). Do **not** paste them into GitHub.

### 1) Start Blueprint

1. Top-left / header **New** (not “Create your first project” — Project is optional grouping).
2. Choose **Blueprint**.
3. Connect GitHub if asked → pick **`zakard114/policy-refund-agent`**.
4. Branch: **`main`**. Render reads root **`render.yaml`**.
5. Review the service list, then continue / apply.

Expected services (names may match exactly):

| Service | Role |
|---------|------|
| `policy-refund-agent` | Product (FastAPI + static hub/chat) |
| `policy-refund-agent-api` | Integrate (`/docs`, same image) |
| `policy-refund-agent-grafana` | Insights |

Product health check: `/health` (not Streamlit `/_stcore/health`).

### 2) Region (Guam)

Blueprint default in repo is **`oregon`** (same as your old Notes-Backend).

| Region | From Guam |
|--------|-----------|
| **Singapore** | Usually best latency in Render’s common list |
| Oregon | OK, a bit farther; fine if free-tier only offers this |

**To use Singapore:** either edit each service’s **Region** in the Blueprint review UI before create, or tell the agent to change `region:` in `render.yaml` and push, then re-apply Blueprint.

Free tier region availability changes; if Singapore is greyed out, stay on **Oregon**.

### 3) Fill secrets (`sync: false`)

Dashboard will ask for env vars marked sync:false. Use the **same Neon** as Streamlit Cloud thumbs.

**Product** (`policy-refund-agent`) — and **API** if created:

| Key | Value |
|-----|--------|
| `CEREBRAS_API_KEY` | your Cerebras key |
| `POSTGRES_HOST` | Neon host only, e.g. `ep-….neon.tech` (pooled OK) |
| `POSTGRES_DB` | e.g. `neondb` |
| `POSTGRES_USER` | e.g. `neondb_owner` |
| `POSTGRES_PASSWORD` | Neon password |
| `PRA_OPS_PASSWORD` | shared Ops unlock for Product hub **Ops 🔒** (local guidance only; fail-closed if unset) |

(`POSTGRES_PORT=5432`, `POSTGRES_SSLMODE=require` are usually prefilled.)

Ops stays locked off the public face: set `PRA_OPS_PASSWORD` in the Dashboard for **Product** (`policy-refund-agent`). Never commit the real value; never publish it in README. If unset, `/ops/unlock` returns 503 and the UI refuses unlock.

**Operator guide:** [`docs/OPS_PASSWORD.md`](OPS_PASSWORD.md) — local `.env` + Render Add steps.

**Grafana** (`policy-refund-agent-grafana`):

| Key | Value |
|-----|--------|
| `GF_SECURITY_ADMIN_PASSWORD` | pick a password (not `admin` in public if you can avoid it) |
| `PRA_PG_HOST` | `ep-….neon.tech:5432` (host **with** port) |
| `PRA_PG_USER` / `PRA_PG_PASSWORD` / `PRA_PG_DB` | same Neon |

### 4) Wait for build

1. Open each service → **Logs** / **Events**.
2. First Docker build can take several minutes.
3. Free tier sleeps when idle — first hit after sleep is slow.

### 5) Smoke checks

| Service | URL path |
|---------|----------|
| Product | `https://<product>.onrender.com/` and `/health` (FastAPI Product + static UI) |
| API | `https://<api>.onrender.com/health` and `/docs` |
| Grafana | `https://<grafana>.onrender.com/d/pra-agent-monitoring/pra-agent-monitoring?orgId=1` (anonymous Viewer) |

Try on Product: `Can I refund order ZK-1001?` (Agent tools on).  
Optional: Settings → turn **Generate answer** off for retrieval-only citations (`POST /answer` with `"use_llm": false`).

### 6) After it works

1. GitHub repo → **About → Homepage** = Product URL (official).
2. Streamlit Cloud URL stays **secondary** only.
3. Do **not** put Kestra / local Ops on Render.

---

## Local API (dev)

```powershell
uv sync
uv run pra-api
# http://localhost:8000/docs
# POST /search {"query":"refund deadline","use_llm":false}
```

## Notes

- Free-tier sleeps; cold start is normal.
- Grafana meta-DB on Render uses SQLite; dashboard **data** is Neon via `PRA_PG_*`.
- Local Compose Ops unchanged: Streamlit `:8502`, Grafana `:3002`.
