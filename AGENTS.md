# Agent instructions — policy-refund-agent

**Policy & Refund Support Agent** — grounded RAG for e-commerce refund policy Q&A and eligibility support.

## Concept

E-commerce support agent that:

- Answers policy questions with **mandatory citations** (grounded RAG)
- Evaluates refund requests via **agent tools** and policy rules
- Refuses out-of-scope / prompt-injection / missing-context cases safely
- Logs decisions for **offline eval** and **online monitoring**

## Data

- Primary corpus: `data/refund_policy.md` (synthetic **Zakard Shop** refund policy, English).
- Do **not** use unrelated FAQ dumps as the knowledge base.

## Coding from tutor / Gemini pastes

When zakard pastes sample code or steps:

1. **Validate only** — say whether the code is correct/complete for this project.
2. **Do not** auto-rewrite, “improve”, or replace working files unless zakard explicitly asks to apply/fix/implement.
3. If asked to apply, implement **what they provided** (minimal fixes only if it otherwise cannot run, and call those out).

## Gemini handoff (mandatory)

While learning / building this project:

- **Do not** invent the next tutor lesson, invent Gemini instructions, or decide Gemini’s curriculum on your own.
- When a step needs Gemini (Why/What/How, Part briefing, concept teaching packet): **report to zakard** and tell them to **instruct Gemini** — include a short paste-ready message if helpful.
- Cursor focuses on: apply-on-request, validate, debug, PHASE_LOG, E:/Docker/path issues.

## Hard rules

1. **Do not** use unrelated course FAQ dumps as the knowledge base.
2. **Do not** bulk-paste from sibling project `dtc-podcast-rag` — patterns only, new domain code.
3. **Do not** use `dtc` in project or product naming.
4. External patterns may be **adapted** with clear refactoring — not notebook dumps.
5. **Do not** commit secrets or large model weights.

## Stack (target)

| Layer | Tech |
|-------|------|
| RAG | minsearch / sqlitesearch / **pgvector**, hybrid (RRF), rerank, query rewrite |
| Agent | function-calling loop, policy + order tools |
| Orchestration | **Kestra** ingest flows |
| Eval | ground truth CSV, Hit Rate, MRR, LLM-as-judge |
| UI | **Streamlit** |
| Monitoring | PostgreSQL + **Grafana**, user feedback |
| Runtime | Python 3.12+, `uv`, Docker Compose on **E:** |

## User environment

- Windows; workspace `E:\IT_SPACES\AI\`
- **Storage policy:** all caches, data, models, Docker volumes on **E:** — never `C:\Users\...`
- Before `uv sync`: `. .\scripts\use_e_drive.ps1`

### E: path map

| What | Path |
|------|------|
| Project root | `E:\IT_SPACES\AI\Projects\llm\policy-refund-agent\` |
| Policy docs / chunks | `...\data\` |
| Docker state | `...\docker\` |
| Shared uv/HF cache | `E:\IT_SPACES\AI\.cache\` |

## Docker Compose

```powershell
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
docker compose up -d
```

Services: Postgres (+ pgvector), Grafana (`:3002`), Kestra (`:8085`) — volumes on E: (see compose notes for named volumes).

**Grafana down / `docker ps` hangs:** treat as Docker engine (WSL2) hang first — Quit Desktop → `wsl --shutdown` → restart Desktop → wait for Ready → `docker compose up -d`. Full playbook: [`docs/DOCKER_TROUBLESHOOT.md`](docs/DOCKER_TROUBLESHOOT.md).

## LLM provider (Gemma on Cerebras)

| Role | Backend | Config |
|------|---------|--------|
| **App RAG / Agent / Judge** | **Cerebras** (default) | `PRA_LLM_BACKEND=cerebras` + `CEREBRAS_MODEL=gemma-4-31b` in `ZoomCamp/LLM/.env` |
| **Tutoring prompts** | Any chat UI | `_planning/tutor_packets/` — not in app code |

Shared secrets file: `E:\IT_SPACES\AI\ZoomCamp\LLM\.env` (same as dtc-podcast-rag).

```powershell
. .\scripts\use_e_drive.ps1
uv sync
uv run pra-check-llm
```

## Git & version control

1. **Commit attribution:** Do not include `Co-authored-by` or any AI/Cursor signatures in commit messages.
2. **`.cursor/rules/`:** Keep tracked in Git (project standards).
3. **Ignore:** `.cursor/history/`, `.cursor/temp/` (see `.gitignore`).
4. Commits are created **only when the user explicitly asks**.

## Phase workflow

1. Read `_planning/ROADMAP.md` — current phase **Done when** only.
2. Implement in this repo.
3. Update `_planning/PHASE_LOG.md`.
