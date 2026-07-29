# Demo screenshots

For README and portfolio use.

## Canonical (README)

### Hybrid retrieval

| File | Description |
|------|-------------|
| `hybrid/hybrid_ui.png` | Streamlit `:8502` — `retrieval: hybrid` + RRF scores |
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

Sequence: empty dashboard → Streamlit question with 👍 → Grafana metrics update.

### Docker Compose

| File | Description |
|------|-------------|
| `compose/streamlit-compose-refund.png` | Compose `:8502` — refund answer + Citations + **Feedback recorded: helpful 👍** |

## Archive

| Path | Description |
|------|-------------|
| `archive/pre-hybrid/temp.png` | Grafana before hybrid-era |
| `archive/pre-hybrid/temp2.png` | Older Grafana snapshot |
| `archive/pre-hybrid/temp_ui.png` | UI without `retrieval: hybrid` |
