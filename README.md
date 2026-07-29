# Policy & Refund Support Agent

**Grounded policy RAG for e-commerce refund support** — retrieve policy clauses, answer with citations, refuse safely when context is missing, and measure quality with an offline eval harness.

---

## Problem

This project answers questions and evaluates refund eligibility **from the Zakard Shop refund policy document** (`data/refund_policy.md`), not from general LLM knowledge.

Support teams need answers **strictly from policy documents** and consistent refund decisions. This app:

1. Retrieves policy clauses (keyword search + citations)
2. Supports multilingual questions (translate-to-English for search, answer in the user's language)
3. Returns safe fallbacks when context is insufficient
4. Measures quality offline (Hit Rate, Top-1, Fact Pass Rate)

### Knowledge base

| Item | Detail |
|------|--------|
| Source | Synthetic **Zakard Shop** refund & return policy |
| File | [`data/refund_policy.md`](data/refund_policy.md) |
| License | Original text written for this project (demo use); not scraped from a live retailer |

---

## Status

**Capstone-ready (local)** — RAG + hybrid RRF + Streamlit/Docker + agent tools + safety guards + monitoring. See [Evaluation criteria](#evaluation-criteria) for rubric mapping.

---

## Configuration

| Role | Provider | Variables |
|------|----------|-----------|
| App LLM | **Gemma on Cerebras** (OpenAI-compatible) | `PRA_LLM_BACKEND=cerebras`, `CEREBRAS_*` in `.env` or shared workspace LLM env |

```powershell
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
. .\scripts\use_e_drive.ps1
copy .env.example .env
uv sync
uv run pra-check-llm
```

---

## Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- [Docker Desktop](https://www.docker.com/) (disk location on **E:**)
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
| `pra-grafana` | **3002** | Monitoring — not `:3000` / `:3001` (other stacks) |
| `pra-streamlit` | **8502** | Chat UI (`Dockerfile`) |
| `pra-kestra` | **8085** | Optional ingest flows |

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

If `pra-streamlit` is missing after a fresh clone (and you prefer not to full-sync): `uv pip install -e . --no-deps`.

**Agent tools (Part 6-1):** Streamlit sidebar toggle *Agent tools* (default on). Demo orders `ZK-1001` (eligible), `ZK-1002` (ineligible), `ZK-1003` (need_more_info).

```powershell
$env:PYTHONPATH = "E:\IT_SPACES\AI\Projects\llm\policy-refund-agent"
python scripts\demo_part_c_tools.py
python scripts\demo_part_c_tools.py --with-llm
```

Compose Streamlit image must be rebuilt after code changes: `docker compose up -d --build streamlit`.

All data and Docker volumes use **E:** paths — see [`AGENTS.md`](AGENTS.md). Grafana troubleshooting: [`docs/DOCKER_TROUBLESHOOT.md`](docs/DOCKER_TROUBLESHOOT.md).

---

## Screenshots

### Hybrid retrieval

Hybrid RAG chat (keyword + vector **RRF**) — http://localhost:8502  
Caption shows `retrieval: hybrid` and per-section RRF scores.

![Streamlit hybrid chat](docs/images/hybrid/hybrid_ui.png)

### Monitoring (Postgres → Grafana + feedback)

Empty dashboard → live ask with 👍 → metrics update (`conversation_logs`).  
Grafana: http://localhost:3002 · Streamlit: http://localhost:8502

| Step | Shot |
|------|------|
| **1 · Before** | Cold start — Questions `0`, panels empty |
| **2 · UI** | Ask + citations + **Feedback recorded: helpful 👍** |
| **3 · After** | Latency / citations / **Thumbs up** populated |

![Grafana before (cold start)](docs/images/monitoring/grafana-before.png)

![Streamlit ask + thumbs-up feedback](docs/images/monitoring/streamlit-feedback.png)

![Grafana after live ask + feedback](docs/images/monitoring/grafana-after.png)

### Docker Compose (Streamlit in container)

Compose stack on `:8502` — refund Q&A + citations + 👍 (`docker compose up -d streamlit`).

![Streamlit Compose — refund + feedback](docs/images/compose/streamlit-compose-refund.png)

Stable aliases (hybrid era): `docs/images/streamlit-chat.png`, `docs/images/grafana-monitoring.png`.  
Index / archive: [`docs/images/README.md`](docs/images/README.md).

---

## Evaluation criteria

Maps this repo to the [LLM Zoomcamp project rubric](https://github.com/DataTalksClub/llm-zoomcamp/blob/main/project.md) (0–2 points per row unless noted). Peer reviewers can follow the **Evidence** links.

| Criterion | Target | Evidence in this repo |
|-----------|--------|------------------------|
| **Problem description** | 2 | [Problem](#problem) — Zakard Shop refund support; synthetic KB in [`data/refund_policy.md`](data/refund_policy.md) |
| **Retrieval flow** | 2 | KB + LLM: [`app/hybrid.py`](app/hybrid.py) (keyword + vector **RRF**) → [`app/llm.py`](app/llm.py) `answer_question` with citations |
| **Retrieval evaluation** | 2 | Multiple strategies compared (`keyword` / `vector` / `hybrid`); **hybrid** selected. [`app/evaluate.py`](app/evaluate.py), [`data/eval_data.json`](data/eval_data.json), results [`data/eval_results.json`](data/eval_results.json) — Hit@1/3/5 **100%**, MRR **1.0** (20 answerable, retrieval-only). Scripts: [`scripts/m2_4_eval_3way.py`](scripts/m2_4_eval_3way.py) |
| **LLM evaluation** | 1–2 | [`app/judge.py`](app/judge.py) LLM-as-judge; smoke [`data/eval_results_judge_smoke.json`](data/eval_results_judge_smoke.json). Full multi-prompt sweep not finalized — judge path exists for extension |
| **Interface** | 2 | Streamlit chat + citations + 👍/👎 — [`app/streamlit_ui.py`](app/streamlit_ui.py), `pra-streamlit`, Compose `:8502` — [Screenshots](#screenshots) |
| **Ingestion pipeline** | 2 | Kestra flow [`flows/ingest_policy.yaml`](flows/ingest_policy.yaml) — `docker compose up -d kestra-postgres kestra` → http://localhost:8085 |
| **Monitoring** | 2 | Postgres `conversation_logs` + Streamlit feedback + Grafana **7 panels** — [`app/database.py`](app/database.py), [`grafana/dashboards/pra_agent_monitoring.json`](grafana/dashboards/pra_agent_monitoring.json), `:3002` — [Screenshots](#screenshots) |
| **Containerization** | 2 | `docker compose up -d postgres grafana streamlit` — [`Dockerfile`](Dockerfile), [`docker-compose.yaml`](docker-compose.yaml) |
| **Reproducibility** | 2 | [Quick start](#quick-start), [Configuration](#configuration), `.env.example`, `uv.lock` / `pyproject.toml` (Python ≥3.12), policy + eval data in `data/` |
| **Best practice: hybrid search** | +1 | Default `PRA_RETRIEVAL_METHOD=hybrid` — [`app/hybrid.py`](app/hybrid.py) |
| **Best practice: re-ranking** | +1 | **RRF** fusion of keyword + vector ranked lists (same module) |
| **Best practice: query rewriting** | +1 | [`app/query.py`](app/query.py) `prepare_search_query` — language detect + English search query for multilingual input |
| **Agent / tools** (capstone extra) | — | [`app/tools.py`](app/tools.py) + [`app/agent.py`](app/agent.py) — mock `lookup_order` / `evaluate_refund` (`data/mock_orders.json`); demo `scripts/demo_part_c_tools.py` |
| **Safety** (capstone extra) | — | [`app/safety.py`](app/safety.py) — injection block + unanswerable/OOS CS fallback; `scripts/demo_part_d_safety.py` |

### Gaps (honest)

| Item | Status |
|------|--------|
| Cloud deployment | Not deployed (local Docker + host Streamlit only) |
| Full LLM judge on all 26 eval cases | Smoke run only (`eval_results_judge_smoke.json`); extend with `python -m app.evaluate` (full mode) |
| Public git remote | Local workspace on **E:**; push when submission repo is ready |

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

## Troubleshooting (문제해결)

Grafana가 안 열리거나 컨테이너가 한꺼번에 멈출 때:

1. **`docker info` / `docker ps`가 멈추면** → 개별 Grafana 문제가 아니라 **Docker 엔진(WSL2) hang**. Docker Desktop 종료 → `wsl --shutdown` → Desktop 재실행 → 초록불 대기.
2. 엔진이 살아난 뒤:

```powershell
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
docker compose up -d
```

3. Postgres가 `healthy`인지 확인한 다음 **http://localhost:3002** 접속.

포트 구분: `:3000` / `:3001`은 다른 프로젝트 Grafana. **PRA는 `:3002`만**.

자세한 증상·원인·체크리스트: [`docs/DOCKER_TROUBLESHOOT.md`](docs/DOCKER_TROUBLESHOOT.md).

---

## License

- **Code:** TBD (MIT planned)
- **Policy text:** synthetic Zakard Shop document in `data/refund_policy.md`, created for this demo
