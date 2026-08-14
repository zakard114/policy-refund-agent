# Demo screenshots

For README and portfolio use.

## Hero

| File | Description |
|------|-------------|
| `readme-hero-banner.png` | README top banner — Zakard Shop Policy Support |

## Architecture

| File | Description |
|------|-------------|
| `architecture/live-path-infographic-v1.png` | Public live-path infographic — original v1 stage layout on dark charcoal (#0b0f14) with soft teal accents (Product → API → Agent/RAG → Hybrid RRF → LLM → Neon/Grafana). README Mermaid graph kept as the code-oriented view. |

## Canonical (README)

### Official Product (Render)

| File | Description |
|------|-------------|
| `product/render-product-zk1001.png` | Official Product on [Render](https://policy-refund-agent.onrender.com) — ZK-1001 eligible + citations (agent tools) |

### Hybrid retrieval (secondary — Streamlit)

| File | Description |
|------|-------------|
| `hybrid/hybrid_ui.png` | *Secondary Streamlit prototype (dev/demo)* — local `:8502` / [Cloud](https://policy-refund-agent.streamlit.app/); not official Render Product. `retrieval: hybrid` + RRF scores |
| `hybrid/hybrid_grafana.png` | Grafana `:3002` — hybrid-era monitoring snapshot |

Stable aliases (same bytes as hybrid):

- `streamlit-chat.png` ← `hybrid/hybrid_ui.png`
- `grafana-monitoring.png` ← `hybrid/hybrid_grafana.png`

### Monitoring + feedback

| File | Description |
|------|-------------|
| `monitoring/grafana-before.png` | Cold start — Questions `0` / No data |
| `monitoring/streamlit-feedback.png` | Live ask + Citations + **Feedback recorded: helpful 👍** |
| `monitoring/grafana-after.png` | After ask — latency, citations, **Thumbs up ≥ 1** |
| `monitoring/grafana-neon-after.png` | Optional — Grafana on Neon (public thumbs / logs) |

Sequence: empty dashboard → Streamlit question with 👍 → Grafana metrics update.

### Docker Compose

| File | Description |
|------|-------------|
| `compose/streamlit-compose-refund.png` | Compose `:8502` — refund answer + Citations + **Feedback recorded: helpful 👍** |

### Ops 🔒 (password-gated)

| File | Description |
|------|-------------|
| `ops/ops-unlock-gate.png` | Hub corner **Ops 🔒** — shared-password prompt (value masked by the input itself) |
| `ops/ops-unlocked-guidance.png` | Unlocked local operator guidance — Grafana `:3002`, Kestra `:8085`, Compose command. Postgres host **redacted**: original pixels overwritten with a flat opaque fill plus a painted `<host:port redacted>` bar (not a blur — nothing recoverable) |

### Cloud (secondary — Streamlit Community Cloud)

| File | Description |
|------|-------------|
| `cloud/streamlit-cloud-zk1001-ui.png` | Secondary prototype — `ZK-1001` eligible + 👍/feedback (no manage-app log); not official Render Product |
| `cloud/streamlit-cloud-zk1001.png` | Same answer + Cloud manage-app / install log |
| `cloud/streamlit-cloud-zk1001-ko.png` | Korean Q&A — `language: Korean`, agent tools, citations |

## Archive

| Path | Description |
|------|-------------|
| `archive/pre-hybrid/temp.png` | Grafana before hybrid-era |
| `archive/pre-hybrid/temp2.png` | Older Grafana snapshot |
| `archive/pre-hybrid/temp_ui.png` | UI without `retrieval: hybrid` |
