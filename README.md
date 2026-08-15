# Policy & Refund Support Agent

![Zakard Shop Policy Support — hero banner](docs/images/readme-hero-banner.png)

**Grounded policy RAG for e-commerce refund support** — retrieve policy clauses, answer with citations, refuse safely when context is missing, and measure quality with an offline eval harness.

Built as a capstone project for [LLM Zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp).

**Official Product (Render):** https://policy-refund-agent.onrender.com  
**Integrate API:** https://policy-refund-agent-api.onrender.com/docs · also `/docs` on Product  
**Insights (Grafana):** https://policy-refund-agent-grafana.onrender.com/d/pra-agent-monitoring/pra-agent-monitoring?orgId=1<br>
**Secondary prototype (Streamlit Cloud — may sleep):** https://policy-refund-agent.streamlit.app/  
Try chips: ZK-1001 · Non-refundable · 한국어 · or ask freely (Agent tools on).

Hub on Product: **Product · Insights · Integrate · GitHub** · Ops locked (local only).

## Mission

**Zakard Shop Refund CS — precision over vibes.**  
Refund handling needs clarity, not guesses. This agent answers from **verified policy documents and order data (demo tools)** only.

- Safely abstains on unverified or out-of-scope questions to minimize hallucinations.
- Every response carries citations and leaves operational logs.

Keeping the stack behind the scenes while delivering fast, grounded answers — that is why this agent exists.

## Table of contents

