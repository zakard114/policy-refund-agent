# Ops 비밀번호 설정 가이드

운영자(zakard)용. **실제 비밀번호 값은 이 문서·README·git에 절대 넣지 마세요.**

## 1. Ops가 무엇인가 / 왜 잠겨 있는가

Product 허브 모서리의 **Ops 🔒**는 Kestra, 로컬 Postgres, 로컬 Grafana(`:3002`) 같은 **로컬 Ops 안내만** 보여 주는 게이트입니다.

- 공개 면: Product · Insights · Integrate · GitHub
- Ops: 리뷰어/일반 사용자에게 열어 두지 않음 (fail-closed)
- 비밀번호가 맞아도 **원격 Kestra/DB를 노출하지 않음** — `localhost` 안내와 Compose 힌트만 반환

구현: `POST /ops/unlock` (`app/api.py`) + Product 모달 (`product/static/app.js`).

## 2. 환경 변수

| 키 | 용도 |
|----|------|
| `PRA_OPS_PASSWORD` | Ops 🔓 공유 비밀번호 |

규칙:

- **커밋 금지** (`.env`는 gitignore, `.env.example`에는 빈 주석만)
- **공개 README에 평문 비밀번호 금지**
- 미설정 시 fail-closed: API `503`, UI는 `/config`의 `ops_configured: false`로 언락 거부

## 3. 로컬 설정

앱은 시작 시 `load_app_env()` (`app/config.py`)로 로드합니다.

1. 이미 프로세스에 있는 env (셸 export / IDE)
2. 프로젝트 `E:\IT_SPACES\AI\Projects\llm\policy-refund-agent\.env`
3. 공유 `E:\IT_SPACES\AI\ZoomCamp\LLM\.env` (없을 때만 채움, override 없음)

권장: **프로젝트 `.env`**에만 추가 (ZoomCamp 공유 파일과 섞지 않아도 됨).

```env
# .env — 실제 값만 로컬에. git에 올리지 말 것.
PRA_OPS_PASSWORD=여기에-본인이-정한-비밀번호
```

`.env.example` 참고 줄:

```env
# PRA_OPS_PASSWORD=
```

변경 후 FastAPI/Product 프로세스를 **재시작**해야 반영됩니다.

## 4. Render 설정

Product 서비스에만 넣으면 됩니다 (`render.yaml`의 `sync: false` 시크릿).

1. [Render Dashboard](https://dashboard.render.com) 로그인
2. 서비스 **`policy-refund-agent`** (Product) 선택  
   - Integrate 전용 `policy-refund-agent-api`에도 넣어도 되지만, 허브 UI의 Ops는 **Product** 쪽이 기준
3. **Environment** → `PRA_OPS_PASSWORD` 추가 (또는 기존 값 수정)
4. **Save Changes**
5. 자동 재배포를 기다리거나 **Manual Deploy** → 배포 완료·Healthy 확인

비밀번호 평문을 Blueprint/GitHub에 넣지 마세요.

## 5. 테스트 (본인이 직접)

### UI

1. https://policy-refund-agent.onrender.com 열기
2. 허브에서 **Ops 🔒** 클릭
3. 비밀번호 입력 → Unlock

| 상황 | 기대 |
|------|------|
| 올바른 비밀번호 | 모달에 로컬 Grafana / Postgres / Kestra / Compose 안내 표시 |
| 틀린 비밀번호 | 에러 (API `401 Invalid Ops password`) |
| env 미설정 | UI: “Ops password not configured…” 또는 API `503` |

미설정 시 UI는 `/config` → `ops_configured: false`이면 **요청 전에** 막고, 직접 API를 치면 `503`입니다.

### curl (선택)

```powershell
# 성공 (비밀번호는 셸에만; 히스토리/스크린샷 주의)
curl -s -X POST https://policy-refund-agent.onrender.com/ops/unlock `
  -H "Content-Type: application/json" `
  -d "{\"password\":\"YOUR_PASSWORD_HERE\"}"

# 틀린 비밀번호 → HTTP 401
curl -s -o - -w "\nHTTP %{http_code}\n" -X POST https://policy-refund-agent.onrender.com/ops/unlock `
  -H "Content-Type: application/json" `
  -d "{\"password\":\"wrong\"}"

# 미설정 배포 → HTTP 503
# (PRA_OPS_PASSWORD를 비운 뒤 재배포한 경우에만)
```

로컬 예: `http://127.0.0.1:8000/ops/unlock` (앱이 떠 있는 포트에 맞춤).

## 6. 비밀번호 변경 / 로테이션

1. 새 비밀번호를 정한다 (문서·채팅·이슈에 붙여 넣지 말 것).
2. **로컬:** `.env`의 `PRA_OPS_PASSWORD` 수정 → 앱 재시작.
3. **Render:** Product → Environment → 값 교체 → Save → 재배포 대기.
4. 위 테스트로 새 값 확인, 옛 값으로 `401` 나는지 확인.
5. 예전에 공유했다면 신뢰하는 운영자만 새 값을 **안전한 경로**(비밀번호 관리자 등)로 전달.

## 7. 빠른 체크리스트 (Render)

- [ ] Product `policy-refund-agent` Environment에 `PRA_OPS_PASSWORD` 설정
- [ ] 실제 값을 git / README / 이슈에 안 넣음
- [ ] Save 후 배포 Healthy
- [ ] 사이트 → Ops 🔒 → 정상 언락
- [ ] 틀린 비밀번호 → 401 / 에러 메시지
- [ ] (선택) curl로 `/ops/unlock` 확인

질문이 있으면 Cursor/채팅에 **값 없이** “설정했는지 / 503인지 401인지”만 알려 주세요.
