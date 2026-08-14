# 🔒 Ops unlock password setup guide

For operators (zakard). The Product hub corner **Ops 🔒** is a password gate that shows **local Ops guidance only** — Kestra, local Postgres, local Grafana (`:3002`), and similar. Unlike the public surfaces (Product · Insights · Integrate · GitHub), it stays closed to reviewers and general users.

---

### 💡 Critical security note (read first)

> **Never put the actual password in GitHub, README, code, or chat.** (Prevents credential leaks.)

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

| Service name | URL | Role | Needs `PRA_OPS_PASSWORD`? |
|--------------|-----|------|---------------------------|
| **`policy-refund-agent`** | [policy-refund-agent.onrender.com](https://policy-refund-agent.onrender.com) | Product hub + chat + **Ops 🔒** | **Yes — set it here** |
| `policy-refund-agent-api` | [policy-refund-agent-api.onrender.com](https://policy-refund-agent-api.onrender.com) | Integrate API (`/health`, `/search`, `/answer`) | No — setting it here does **not** unlock Product Ops |

> **Common mistake:** If you open **`policy-refund-agent-api`**, you will see vars like `CEREBRAS_*` and `PRA_INSIGHTS_URL`, but **`PRA_OPS_PASSWORD` is not listed** (and is not in that service's Blueprint). That is expected. Switch to **Product** below.

1. Log in to the [Render dashboard](https://dashboard.render.com).
2. In the **left sidebar**, select service **`policy-refund-agent`** (Product — URL ends with `.onrender.com`, **without** `-api`).  
   **Do not** use `policy-refund-agent-api`.
3. In the **left sidebar**, click **Environment**.
4. `PRA_OPS_PASSWORD` will **not** exist yet on a fresh deploy — click **Add Environment Variable** (or **Edit** → add a row):
   - **Key:** `PRA_OPS_PASSWORD`
   - **Value:** your chosen password (do not put plaintext in Blueprint/GitHub)
5. Click **Save Changes**.
6. Wait for auto-redeploy or run **Manual Deploy** → confirm deploy completes and status is **Healthy**.

> **Note:** If you set `PRA_OPS_PASSWORD` only on `policy-refund-agent-api`, Product Ops 🔒 will still show *"Ops password not configured"* (`ops_configured: false` on `/config`). Always set it on **Product** (`policy-refund-agent`).

---

## ✅ Step 3. Verify the setup (test)

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
curl -s -o - -w "`nHTTP %{http_code}`n" -X POST https://policy-refund-agent.onrender.com/ops/unlock `
  -H "Content-Type: application/json" `
  -d "{\"password\":\"wrong\"}"
# → HTTP 401
```

---

## 🔄 Step 4. Password rotation

1. Choose a new password (do not paste it into docs, chat, or issues).
2. **Local:** update `PRA_OPS_PASSWORD` in the project `.env` → restart the app.
3. **Render:** Product → Environment → replace the value → **Save** → wait for redeploy.
4. Run Step 3: the new value unlocks; the old value should return **401**.

---

## 📋 Quick checklist (Render)

- [ ] `PRA_OPS_PASSWORD` set on Product `policy-refund-agent` Environment
- [ ] Real value not in git / README / issues
- [ ] After Save, deploy is Healthy
- [ ] Site → Ops 🔒 → unlock works
- [ ] Wrong password → 401 / error message

If you need help, tell Cursor/chat **without the value** — e.g. whether it is configured, or whether you see **503** vs **401**.
