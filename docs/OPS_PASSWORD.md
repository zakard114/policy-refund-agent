# 🔒 Ops 잠금 해제 비밀번호 설정 가이드

운영자(zakard)용. Product 허브 모서리 **Ops 🔒**는 Kestra·로컬 Postgres·로컬 Grafana(`:3002`) 같은 **로컬 Ops 안내**만 보여 주는 비밀번호 게이트입니다. 공개 면(Product · Insights · Integrate · GitHub)과 달리 리뷰어/일반 사용자에게는 열어 두지 않습니다.

---

### 💡 가장 먼저 꼭 기억해야 할 주의사항

> **비밀번호 실제 값을 절대 GitHub, README, 코드, 채팅창에 올리지 마세요!** (보안 사고 방지)

---

## 🛠️ Step 1. 내 컴퓨터(로컬) 환경 설정하기

앱은 시작 시 `load_app_env()` (`app/config.py`)로 환경 변수를 읽습니다.

1. **프로젝트 `.env`** (권장)  
   `E:\IT_SPACES\AI\Projects\llm\policy-refund-agent\.env`
2. (선택) 공유 **`E:\IT_SPACES\AI\ZoomCamp\LLM\.env`** — 프로젝트 `.env`에 없을 때만 채워지며, **덮어쓰지 않음**

로컬 테스트는 **프로젝트 `.env`에만** 넣는 것을 권장합니다.

1. 위 `.env` 파일을 엽니다.
2. 맨 아래에 사용할 비밀번호를 한 줄 추가하고 저장합니다.

```env
# .env — 실제 값은 로컬에만. git에 올리지 말 것.
PRA_OPS_PASSWORD=여기에-본인이-정한-비밀번호
```

*(※ `.env.example`에는 `# PRA_OPS_PASSWORD=` 형태로 **빈 주석만** 남깁니다.)*

3. 실행 중이던 FastAPI/Product 프로세스를 **껐다가 다시 켜야** 반영됩니다.

---

## ☁️ Step 2. Render(인터넷 배포 서버) 설정하기

Product 서비스에만 넣으면 됩니다 (`render.yaml`의 `sync: false` 시크릿).

1. [Render 대시보드](https://dashboard.render.com)에 로그인합니다.
2. 서비스 **`policy-refund-agent`** (Product)를 클릭합니다.  
   *(Integrate 전용 `policy-refund-agent-api`에도 넣을 수 있지만, 허브 UI의 Ops는 **Product** 기준입니다.)*
3. 왼쪽 메뉴 **Environment**를 클릭합니다.
4. `PRA_OPS_PASSWORD`가 없으면 **Add Environment Variable**로 추가합니다.
   - **Key:** `PRA_OPS_PASSWORD`
   - **Value:** 본인이 정한 비밀번호 (평문을 Blueprint/GitHub에 넣지 말 것)
5. **Save Changes**를 눌러 저장합니다.
6. 자동 재배포를 기다리거나 **Manual Deploy** → 배포 완료·**Healthy** 확인.

---

## ✅ Step 3. 설정이 잘 되었는지 확인하기 (테스트)

1. [https://policy-refund-agent.onrender.com](https://policy-refund-agent.onrender.com) 접속
2. 화면 구석 **Ops 🔒** 클릭
3. 비밀번호 입력 → **Unlock**

| 상황 | 기대 |
|------|------|
| 올바른 비밀번호 | 로컬 Grafana / Postgres / Kestra / Compose 안내가 모달에 표시 |
| 틀린 비밀번호 | `Invalid Ops password` (API **401**) |
| env 미설정 | UI: `Ops password not configured on this deploy (set PRA_OPS_PASSWORD).` — `/config`의 `ops_configured: false`이면 **요청 전에** 막힘. API 직접 호출 시 **503** |

로컬: `http://127.0.0.1:8000` (앱이 떠 있는 포트에 맞춤).

*(선택) curl:*

```powershell
curl -s -o - -w "`nHTTP %{http_code}`n" -X POST https://policy-refund-agent.onrender.com/ops/unlock `
  -H "Content-Type: application/json" `
  -d "{\"password\":\"wrong\"}"
# → HTTP 401
```

---

## 🔄 Step 4. 비밀번호를 바꾸고 싶을 때 (로테이션)

1. 새 비밀번호를 정합니다 (문서·채팅·이슈에 붙여 넣지 말 것).
2. **로컬:** 프로젝트 `.env`의 `PRA_OPS_PASSWORD` 수정 → 앱 재시작.
3. **Render:** Product → Environment → 값 교체 → **Save** → 재배포 대기.
4. Step 3으로 새 값은 열리고, 예전 값은 **401**인지 확인합니다.

---

## 📋 빠른 체크리스트 (Render)

- [ ] Product `policy-refund-agent` Environment에 `PRA_OPS_PASSWORD` 설정
- [ ] 실제 값을 git / README / 이슈에 안 넣음
- [ ] Save 후 배포 Healthy
- [ ] 사이트 → Ops 🔒 → 정상 언락
- [ ] 틀린 비밀번호 → 401 / 에러 메시지

질문이 있으면 Cursor/채팅에 **값 없이** “설정했는지 / 503인지 401인지”만 알려 주세요.
