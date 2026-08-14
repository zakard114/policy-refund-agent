# Demo screenshots

For README and portfolio use.

## Hero

| File | Description |
|------|-------------|
| `readme-hero-banner.png` | README top banner — Zakard Shop Policy Support |

## Architecture

| File | Description |
|------|-------------|
| `architecture/live-path-infographic-v1.png` | Public live-path infographic (Product → API → Agent/RAG → Hybrid RRF → LLM → Neon/Grafana). README Mermaid graph kept as the code-oriented view. |

## Canonical (README)

### Hybrid retrieval

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
| `monitoring/grafana-neon-after.png` | Optional — Grafana on Neon (Cloud thumbs / logs) |

Sequence: empty dashboard → Streamlit question with 👍 → Grafana metrics update.

### Docker Compose

| File | Description |
|------|-------------|
| `compose/streamlit-compose-refund.png` | Compose `:8502` — refund answer + Citations + **Feedback recorded: helpful 👍** |

### Cloud deployment

| File | Description |
|------|-------------|
| `cloud/streamlit-cloud-zk1001-ui.png` | Clean UI — `ZK-1001` eligible + 👍/feedback (no manage-app log) |
| `cloud/streamlit-cloud-zk1001.png` | Same answer + Cloud manage-app / install log |
| `cloud/streamlit-cloud-zk1001-ko.png` | Korean Q&A — `language: Korean`, agent tools, citations |

## Archive

| Path | Description |
|------|-------------|
| `archive/pre-hybrid/temp.png` | Grafana before hybrid-era |
| `archive/pre-hybrid/temp2.png` | Older Grafana snapshot |
| `archive/pre-hybrid/temp_ui.png` | UI without `retrieval: hybrid` |
