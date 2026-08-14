# 🔒 Ops unlock password setup guide

For operators (zakard). The Product hub corner **Ops 🔒** is a password gate that shows **local Ops guidance only** — Kestra, local Postgres, local Grafana (`:3002`), and similar. Unlike the public surfaces (Product · Insights · Integrate · GitHub), it stays closed to reviewers and general users.

---

### 💡 Critical security note (read first)

> **Never put the actual password in GitHub, README, code, or chat.** (Prevents credential leaks.)

---

## ⚠️ Pick the correct Render service (read before Step 2)

Ops unlock lives on **Product only**. If you open the wrong service, you will waste time looking for a variable that is not there.

| Service name | URL | Role | Set `PRA_OPS_PASSWORD` here? |
|--------------|-----|------|------------------------------|
| **`policy-refund-agent`** ✅ | [policy-refund-agent.onrender.com](https://policy-refund-agent.onrender.com) | Product hub + chat + **Ops 🔒** | **Yes — set it here** |
| **`policy-refund-agent-api`** ❌ | [policy-refund-agent-api.onrender.com](https://policy-refund-agent-api.onrender.com) | Integrate API (`/health`, `/search`, `/answer`) | **No — wrong service for Ops** |

**You are on the wrong service if:**

- The browser / service URL contains **`policy-refund-agent-api`**
- The service name is **`policy-refund-agent-api`** (Integrate API)

Switch back to **`policy-refund-agent`** (URL **without** `-api`).

### ✅ On Product — missing `PRA_OPS_PASSWORD` is EXPECTED

You are on the **correct** service when the name is **`policy-refund-agent`** and the Environment list already shows many vars (`CEREBRAS_*`, `POSTGRES_*`, `PRA_*`, …) but **`PRA_OPS_PASSWORD` is not in the list**.

That is **not broken**. In `render.yaml` the key is `sync: false`, so Render does **not** create or show it until you add it yourself in the Dashboard (Step 2). Seeing lots of other env vars and no Ops password row means: right service — now Add/Edit.

---

## 🛠️ Step 1. Local environment setup

On startup, the app loads environment variables via `load_app_env()` (`app/config.py`).

1. **Project `.env`** (recommended)  
   `E:\IT_SPACES\AI\Projects\llm\policy-refund-agent\.env`
2. (Optional) Shared **`E:\IT_SPACES\AI\ZoomCamp\LLM\.env`** — fills in only when missing from the project `.env`; **does not override** project values.

For local testing, put the password **only in the project `.env`**.

1. Open the `.env` file above.
2. Add one line at the bottom with your chosen password and save.

```env
# .env — keep the real value local only. Do not commit.
PRA_OPS_PASSWORD=your-chosen-password-here
```

*(In `.env.example`, leave only an empty comment: `# PRA_OPS_PASSWORD=`.)*

3. **Restart** any running FastAPI/Product process for the change to take effect.

---

## ☁️ Step 2. Render (production) setup

**Local `.env` does not affect Render** — the Docker image does not include your project `.env`; set `PRA_OPS_PASSWORD` separately in the Render Dashboard.

The **Ops 🔒** UI and `/config` endpoint live on the **Product** service only — not on Integrate API.

### Navigation path (Render Dashboard — current UI)

1. Log in to the [Render dashboard](https://dashboard.render.com).
2. **Left sidebar** → open service **`policy-refund-agent`** (Product — URL ends with `.onrender.com`, **without** `-api`).  
   **Do not** open `policy-refund-agent-api`.
3. **Left sidebar** → click **Environment**.
4. Confirm you see other vars (`CEREBRAS_*`, `POSTGRES_*`, `PRA_*`, …) and **no** `PRA_OPS_PASSWORD` yet — expected (`sync: false`).
5. In the **Environment Variables** section, either:
   - Click **Edit** (top right of that section), **or**
   - Click **Add Environment Variable**
6. Add a **new row**:
   - **Key:** `PRA_OPS_PASSWORD`
   - **Value:** the same password as in your local project `.env` (never paste it into GitHub, Blueprint, README, or chat)
7. Click **Save Changes**.
8. Wait for the deploy to finish — status **Healthy** (auto-redeploy after Save, or **Manual Deploy** if needed).
9. Verify: open [https://policy-refund-agent.onrender.com/config](https://policy-refund-agent.onrender.com/config) → `"ops_configured": true`.

> **Note:** If you set `PRA_OPS_PASSWORD` only on `policy-refund-agent-api`, Product Ops 🔒 will still show *"Ops password not configured"* (`ops_configured: false` on `/config`). Always set it on **Product** (`policy-refund-agent`).

---

## ✅ Step 3. Verify the setup (test)

### 3a. Confirm env on Product `/config`

Open [https://policy-refund-agent.onrender.com/config](https://policy-refund-agent.onrender.com/config) (Product URL — **not** `-api`).

| Field | Expected after Step 2 |
|-------|------------------------|
| `ops_configured` | `true` |
| Wrong service | `-api` URL or `ops_configured: false` → you are on the wrong service or the variable was not saved on Product |

### 3b. Unlock in the UI

1. Open [https://policy-refund-agent.onrender.com](https://policy-refund-agent.onrender.com)
2. Click **Ops 🔒** in the corner
3. Enter the password → **Unlock**

| Situation | Expected |
|-----------|----------|
| Correct password | Modal shows local Grafana / Postgres / Kestra / Compose guidance |
| Wrong password | `Invalid Ops password` (API **401**) |
| Env not set | UI: `Ops password not configured on this deploy (set PRA_OPS_PASSWORD).` — if `/config` has `ops_configured: false`, unlock is blocked **before** the request. Direct API call returns **503** |

Local: `http://127.0.0.1:8000` (use whichever port your app runs on).

*(Optional) curl:*

```powershell
curl -s https://policy-refund-agent.onrender.com/config
# → "ops_configured": true

curl -s -o - -w "`nHTTP %{http_code}`n" -X POST https://policy-refund-agent.onrender.com/ops/unlock `
  -H "Content-Type: application/json" `
  -d "{\"password\":\"wrong\"}"
# → HTTP 401
```

---

## 🔄 Step 4. Password rotation

1. Choose a new password (do not paste it into docs, chat, or issues).
2. **Local:** update `PRA_OPS_PASSWORD` in the project `.env` → restart the app.
3. **Render:** **Sidebar → `policy-refund-agent` → Environment** → **Edit** (or find the existing row) → replace the value → **Save Changes** → wait for redeploy **Healthy**.
4. Run Step 3: `/config` shows `ops_configured: true`; new password unlocks; old password returns **401**.

---

## 📋 Quick checklist (Render)

- [ ] Opened **Product** `policy-refund-agent` (✅), not `policy-refund-agent-api` (❌)
- [ ] Env list can show many vars and still omit `PRA_OPS_PASSWORD` until you add it (`sync: false` — expected)
- [ ] **Edit** or **Add Environment Variable** → Key `PRA_OPS_PASSWORD` → Save Changes
- [ ] Real value not in git / README / issues
- [ ] After Save, deploy is Healthy
- [ ] [policy-refund-agent.onrender.com/config](https://policy-refund-agent.onrender.com/config) → `ops_configured: true`
- [ ] Site → Ops 🔒 → unlock works
- [ ] Wrong password → 401 / error message

If you need help, tell Cursor/chat **without the value** — e.g. whether it is configured, or whether you see **503** vs **401**.
