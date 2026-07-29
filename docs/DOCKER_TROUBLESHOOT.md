# Docker / Grafana 문제해결

Windows + Docker Desktop(WSL2) + 여러 Grafana 스택을 돌릴 때 자주 막히는 경우를 정리한 운영 메모입니다.  
(`PHASE_LOG`에 흩어진 Docker/Grafana 트러블슈팅을 여기로 모은 플레이북.)

**이 프로젝트(PRA) Grafana:** http://localhost:3002 (`admin` / `admin`)

---

## 0. 먼저 구분하기 — Grafana만 죽은 건가, 엔진이 죽은 건가?

| 증상 | 의심 | 다음 행동 |
|------|------|-----------|
| `docker ps` / `docker info`가 **수 초~수십 초 이상 멈춤** | **Docker 엔진(WSL2) hang** | [1. 엔진 리셋](#1-도커-엔진-리셋)부터 |
| CLI는 되지만 Grafana만 404/빈 화면/재시작 반복 | 컨테이너·의존 DB 문제 | [2. 스택 재기동](#2-프로젝트-스택-재기동) |
| Grafana 로그에 `unable to open database file` / `SQLITE_BUSY` | 메타 DB(SQLite) 잠금·손상 | PRA는 이미 Postgres 메타 DB — [이슈 E](#e-grafana-sqlitebusy--마이그레이션-극느림) |
| `Conflict. The container name "/pra-..."` | orphan 컨테이너 이름 점유 | [이슈 D](#d-conflict-the-container-name-pra-postgres-is-already-in-use) |

> **핵심:** Grafana가 “꺼진” 것처럼 보여도, 원인은 종종 **개별 컨테이너가 아니라 Docker 엔진 hang**입니다. 엔진이 안 살면 `docker compose`도 의미가 없습니다.

---

## 1. 도커 엔진 리셋

### 순서

1. Docker Desktop을 **완전히 종료** (트레이 아이콘 → Quit).
2. PowerShell에서 WSL2 백엔드 강제 초기화:

```powershell
wsl --shutdown
```

3. Docker Desktop을 다시 실행하고, **초록불(엔진 Ready)** 이 될 때까지 기다린다.
4. 엔진 응답 확인:

```powershell
docker info
```

- 정상: Server Version 등이 바로 출력
- 비정상: **타임아웃/무응답** → 1~3을 한 번 더. 그래도 안 되면 Docker Desktop **Restart** / PC 재부팅

### 왜 이렇게 하나?

Docker Desktop 프론트 프로세스가 떠 있어도 **엔진(WSL `docker-desktop`)이 hang**이면 CLI가 멈춥니다. `wsl --shutdown`으로 VM을 내리고 Desktop을 다시 올려야 합니다.

---

## 2. 프로젝트 스택 재기동

엔진이 살아난 뒤, **이 프로젝트 폴더**에서:

```powershell
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
docker compose up -d
```

### Postgres가 먼저 healthy인지 확인

하드 종료 직후 Postgres는 **crash recovery**에 수십 초가 걸릴 수 있습니다. 그동안 Grafana가 `depends_on: service_healthy` 때문에 기동에 실패하거나 Restarting 루프에 들어갈 수 있습니다.

```powershell
docker ps --filter "name=pra-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

- `pra-postgres` / `pra-kestra-postgres` → `healthy`
- `pra-grafana` → `Up` (포트 **3002**)

Postgres만 늦게 올라온 경우:

```powershell
docker compose up -d grafana
```

한 번 더 실행하면 됩니다.

### UI 확인

브라우저: **http://localhost:3002**

---

## 3. 이 머신 포트 맵 (충돌 방지)

| 포트 | 용도 | 비고 |
|------|------|------|
| **3000** | 다른 Grafana (`grafana`) | nyc-taxi / ZoomCamp 등 — **PRA 아님** |
| **3001** | `dtc-rag-grafana` | `llm/dtc-podcast-rag` |
| **3002** | **`pra-grafana`** | **이 프로젝트 공식 URL** |
| **5433** | `llm02-pgvector` | Grafana 메타 DB + (당분간) 메트릭 `conversation_logs` |
| **5435** | `pra-postgres` | 앱 Postgres (named volume `pra_pgdata`) |
| **8080** | ZoomCamp Kestra 등 | PRA와 충돌 → PRA는 **8085** |
| **8085** | `pra-kestra` | PRA Kestra UI |

> PRA 데모 Grafana는 **항상 `:3002`**. `:3000`에 보이는 건 다른 스택입니다.

---

## 4. 알려진 이슈 (PHASE_LOG에서 모은 것)

### A) 엔진 hang 후 Grafana crash loop (2026-07-22)

- **증상:** `Restarting (1)`, 로그에 `unable to open database file (14)` (SQLite CANTOPEN)
- **배경:** 강제 종료 직후 bind-mount/SQLite 잠금, 또는 의존 Postgres가 아직 unhealthy
- **대응:** 엔진 리셋 → Postgres `healthy` 확인 → `docker compose up -d grafana`
- **기록:** `PHASE_LOG` Ops 2026-07-22

### B) Postgres `unhealthy` → Grafana dependency failed (Part 0-3)

- **증상:** `dependency failed to start: container ... is unhealthy`
- **원인 1 (첫 기동):** healthcheck가 `-d policy_refund_agent`로 찔러 **DB 생성 전**에 fail  
  (`database "policy_refund_agent" does not exist`)
- **원인 2 (재기동):** crash recovery / initdb에 수십 초 → healthcheck 연속 실패
- **정착 설정 (`docker-compose.yaml`):**

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U pra"]   # DB 이름 넣지 말 것
  interval: 5s
  timeout: 5s
  retries: 10
  start_period: 40s
```

- **대응:** `docker logs pra-postgres`에서 `ready to accept connections` 확인 후 `docker compose up -d`
- **기록:** `PHASE_LOG` Part 0-3

### C) `docker ps`가 영원히 안 끝남

- **진단:** 엔진 hang. Grafana 재기동 시도는 의미 없음 → [1. 엔진 리셋](#1-도커-엔진-리셋)

### D) `Conflict. The container name "/pra-postgres" is already in use` (2026-07-22)

- **증상:** `docker compose up -d` 시 이름 충돌. `compose ps`에는 없고 `docker ps -a`에는 `Exited` orphan
- **원인:** 예전 컨테이너가 compose 관리 밖으로 남거나, 엔진 hang 후 이름만 점유 (`Labels: {}`)
- **대응:**

```powershell
docker rm -f pra-postgres
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
docker compose up -d
```

- named volume(`pra_pgdata`)이면 데이터는 유지되고 컨테이너만 다시 만들어짐

### E) Grafana `SQLITE_BUSY` / 마이그레이션 극느림 (Part 5-3)

- **증상:** `:3002`가 `database: failing`, 패널 안 뜸. Desktop + Grafana SQLite 조합에서 자주 발생
- **정착 설정:** Grafana **메타 DB를 Postgres로** (`GF_DATABASE_*` → host `llm02` `:5433` DB `grafana`), 이미지 **10.4.19** 핀
- **주의:** 메타 DB(`grafana`)와 메트릭 조회 DB(`policy_refund_agent.conversation_logs`)는 역할이 다름 — 둘 다 llm02에 있을 수 있음
- **기록:** `PHASE_LOG` Part 5-3

### F) Windows bind-mount chown hang → Postgres 기동 실패 (Part 5-2)

- **증상:** `pra-postgres`가 Windows 호스트 폴더 bind-mount에서 권한/chown에 걸려 기동·헬스 실패
- **정착 설정:** 앱 DB는 **named volume `pra_pgdata`** 사용 (bind-mount 대신)
- **부작용/부채:** 엄격한 “모든 데이터 E:” 정책과 named volume(Docker VM 내부)의 타협 — AGENTS.md 참고
- **기록:** `PHASE_LOG` Part 5-2

### G) 메트릭 DB를 llm02 `:5433`에 둔 이유 (Part 5-3 부채) → **해소 (2026-07-22)**

- 과거: `pra-postgres` bind-mount 이슈로 Grafana 데이터소스가 **llm02 `:5433`** 을 봄
- 앱 `.env`는 **`POSTGRES_PORT=5435`** (`pra-postgres`) — **쓰기/읽기 경로 불일치**
- 증상: Streamlit/CLI로 새 Q&A를 해도 Grafana **No data** (또는 1h 창은 오래된 데이터만)
- **정착 (2026-07-22):**
  1. `pra-postgres`에 `conversation_logs` 생성 + llm02 기존 12건 이관
  2. `grafana/provisioning/datasources/postgres.yaml` → `host.docker.internal:5435` / user `pra`
  3. `docker compose up -d --force-recreate grafana`
- **추가 함정:** URL만 바꿔도 Grafana 메타DB에 **옛 user/password(`user`/`pswd`)가 남는 경우** → No data.  
  `deleteDatasources`로 삭제 후 재프로비저닝(또는 meta DB `data_source` row 삭제 후 recreate).
- 확인: http://localhost:3002/d/pra-agent-monitoring (기본 **now-3h**). 로그인 `admin`/`admin`.
- **Streamlit이 질문에 답은 하는데 Grafana가 안 변할 때:** 프로세스 환경에 옛 `POSTGRES_PORT=5433` 등이 남아 `.env`(5435)를 무시하는 경우가 많음.  
  `app/config.py`가 프로젝트 `.env`의 `POSTGRES_*`를 **강제 적용**하도록 수정함. Streamlit 재시작 필요.  
  확인: `psutil`로 프로세스 env의 `POSTGRES_PORT`가 `5435`인지 본다.

### H) Kestra 포트 / 볼륨 (K-1)

- 호스트 **8085** (ZoomCamp `8080`과 충돌 회피)
- 볼륨 E: `docker/kestra_pgdata`, `kestra_data`, `kestra_tmp`
- 파일 감시 트리거는 Windows bind 이슈로 K-2에서 보류 → 수동 실행 + Schedule

---

## 5. Docker 밖이지만 자주 막히는 것 (참고)

| 이슈 | 대응 요지 | 기록 |
|------|-----------|------|
| 이 PC에서 full `uv sync` hang (대형 휠) | `--no-sync` + system-site-packages venv로 검증 | Part 1-2, 3-2 |
| `pra-streamlit` 엔트리 누락 | `uv pip install -e . --no-deps` | README Quick start |

앱/의존성 이슈는 여기 Docker 플레이북 범위 밖이지만, “또 막히면” 위 표를 먼저 본다.

---

## 6. 빠른 체크리스트 (복붙용)

```powershell
# 1) 엔진 살아 있나?
docker info

# 2) 안 되면
# Docker Desktop Quit → wsl --shutdown → Desktop 재실행 → 초록불 대기

# 3) 이름 충돌이면
# docker rm -f pra-postgres

# 4) PRA 스택
cd E:\IT_SPACES\AI\Projects\llm\policy-refund-agent
docker compose up -d
docker ps --filter "name=pra-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 5) Grafana
# http://localhost:3002
```

---

## 관련 기록

| 출처 | 내용 |
|------|------|
| 이 파일 | **재현 가능한 플레이북** (증상 → 대응) |
| `_planning/PHASE_LOG.md` | 파트별 서사·배운 점·날짜별 Ops |
| `docker-compose.yaml` | healthcheck, `GF_DATABASE_*`, ports, volumes 정착값 |
| `README.md` / `AGENTS.md` | 요약 + 이 문서 링크 |