- [Mission](#mission)
- [Problem](#problem)
- [Status](#status)
- [Configuration](#configuration)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Architecture](#architecture)
- [Decisions and trade-offs](#decisions-and-trade-offs)
- [Project structure](#project-structure)
- [Screenshots](#screenshots)
- [Evaluation criteria](#evaluation-criteria)
- [Cloud deployment](#cloud-deployment)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Problem

This project answers questions and evaluates refund eligibility **from the Zakard Shop refund policy document** (`data/refund_policy.md`), not from general LLM knowledge.

Support teams need answers **strictly from policy documents** and consistent refund decisions. This app:

1. Retrieves policy clauses via hybrid search (keyword + vector RRF) with citations
2. Supports multilingual questions (translate-to-English for search, answer in the user's language)
3. Returns safe fallbacks when context is insufficient or prompt injection is detected
4. Evaluates refund eligibility with mock order tools (`lookup_order` / `evaluate_refund`)
5. Measures quality offline (Hit Rate, MRR, LLM-as-judge), including multilingual questions (Korean / Spanish / French) with English glosses in [`data/eval_data.json`](data/eval_data.json)
6. Offers a retrieval-only Product/API mode that returns ranked policy citations without an LLM call

### Knowledge base

| Item | Detail |
|------|--------|
| Source | Synthetic **Zakard Shop** refund & return policy |
| File | [`data/refund_policy.md`](data/refund_policy.md) |
| License | Original text written for this project (demo use); not scraped from a live retailer |


[↑ Contents](#table-of-contents)

---

## Status

**Capstone-ready** — RAG + hybrid RRF + agent tools + safety + Kestra + Grafana.  
**Public deploy:** **Render = official** Product / Insights / Integrate ([`docs/RENDER.md`](docs/RENDER.md), [`render.yaml`](render.yaml)). **Streamlit Community Cloud = secondary** prototype (may sleep) — [Cloud deployment](#cloud-deployment). See [Evaluation criteria](#evaluation-criteria).

### Paths (read this first)

Commands below assume you are in the **repository root** after cloning.

| | |
|--|--|
| **Your machine** | Whatever path you cloned into, e.g. `~/policy-refund-agent` or `C:\dev\policy-refund-agent` |
| **Example used in this README** | `E:\IT_SPACES\AI\Projects\llm\policy-refund-agent` (author’s Windows layout — **not required**) |

Replace the example `cd …` with your own clone path. Relative paths like `data/`, `app/`, and `docker compose` are the same everywhere.


[↑ Contents](#table-of-contents)

---

## Configuration

| Role | Provider | Variables |
|------|----------|-----------|
| App LLM | **Gemma on Cerebras** (OpenAI-compatible) | `PRA_LLM_BACKEND=cerebras`, `CEREBRAS_*` in `.env` |
| Ops hub gate | Local guidance only (password-locked) | `PRA_OPS_PASSWORD` in `.env` / Render Dashboard — **not** published in README |

```powershell
# Example path (replace with your clone root):
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
. .\scripts\use_e_drive.ps1   # optional: author Windows cache layout on E:
copy .env.example .env        # set CEREBRAS_API_KEY inside
uv sync
uv run pra-check-llm
```


[↑ Contents](#table-of-contents)

---

## Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- [Docker Desktop](https://www.docker.com/)
- LLM API key (Cerebras / OpenAI-compatible)


[↑ Contents](#table-of-contents)

---

## Quick start

**Recommended:** Postgres + Grafana + Streamlit via Compose.

```powershell
# Example path (replace with your clone root):
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
. .\scripts\use_e_drive.ps1   # optional
copy .env.example .env   # if missing — set CEREBRAS_API_KEY
docker compose up -d postgres grafana streamlit
docker compose ps
# Streamlit http://localhost:8502 · Grafana http://localhost:3002 (admin/admin)
# Postgres host :5435 (from Streamlit container use host name `postgres`)
```

Optional orchestration UI: `docker compose up -d kestra-postgres kestra` → `http://localhost:8085` (`admin@kestra.io` / `Admin1234!`).

| Service | Port | Notes |
|---------|------|--------|
| `pra-postgres` | **5435** | App metrics DB (`conversation_logs`) |
| `pra-grafana` | **3002** | Monitoring dashboard |
| `pra-streamlit` | **8502** | Chat UI (`Dockerfile`) |
| `pra-kestra` | **8085** | Optional ingestion flows |

### Dev alternative (host Python)

```powershell
# Example path (replace with your clone root):
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
. .\scripts\use_e_drive.ps1   # optional
uv sync
uv run pra-check-llm
docker compose stop streamlit   # free :8502 if container is up
uv run --no-sync pra-streamlit
uv run --no-sync pra-api        # Integrate API → http://localhost:8000/docs
uv run --no-sync python -m app.evaluate --retrieval-only
```

If `pra-streamlit` is missing after a fresh clone: `uv pip install -e . --no-deps`.

### Agent tools

Product and Streamlit toggle **Agent tools** (default on). Product also exposes **Generate answer**: turn it off for retrieval-only citations with no LLM call. The API equivalent is `POST /answer` with `"use_llm": false`.
Demo orders: `ZK-1001` (eligible), `ZK-1002` (ineligible), `ZK-1003` (need_more_info).

```powershell
python scripts\demo_part_c_tools.py
python scripts\demo_part_c_tools.py --with-llm
```

Compose Streamlit image must be rebuilt after code changes: `docker compose up -d --build streamlit`.

`scripts/use_e_drive.ps1` is optional (keeps uv/HF caches on the author’s `E:` drive). Skip it if you use default cache locations.


[↑ Contents](#table-of-contents)

---

## Architecture

![Live path architecture — Product → API → Agent/RAG → Hybrid RRF → LLM → Neon/Grafana](docs/images/architecture/live-path-infographic-v1.png)

**Live path (infographic):** User → Render Product → FastAPI Integrate → Agent tools / RAG → Hybrid RRF → Cerebras Gemma → citations + safety → Neon logs → Grafana Insights. Ops (Kestra / local Grafana) stays locked off the public face.

Technical graph (same system, code-oriented):

```mermaid
flowchart TD
    User["User"] --> Product["Render Product<br/>FastAPI + static chat · /docs"]
    Product --> Core["Agent + RAG core<br/>app/agent.py · app/llm.py"]
    ST["Streamlit<br/>secondary / local"] -.-> Core
    Core --> Tools["Order tools<br/>lookup_order · evaluate_refund"]
    Core --> Hybrid["Hybrid RRF<br/>minsearch + vector ranks"]
    Core --> LLM["LLM<br/>Cerebras Gemma"]
    Hybrid --> Policy["Policy KB<br/>data/refund_policy.md"]
    Kestra["Kestra ingest"] --> Policy
    LLM --> Safety["Safety guards<br/>app/safety.py"]
    Safety --> PG[("Neon / Postgres<br/>conversation_logs")]
    PG --> GF["Grafana Insights"]

    linkStyle default stroke:#5ecfc4,stroke-width:1.5px

    style User fill:#151c24,color:#e2e8f0,stroke:#5ecfc4
    style Product fill:#0f766e,color:#e2e8f0,stroke:#5eead4
    style Core fill:#1a2430,color:#e2e8f0,stroke:#5ecfc4
    style ST fill:#151c24,color:#e2e8f0,stroke:#64748b
    style Tools fill:#151c24,color:#e2e8f0,stroke:#5ecfc4
    style Hybrid fill:#0f766e,color:#e2e8f0,stroke:#5eead4
    style Policy fill:#1a2430,color:#e2e8f0,stroke:#5ecfc4
    style Kestra fill:#151c24,color:#e2e8f0,stroke:#64748b
    style LLM fill:#b45309,color:#e2e8f0,stroke:#fbbf24
    style Safety fill:#334155,color:#e2e8f0,stroke:#94a3b8
    style PG fill:#1e3a5f,color:#e2e8f0,stroke:#60a5fa
    style GF fill:#c2410c,color:#e2e8f0,stroke:#fb923c
```

**Request path (short):** question → Render Product / FastAPI → (optional tools) → hybrid RRF retrieval → LLM with citations → safety check → response + log row (+ optional 👍/👎) → Grafana. Streamlit remains a secondary client of the same core.


[↑ Contents](#table-of-contents)

---

## Decisions and trade-offs

- **Hybrid RRF over keyword-only:** keyword is strong on this small structured policy; vector ranks help paraphrases. RRF fuses both without a learned re-ranker. Trade-off: more moving parts than pure TF-IDF.
- **Cerebras Gemma over larger hosted models:** Zoomcamp-friendly cost/latency; shared OpenAI-compatible client across Render and Streamlit secrets. Trade-off: tool-calling quirks → deterministic tool fallback in [`app/agent.py`](app/agent.py).
- **Render as official public face:** Product + Integrate API + Insights on Render; Streamlit Cloud kept as a secondary prototype (may sleep). Trade-off: Blueprint + Docker images instead of one-click Streamlit-only.
- **Streamlit as secondary / ops UI:** course-era chat and local Compose `:8502` for demos and rubric evidence; official Product is the Render static UI + FastAPI. Trade-off: two public surfaces to maintain.
- **Neon for public logging:** local Compose keeps Postgres on `:5435`; public 👍 (Render / Streamlit Cloud) needs a reachable DB → Neon + `POSTGRES_SSLMODE=require`. Grafana Insights uses the same DB via `PRA_PG_*`.
- **Mock orders for tools:** `data/mock_orders.json` demos eligibility without a real OMS. Trade-off: not production order data.
- **In-memory TF-IDF vector ranks when pgvector is unavailable:** hybrid RRF still runs on free-tier / Cloud demos without a vector DB volume.


[↑ Contents](#table-of-contents)

---

## Project structure

```text
app/                 # Product API, Streamlit UI, RAG, hybrid RRF, agent tools, safety, eval
data/                # Policy, mock orders, eval sets + results
flows/               # Kestra ingestion
grafana/             # Provisioned dashboard + Postgres datasource
scripts/             # Demos and offline eval helpers
streamlit_app.py     # Streamlit Cloud / Compose entrypoint (secondary / local)
docker-compose.yaml  # postgres · grafana · streamlit · kestra
render.yaml          # Official Render Blueprint (Product · API · Grafana)
```


[↑ Contents](#table-of-contents)

---

## Screenshots

### Official Product (Render)

Live Product UI on Render — ZK-1001 eligible demo with grounded answer + citations.  
https://policy-refund-agent.onrender.com

![Render Product — ZK-1001](docs/images/product/render-product-zk1001.png)

### Hybrid retrieval (secondary — Streamlit)

\* *Secondary Streamlit prototype (dev/demo)* — not the official Product UI.  
Live: [Streamlit Cloud](https://policy-refund-agent.streamlit.app/) · local Compose serves the same UI on `:8502`

Hybrid RAG chat (keyword + vector **RRF**). Caption shows `retrieval: hybrid` and per-section RRF scores.

![Streamlit hybrid chat](docs/images/hybrid/hybrid_ui.png)

### Monitoring (Postgres → Grafana + feedback)

Empty dashboard → live ask with 👍 → metrics update (`conversation_logs`).  
[Public Insights (Grafana on Render)](https://policy-refund-agent-grafana.onrender.com/d/pra-agent-monitoring/pra-agent-monitoring?orgId=1) · local Ops runs Grafana on `:3002` and Streamlit on `:8502`

| Step | Description |
|------|-------------|
| **1 · Before** | Cold start — Questions `0`, panels empty |
| **2 · UI** | Ask + citations + **Feedback recorded: helpful 👍** |
| **3 · After** | Latency / citations / **Thumbs up** populated |

![Grafana before (cold start)](docs/images/monitoring/grafana-before.png)

![Streamlit ask + thumbs-up feedback](docs/images/monitoring/streamlit-feedback.png)

![Grafana after live ask + feedback](docs/images/monitoring/grafana-after.png)

Optional — same dashboard with Grafana datasource pointed at **Neon** (public `conversation_logs`):

![Grafana after public traffic on Neon](docs/images/monitoring/grafana-neon-after.png)

### Docker Compose (Streamlit in container — local ops)

Compose stack on `:8502` — refund Q&A + citations + 👍 (`docker compose up -d streamlit`). Local ops/dev only.

![Streamlit Compose — refund + feedback](docs/images/compose/streamlit-compose-refund.png)

### Ops 🔒 (password-gated)

Hub corner **Ops 🔒** — password gate ([`docs/OPS_PASSWORD.md`](docs/OPS_PASSWORD.md)) that only prints local operator URLs (Grafana `:3002`, Kestra `:8085`, Compose command). Kestra and local Postgres are never exposed publicly; the Postgres host is redacted in the screenshot.

![Ops unlock gate — shared password prompt](docs/images/ops/ops-unlock-gate.png)

![Ops unlocked — local operator guidance with Postgres host redacted](docs/images/ops/ops-unlocked-guidance.png)

### Secondary prototype (Streamlit Cloud)

Course-era / bonus evidence — **not** the official Product. App may sleep on free tier.  
https://policy-refund-agent.streamlit.app/

Agent tools on; demo order `ZK-1001` → **eligible**; 👍 via Neon Postgres when secrets are set.

| Shot | File |
|------|------|
| UI only (no manage-app log) | [`docs/images/cloud/streamlit-cloud-zk1001-ui.png`](docs/images/cloud/streamlit-cloud-zk1001-ui.png) |
| UI + Cloud manage-app log | [`docs/images/cloud/streamlit-cloud-zk1001.png`](docs/images/cloud/streamlit-cloud-zk1001.png) |
| Korean question (multilingual) | [`docs/images/cloud/streamlit-cloud-zk1001-ko.png`](docs/images/cloud/streamlit-cloud-zk1001-ko.png) |

![Streamlit Cloud (secondary) — ZK-1001 (UI)](docs/images/cloud/streamlit-cloud-zk1001-ui.png)

![Streamlit Cloud (secondary) — ZK-1001 (with deploy log)](docs/images/cloud/streamlit-cloud-zk1001.png)

![Streamlit Cloud (secondary) — Korean ZK-1001](docs/images/cloud/streamlit-cloud-zk1001-ko.png)

`language: Korean` · agent tools · citations — query rewriting + answer-in-user-language.


[↑ Contents](#table-of-contents)

---

## Evaluation criteria

Maps this repo to the [LLM Zoomcamp project rubric](https://github.com/DataTalksClub/llm-zoomcamp/blob/main/project.md) (0–2 points per row unless noted). Peer reviewers can follow the **Evidence** links.

Rows marked **capstone extra** are **implemented** features that are not fixed-score criteria; they are candidates for the rubric’s **optional bonus (max +3, reviewer decides)** — not unfinished work.

| Criterion | Target | Evidence in this repo |
|-----------|--------|------------------------|
| **Problem description** | 2 | [Problem](#problem) — Zakard Shop refund support; synthetic KB in [`data/refund_policy.md`](data/refund_policy.md) |
| **Retrieval flow** | 2 | KB + LLM: [`app/hybrid.py`](app/hybrid.py) (keyword + vector **RRF**) → [`app/llm.py`](app/llm.py) `answer_question` with citations |
| **Retrieval evaluation** | 2 | Multiple strategies compared (`keyword` / `vector` / `hybrid`); **hybrid** selected. Harness: [`app/evaluate.py`](app/evaluate.py), cases [`data/eval_data.json`](data/eval_data.json), 3-way script [`scripts/m2_4_eval_3way.py`](scripts/m2_4_eval_3way.py). Tracked smoke summary: [`data/eval_results_judge_smoke.json`](data/eval_results_judge_smoke.json) (Hit@1/3/5 **100 %**, MRR **1.0**, n=3). Full local runs write `data/eval_results.json` (gitignored — regenerate with `uv run --no-sync python -m app.evaluate --retrieval-only`) |
| **LLM evaluation** | 2 | Compared **two system prompts** on the same retrieval context: **A** minimal grounded vs **B** production `SUPPORT_SYSTEM_PROMPT` (structured + safety). Judge means **A≈4.73** / **B=5.00** (n=5) → **selected B**. Tracked evidence: [`data/eval_llm_approaches.json`](data/eval_llm_approaches.json), script [`scripts/eval_llm_approaches.py`](scripts/eval_llm_approaches.py). Same-model judge (Gemma) = relative signal, not absolute truth |
| **Interface** | 2 | Official: Render Product chat + hub — https://policy-refund-agent.onrender.com ([Screenshots → Official Product](#official-product-render)). Secondary / local: Streamlit chat + citations + 👍/👎 — [`app/streamlit_ui.py`](app/streamlit_ui.py), `pra-streamlit`, Compose `:8502` |
| **Ingestion pipeline** | 2 | Kestra flow [`flows/ingest_policy.yaml`](flows/ingest_policy.yaml) — `docker compose up -d kestra-postgres kestra` → `http://localhost:8085` |
| **Monitoring** | 2 | Postgres / Neon `conversation_logs` + feedback + Grafana **7 panels** — Insights on Render; local Ops `:3002` — [`app/database.py`](app/database.py), [`grafana/dashboards/pra_agent_monitoring.json`](grafana/dashboards/pra_agent_monitoring.json) — [Screenshots](#screenshots) |
| **Containerization** | 2 | `docker compose up -d postgres grafana streamlit` — [`Dockerfile`](Dockerfile), [`docker-compose.yaml`](docker-compose.yaml); Render Blueprint [`render.yaml`](render.yaml) |
| **Reproducibility** | 2 | [Quick start](#quick-start), [Configuration](#configuration), `.env.example`, `requirements.txt` / `pyproject.toml` (Python ≥ 3.12), policy + eval data in `data/` |
| **Best practice: hybrid search** | +1 | Default `PRA_RETRIEVAL_METHOD=hybrid` — [`app/hybrid.py`](app/hybrid.py) |
| **Best practice: re-ranking** | +1 | **RRF** fusion of keyword + vector ranked lists (same module) |
| **Best practice: query rewriting** | +1 | [`app/query.py`](app/query.py) `prepare_search_query` — language detect + English search query for multilingual input |
| **Agent / tools** (capstone extra) | optional bonus (max +3, reviewer decides) | Not a fixed rubric row — candidate for the official discretionary extra points. Implemented: [`app/tools.py`](app/tools.py) + [`app/agent.py`](app/agent.py) — mock `lookup_order` / `evaluate_refund` (`data/mock_orders.json`); demo [`scripts/demo_part_c_tools.py`](scripts/demo_part_c_tools.py); Product / Streamlit demo `ZK-1001` |
| **Safety** (capstone extra) | optional bonus (max +3, reviewer decides) | Same optional pool as above (implemented, not unfinished). [`app/safety.py`](app/safety.py) — injection block + unanswerable/OOS CS fallback; demo [`scripts/demo_part_d_safety.py`](scripts/demo_part_d_safety.py) |
| **Bonus: cloud deployment** | +2 | Official: Render ([`docs/RENDER.md`](docs/RENDER.md)); secondary prototype: https://policy-refund-agent.streamlit.app/ — [Cloud deployment](#cloud-deployment); screenshots under [Screenshots → Secondary prototype](#secondary-prototype-streamlit-cloud) |

### Quick verification commands

```powershell
# Example path (replace with your clone root):
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
. .\scripts\use_e_drive.ps1   # optional
uv run --no-sync python -m app.evaluate --retrieval-only   # retrieval metrics
python scripts\demo_part_c_tools.py                          # agent tools (3 decisions)
python scripts\demo_part_d_safety.py                         # unanswerable + injection (6 cases)
python scripts\eval_llm_approaches.py                        # prompt A vs B (LLM eval)
docker compose up -d postgres grafana streamlit              # full stack
```


[↑ Contents](#table-of-contents)

---

## Cloud deployment

### Official: Render (Product + Insights + Integrate)

Primary public face — Product UI, Integrate API (`/health` `/search` `/answer` `/docs`), and Grafana Insights.  
Blueprint: [`render.yaml`](render.yaml). Full walkthrough: [`docs/RENDER.md`](docs/RENDER.md).

1. Render Dashboard → **New → Blueprint** → this repo / `main`.
2. Fill **Dashboard secrets** (`sync: false` — never commit real values). Prefills like `POSTGRES_PORT=5432` / `POSTGRES_SSLMODE=require` / Cerebras model are already in the Blueprint.

**Product** service `policy-refund-agent` (and Integrate API `policy-refund-agent-api` if present) — Environment:

```env
CEREBRAS_API_KEY=your-cerebras-key
POSTGRES_HOST=ep-xxxx.region.aws.neon.tech
POSTGRES_DB=neondb
POSTGRES_USER=neondb_owner
POSTGRES_PASSWORD=your-neon-password
PRA_OPS_PASSWORD=your-ops-unlock-password
```

Use the **same Neon** as below. On Product only: add `PRA_OPS_PASSWORD` via **Edit → Add** if the row is missing ([`docs/OPS_PASSWORD.md`](docs/OPS_PASSWORD.md)). Wrong service: `policy-refund-agent-api` — Ops 🔒 does not use that env.

**Insights** service `policy-refund-agent-grafana` — Environment:

```env
GF_SECURITY_ADMIN_PASSWORD=your-grafana-admin-password
PRA_PG_HOST=ep-xxxx.region.aws.neon.tech:5432
PRA_PG_USER=neondb_owner
PRA_PG_PASSWORD=your-neon-password
PRA_PG_DB=neondb
```

(`PRA_PG_HOST` includes **`:5432`**. Same Neon DB as Product `POSTGRES_*`.)

3. Wait until services are **Live / Healthy**. Smoke: Product `/`, API `/health` + `/docs`, Grafana dashboard.
4. GitHub **About → Homepage** → Render Product URL. Local Grafana `:3002` and Compose Streamlit `:8502` stay **Ops / dev**.

**Ops 🔒** is password-locked (not published). Peer reviewers use Product / Insights / Integrate only — unlock returns **local-only** guidance after `PRA_OPS_PASSWORD` matches. Never put that password in README or git.

### Secondary prototype: Streamlit Community Cloud

Course-era demo and rubric bonus evidence only — **not** the official product URL. May sleep on free tier.  
Screenshots: [Screenshots → Secondary prototype](#secondary-prototype-streamlit-cloud).

**Secondary live:** https://policy-refund-agent.streamlit.app/

How to redeploy (secondary):

1. Push this repo to GitHub (`https://github.com/zakard114/policy-refund-agent`).
2. Open [share.streamlit.io](https://share.streamlit.io/) → **New app**.
3. Repository `zakard114/policy-refund-agent`, branch `main`, **Main file path** `streamlit_app.py`.
4. **Advanced settings → Secrets**: paste TOML from [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) and set a real `CEREBRAS_API_KEY`. Python **3.12**.
5. Deploy.

Notes:

- **Neon Postgres (optional):** enable Streamlit Cloud 👍/👎 by adding `POSTGRES_*` + `POSTGRES_SSLMODE=require` to Streamlit Secrets (see [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example)). Point local Grafana at the same DB with `PRA_PG_*` in `.env`, then `docker compose up -d grafana`.
- Without Postgres secrets, Q&A and Citations still work; **👍/👎 feedback is unavailable on Streamlit Cloud**.
- Hybrid RRF uses **in-memory TF-IDF** vector ranks when pgvector is unavailable.
- Full monitoring UI: Grafana Insights on Render, or local Ops Grafana (`:3002`) when the app DB is Neon.

### Neon setup (public thumbs + shared Grafana DB)

1. Create a free project at [console.neon.tech](https://console.neon.tech).
2. Copy connection fields (host, port `5432`, database, user, password). Prefer the **pooled** connection host if shown.
3. For the **Streamlit Cloud** secondary app → **Settings → Secrets** — append:

```toml
POSTGRES_HOST = "ep-xxxx.region.aws.neon.tech"
POSTGRES_PORT = "5432"
POSTGRES_DB = "neondb"
POSTGRES_USER = "neondb_owner"
POSTGRES_PASSWORD = "your-neon-password"
POSTGRES_SSLMODE = "require"
```

4. **Reboot** the Streamlit app. Ask `Can I refund order ZK-1001?` → 👍/👎 should appear (not “Feedback unavailable”).
5. (Optional) Local Grafana on Neon — in project `.env`:

```env
PRA_PG_HOST=ep-xxxx.region.aws.neon.tech:5432
PRA_PG_USER=neondb_owner
PRA_PG_PASSWORD=your-neon-password
PRA_PG_DB=neondb
PRA_PG_SSLMODE=require
```

Then: `docker compose up -d grafana` and open `http://localhost:3002` (admin/admin). Re-take monitoring screenshots if panels update from public traffic.


[↑ Contents](#table-of-contents)

---

## Troubleshooting

If Grafana or containers stop responding:

1. **`docker info` / `docker ps` hangs** — this is a Docker engine (WSL2) hang, not a Grafana-specific issue. Quit Docker Desktop → `wsl --shutdown` → restart Desktop → wait for the green "Engine running" indicator.
2. Once the engine is back:

```powershell
# Example path (replace with your clone root):
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
docker compose up -d
```

3. Confirm Postgres shows `healthy`, then open `http://localhost:3002`.

Port map: `:3000` / `:3001` belong to other project stacks. **PRA uses `:3002` only**.

Detailed symptoms, root causes, and a step-by-step checklist: [`docs/DOCKER_TROUBLESHOOT.md`](docs/DOCKER_TROUBLESHOOT.md).


[↑ Contents](#table-of-contents)

---

## License

- **Code:** MIT
- **Policy text:** synthetic Zakard Shop document in `data/refund_policy.md`, created for this demo

[↑ Contents](#table-of-contents)
