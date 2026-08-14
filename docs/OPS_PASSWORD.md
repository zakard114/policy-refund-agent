# Ops unlock password

Password gate for Product hub **Ops 🔒** (local Ops guidance only).  
**Never put the real password in GitHub, README, code, or chat.**

---

## 1. Local `.env`

1. Open project `.env` (`policy-refund-agent/.env`).
2. Add:

```env
PRA_OPS_PASSWORD=your-chosen-password-here
```

3. Keep `# PRA_OPS_PASSWORD=` only in `.env.example` (no real value).
4. Restart the app.

Local `.env` does **not** apply to Render — set the same key on Render separately (below).

---

## 2. Render setup

1. https://dashboard.render.com — log in  
2. Left service list → **`policy-refund-agent`**  
3. Confirm Live URL is `https://policy-refund-agent.onrender.com` (`-api` = wrong service)  
4. That service → left menu → **Environment**  
5. Environment Variables → top-right **Edit**  
6. **Add Environment Variable** (or empty Key / Value row at the bottom)  
7. New row:
   - **Key:** `PRA_OPS_PASSWORD`
   - **Value:** same password as local `.env`
8. **Save Changes**

It will **not** appear in the list until you Add it.  
Do not wait for it to show up next to `CEREBRAS_*` / `POSTGRES_*` — add it yourself.

9. Wait for deploy **Live / Healthy**  
10. https://policy-refund-agent.onrender.com → **Ops 🔒** → Unlock  

Optional check: https://policy-refund-agent.onrender.com/config → `"ops_configured": true`
