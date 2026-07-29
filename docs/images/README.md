# Demo screenshots

README / portfolio용.

## Canonical (README)

### Hybrid retrieval

| File | What |
|------|------|
| `hybrid/hybrid_ui.png` | Streamlit `:8502` — `retrieval: hybrid` + RRF scores |
| `hybrid/hybrid_grafana.png` | Grafana `:3002` — hybrid-era monitoring snapshot |

Stable aliases (same bytes as hybrid):

- `streamlit-chat.png` ← `hybrid/hybrid_ui.png`
- `grafana-monitoring.png` ← `hybrid/hybrid_grafana.png`

### Monitoring + feedback (2026-07-24)

| File | What |
|------|------|
| `monitoring/grafana-before.png` | Cold start — Questions `0` / No data |
| `monitoring/streamlit-feedback.png` | Live ask + Citations + **Feedback recorded: helpful 👍** |
| `monitoring/grafana-after.png` | After ask — latency, citations, **Thumbs up ≥ 1** |

Story: empty dashboard → Streamlit question · 👍 → Grafana metrics update (`pra-postgres:5435`).

### Docker Compose (2026-07-29)

| File | What |
|------|------|
| `compose/streamlit-compose-refund.png` | Compose `:8502` — refund answer + Citations + **Feedback recorded: helpful 👍** |

Source copy also kept in portfolio folder: `zoomcamp_misc/LLM/Project/project_2/img/compose/`.

## Archive

| Path | What |
|------|------|
| `archive/pre-hybrid/temp.png` | Grafana before hybrid-era ask |
| `archive/pre-hybrid/temp2.png` | Older Grafana |
| `archive/pre-hybrid/temp_ui.png` | UI without `retrieval: hybrid` |

**Do not** commit Cursor `assets/` temp paths — copy into `docs/images/` first.
