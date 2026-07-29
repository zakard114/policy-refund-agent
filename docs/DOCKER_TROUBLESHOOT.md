# Docker / Grafana Troubleshooting

Operational playbook for Windows + Docker Desktop (WSL2) environments running multiple Grafana stacks.

**This project's Grafana:** http://localhost:3002 (`admin` / `admin`)

---

## 0. First — is it Grafana or the engine?

| Symptom | Likely cause | Next step |
|---------|-------------|-----------|
| `docker ps` / `docker info` hangs for 10+ seconds | **Docker engine (WSL2) hang** | [1. Engine reset](#1-engine-reset) |
| CLI works but Grafana shows 404 / blank / restart loop | Container or dependency DB issue | [2. Stack restart](#2-project-stack-restart) |
| Grafana logs: `unable to open database file` / `SQLITE_BUSY` | Meta DB (SQLite) lock/corruption | PRA already uses Postgres meta DB — see [Issue E](#e-grafana-sqlite_busy--slow-migrations) |
| `Conflict. The container name "/pra-..."` | Orphan container holding the name | [Issue D](#d-container-name-conflict) |

> **Key insight:** when Grafana appears "down", the root cause is often a **Docker engine hang**, not Grafana itself. If the engine is unresponsive, `docker compose` commands are useless.

---

## 1. Engine reset

### Steps

1. **Quit Docker Desktop** completely (system tray → Quit).
2. Force-reset the WSL2 backend:

```powershell
wsl --shutdown
```

3. Relaunch Docker Desktop and wait for the **green "Engine running"** indicator.
4. Verify:

```powershell
docker info
```

- **Normal:** Server Version prints immediately.
- **Still hanging:** repeat steps 1–3, or reboot the machine.

### Why this works

The Docker Desktop UI process can stay alive while the **WSL `docker-desktop` VM is hung**. `wsl --shutdown` kills the VM so Desktop can start fresh.

---

## 2. Project stack restart

Once the engine is responsive, from the **project folder**:

```powershell
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
docker compose up -d
```

### Wait for Postgres to be healthy

After a hard shutdown, Postgres may need 30+ seconds for crash recovery. During that time Grafana's `depends_on: service_healthy` prevents it from starting.

```powershell
docker ps --filter "name=pra-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

- `pra-postgres` / `pra-kestra-postgres` → `healthy`
- `pra-grafana` → `Up` (port **3002**)

If only Postgres was slow:

```powershell
docker compose up -d grafana
```

### Verify UI

Open **http://localhost:3002** in a browser.

---

## 3. Port map (conflict prevention)

| Port | Service | Notes |
|------|---------|-------|
| **3000** | Other Grafana stacks | Not this project |
| **3001** | `dtc-rag-grafana` | Sibling project |
| **3002** | **`pra-grafana`** | **This project** |
| **5435** | `pra-postgres` | App DB (named volume `pra_pgdata`) |
| **8085** | `pra-kestra` | Ingestion UI |

> PRA Grafana is **always `:3002`**. Anything on `:3000` is a different stack.

---

## 4. Known issues

### A) Engine hang → Grafana crash loop

- **Symptom:** `Restarting (1)`, logs show `unable to open database file (14)` (SQLite CANTOPEN)
- **Cause:** hard shutdown leaves SQLite locks or Postgres is still unhealthy
- **Fix:** engine reset → confirm Postgres `healthy` → `docker compose up -d grafana`

### B) Postgres `unhealthy` → Grafana dependency failed

- **Symptom:** `dependency failed to start: container ... is unhealthy`
- **Cause 1:** healthcheck queries a DB name before `CREATE DATABASE` finishes
- **Cause 2:** crash recovery takes longer than healthcheck retries
- **Settled config** (`docker-compose.yaml`):

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U pra"]
  interval: 5s
  timeout: 5s
  retries: 10
  start_period: 40s
```

- **Fix:** check `docker logs pra-postgres` for `ready to accept connections`, then `docker compose up -d`

### C) `docker ps` never returns

- Engine hang. Skip Grafana troubleshooting → go to [1. Engine reset](#1-engine-reset).

### D) Container name conflict

- **Symptom:** `Conflict. The container name "/pra-postgres" is already in use`
- **Cause:** orphan container from a previous compose session or engine hang
- **Fix:**

```powershell
docker rm -f pra-postgres
docker compose up -d
```

Named volumes (`pra_pgdata`) preserve data across container recreation.

### E) Grafana `SQLITE_BUSY` / slow migrations

- **Symptom:** `:3002` shows `database: failing`, panels won't load
- **Settled fix:** Grafana meta DB switched to Postgres (`GF_DATABASE_*` in `docker-compose.yaml`), image pinned to **10.4.19**

### F) Windows bind-mount chown hang → Postgres won't start

- **Symptom:** `pra-postgres` fails on permission/chown with a Windows host folder
- **Settled fix:** app DB uses **named volume `pra_pgdata`** instead of bind-mount

---

## 5. Quick checklist (copy-paste)

```powershell
# 1) Is the engine alive?
docker info

# 2) If not:
# Docker Desktop Quit → wsl --shutdown → restart Desktop → wait for green light

# 3) Name conflict?
# docker rm -f pra-postgres

# 4) Start PRA stack
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
docker compose up -d
docker ps --filter "name=pra-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 5) Grafana
# http://localhost:3002
```
