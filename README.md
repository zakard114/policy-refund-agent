# Policy & Refund Support Agent

**Grounded policy RAG for e-commerce refund support** — retrieve policy clauses, answer with citations, refuse safely when context is missing, and measure quality with an offline eval harness.

---

## Problem

This project answers questions and evaluates refund eligibility **from the Zakard Shop refund policy document** (`data/refund_policy.md`), not from general LLM knowledge.

Support teams need answers **strictly from policy documents** and consistent refund decisions. This app:

1. Retrieves policy clauses via hybrid search (keyword + vector RRF) with citations
2. Supports multilingual questions (translate-to-English for search, answer in the user's language)
3. Returns safe fallbacks when context is insufficient or prompt injection is detected
4. Evaluates refund eligibility with mock order tools (`lookup_order` / `evaluate_refund`)
5. Measures quality offline (Hit Rate, MRR, LLM-as-judge), including multilingual questions (Korean / Spanish / French) with English glosses in [`data/eval_data.json`](data/eval_data.json)

### Knowledge base

| Item | Detail |
|------|--------|
| Source | Synthetic **Zakard Shop** refund & return policy |
| File | [`data/refund_policy.md`](data/refund_policy.md) |
| License | Original text written for this project (demo use); not scraped from a live retailer |

---

## Status

**Status:** Capstone-ready — RAG + hybrid RRF + Streamlit (local Docker **and** [Streamlit Community Cloud](#cloud-deployment)) + agent tools + safety guards + Kestra ingestion + Grafana monitoring. See [Evaluation criteria](#evaluation-criteria) for rubric mapping.

---

## Configuration

| Role | Provider | Variables |
|------|----------|-----------|
| App LLM | **Gemma on Cerebras** (OpenAI-compatible) | `PRA_LLM_BACKEND=cerebras`, `CEREBRAS_*` in `.env` |

```powershell
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
. .\scripts\use_e_drive.ps1
copy .env.example .env        # set CEREBRAS_API_KEY inside
uv sync
uv run pra-check-llm
```

---

## Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- [Docker Desktop](https://www.docker.com/)
- LLM API key (Cerebras / OpenAI-compatible)

---

## Quick start

**Recommended:** Postgres + Grafana + Streamlit via Compose.

```powershell
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
. .\scripts\use_e_drive.ps1
copy .env.example .env   # if missing — set CEREBRAS_API_KEY
docker compose up -d postgres grafana streamlit
docker compose ps
# Streamlit http://localhost:8502 · Grafana http://localhost:3002 (admin/admin)
# Postgres host :5435 (from Streamlit container use host name `postgres`)
```

Optional orchestration UI: `docker compose up -d kestra-postgres kestra` → http://localhost:8085 (`admin@kestra.io` / `Admin1234!`).

| Service | Port | Notes |
|---------|------|--------|
| `pra-postgres` | **5435** | App metrics DB (`conversation_logs`) |
| `pra-grafana` | **3002** | Monitoring dashboard |
| `pra-streamlit` | **8502** | Chat UI (`Dockerfile`) |
| `pra-kestra` | **8085** | Optional ingestion flows |

### Dev alternative (host Python)

```powershell
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
. .\scripts\use_e_drive.ps1
uv sync
uv run pra-check-llm
docker compose stop streamlit   # free :8502 if container is up
uv run --no-sync pra-streamlit
uv run --no-sync python -m app.evaluate --retrieval-only
```

If `pra-streamlit` is missing after a fresh clone: `uv pip install -e . --no-deps`.

### Agent tools

Streamlit sidebar toggle **Agent tools** (default on).
Demo orders: `ZK-1001` (eligible), `ZK-1002` (ineligible), `ZK-1003` (need_more_info).

```powershell
python scripts\demo_part_c_tools.py
python scripts\demo_part_c_tools.py --with-llm
```

Compose Streamlit image must be rebuilt after code changes: `docker compose up -d --build streamlit`.

All data and Docker volumes use **E:** paths — see [`AGENTS.md`](AGENTS.md).

---

## Screenshots

### Hybrid retrieval

Hybrid RAG chat (keyword + vector **RRF**) — http://localhost:8502
Caption shows `retrieval: hybrid` and per-section RRF scores.

![Streamlit hybrid chat](docs/images/hybrid/hybrid_ui.png)

### Monitoring (Postgres → Grafana + feedback)

Empty dashboard → live ask with 👍 → metrics update (`conversation_logs`).
Grafana: http://localhost:3002 · Streamlit: http://localhost:8502

| Step | Description |
|------|-------------|
| **1 · Before** | Cold start — Questions `0`, panels empty |
| **2 · UI** | Ask + citations + **Feedback recorded: helpful 👍** |
| **3 · After** | Latency / citations / **Thumbs up** populated |

![Grafana before (cold start)](docs/images/monitoring/grafana-before.png)

![Streamlit ask + thumbs-up feedback](docs/images/monitoring/streamlit-feedback.png)

![Grafana after live ask + feedback](docs/images/monitoring/grafana-after.png)

### Docker Compose (Streamlit in container)

Compose stack on `:8502` — refund Q&A + citations + 👍 (`docker compose up -d streamlit`).

![Streamlit Compose — refund + feedback](docs/images/compose/streamlit-compose-refund.png)

---

## Evaluation criteria

Maps this repo to the [LLM Zoomcamp project rubric](https://github.com/DataTalksClub/llm-zoomcamp/blob/main/project.md) (0–2 points per row unless noted). Peer reviewers can follow the **Evidence** links.

| Criterion | Target | Evidence in this repo |
|-----------|--------|------------------------|
| **Problem description** | 2 | [Problem](#problem) — Zakard Shop refund support; synthetic KB in [`data/refund_policy.md`](data/refund_policy.md) |
| **Retrieval flow** | 2 | KB + LLM: [`app/hybrid.py`](app/hybrid.py) (keyword + vector **RRF**) → [`app/llm.py`](app/llm.py) `answer_question` with citations |
| **Retrieval evaluation** | 2 | Multiple strategies compared (`keyword` / `vector` / `hybrid`); **hybrid** selected. [`app/evaluate.py`](app/evaluate.py), [`data/eval_data.json`](data/eval_data.json), results [`data/eval_results.json`](data/eval_results.json) — Hit@1/3/5 **100 %**, MRR **1.0** (20 answerable). Scripts: [`scripts/m2_4_eval_3way.py`](scripts/m2_4_eval_3way.py) |
| **LLM evaluation** | 2 | [`app/judge.py`](app/judge.py) LLM-as-judge with stored outputs in [`data/eval_results.json`](data/eval_results.json). Full 26-case run completed via [`app/evaluate.py`](app/evaluate.py) — Fact Pass Rate **100 %** (20/20 answerable), LLM Judge mean **4.97/5.00** across 26 cases |
| **Interface** | 2 | Streamlit chat + citations + 👍/👎 — [`app/streamlit_ui.py`](app/streamlit_ui.py), `pra-streamlit`, Compose `:8502` — [Screenshots](#screenshots) |
| **Ingestion pipeline** | 2 | Kestra flow [`flows/ingest_policy.yaml`](flows/ingest_policy.yaml) — `docker compose up -d kestra-postgres kestra` → http://localhost:8085 |
| **Monitoring** | 2 | Postgres `conversation_logs` + Streamlit feedback + Grafana **7 panels** — [`app/database.py`](app/database.py), [`grafana/dashboards/pra_agent_monitoring.json`](grafana/dashboards/pra_agent_monitoring.json), `:3002` — [Screenshots](#screenshots) |
| **Containerization** | 2 | `docker compose up -d postgres grafana streamlit` — [`Dockerfile`](Dockerfile), [`docker-compose.yaml`](docker-compose.yaml) |
| **Reproducibility** | 2 | [Quick start](#quick-start), [Configuration](#configuration), `.env.example`, `uv.lock` / `pyproject.toml` (Python ≥ 3.12), policy + eval data in `data/` |
| **Best practice: hybrid search** | +1 | Default `PRA_RETRIEVAL_METHOD=hybrid` — [`app/hybrid.py`](app/hybrid.py) |
| **Best practice: re-ranking** | +1 | **RRF** fusion of keyword + vector ranked lists (same module) |
| **Best practice: query rewriting** | +1 | [`app/query.py`](app/query.py) `prepare_search_query` — language detect + English search query for multilingual input |
| **Agent / tools** (capstone extra) | — | [`app/tools.py`](app/tools.py) + [`app/agent.py`](app/agent.py) — mock `lookup_order` / `evaluate_refund` (`data/mock_orders.json`); demo [`scripts/demo_part_c_tools.py`](scripts/demo_part_c_tools.py) |
| **Safety** (capstone extra) | — | [`app/safety.py`](app/safety.py) — injection block + unanswerable/OOS CS fallback; [`scripts/demo_part_d_safety.py`](scripts/demo_part_d_safety.py) |
| **Bonus: cloud deployment** | +2 | Streamlit Community Cloud — see [Cloud deployment](#cloud-deployment). Main file: [`streamlit_app.py`](streamlit_app.py); deps: [`requirements.txt`](requirements.txt); secrets template: [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) |

### Quick verification commands

```powershell
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
. .\scripts\use_e_drive.ps1
uv run --no-sync python -m app.evaluate --retrieval-only   # retrieval metrics
python scripts\demo_part_c_tools.py                          # agent tools (3 decisions)
python scripts\demo_part_d_safety.py                         # unanswerable + injection (6 cases)
docker compose up -d postgres grafana streamlit              # full stack
```

---

## Cloud deployment

Public demo on **Streamlit Community Cloud** (bonus criterion).

1. Push this repo to GitHub (already: `https://github.com/zakard114/policy-refund-agent`).
2. Open [share.streamlit.io](https://share.streamlit.io/) → **New app**.
3. Select repository `zakard114/policy-refund-agent`, branch `main`, **Main file path** `streamlit_app.py`.
4. In **Advanced settings → Secrets**, paste TOML from [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) and set a real `CEREBRAS_API_KEY`.
5. Deploy. After it is live, put the app URL here:

**Live app:** https://policy-refund-agent.streamlit.app/

Notes:

- Without Postgres secrets, Q&A still works: hybrid RRF uses **in-memory TF-IDF** vector ranks when pgvector is unavailable; conversation logging fails soft.
- Full monitoring (Grafana + `conversation_logs`) remains on the local Docker stack (`:3002`).

---

## Troubleshooting

If Grafana or containers stop responding:

1. **`docker info` / `docker ps` hangs** — this is a Docker engine (WSL2) hang, not a Grafana-specific issue. Quit Docker Desktop → `wsl --shutdown` → restart Desktop → wait for the green "Engine running" indicator.
2. Once the engine is back:

```powershell
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
docker compose up -d
```

3. Confirm Postgres shows `healthy`, then open **http://localhost:3002**.

Port map: `:3000` / `:3001` belong to other project stacks. **PRA uses `:3002` only**.

Detailed symptoms, root causes, and a step-by-step checklist: [`docs/DOCKER_TROUBLESHOOT.md`](docs/DOCKER_TROUBLESHOOT.md).

---

## License

- **Code:** MIT
- **Policy text:** synthetic Zakard Shop document in `data/refund_policy.md`, created for this demo
