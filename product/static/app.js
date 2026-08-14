(function () {
  const bootScreen = document.getElementById("boot-screen");
  const bootStatus = document.getElementById("boot-status");
  const messagesEl = document.getElementById("messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("question-input");
  const sendBtn = document.getElementById("send-btn");
  const toolsToggle = document.getElementById("use-tools");
  const chips = document.getElementById("chips");
  const clearBtn = document.getElementById("clear-chat");
  const modelSelect = document.getElementById("model-select");
  const retrievalSelect = document.getElementById("retrieval-select");
  const opsBtn = document.getElementById("ops-btn");
  const opsModal = document.getElementById("ops-modal");
  const opsPassword = document.getElementById("ops-password");
  const opsError = document.getElementById("ops-error");
  const opsResult = document.getElementById("ops-result");
  const opsCancel = document.getElementById("ops-cancel");
  const opsSubmit = document.getElementById("ops-submit");
  let typingEl = null;
  let cfg = {
    insights_url: "",
    github_url: "https://github.com/zakard114/policy-refund-agent",
    model: "",
    models: [],
    retrieval: "hybrid",
    retrieval_options: ["hybrid", "keyword", "vector"],
    ops_configured: false,
  };

  function setBootStatus(text) {
    if (bootStatus) bootStatus.textContent = text;
  }

  function hideBoot() {
    if (!bootScreen) return;
    bootScreen.classList.add("is-done");
    bootScreen.setAttribute("aria-busy", "false");
    window.setTimeout(function () {
      if (bootScreen && bootScreen.parentNode) bootScreen.parentNode.removeChild(bootScreen);
    }, 400);
  }

  function fillSelect(el, values, selected) {
    if (!el) return;
    el.innerHTML = "";
    (values || []).forEach(function (v) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      if (v === selected) opt.selected = true;
      el.appendChild(opt);
    });
  }

  function applyConfig(data) {
    cfg = Object.assign(cfg, data || {});
    const insightsOpen = document.getElementById("insights-open");
    if (insightsOpen && cfg.insights_url) insightsOpen.href = cfg.insights_url;
    ["github-open", "github-readme"].forEach(function (id) {
      const el = document.getElementById(id);
      if (!el || !cfg.github_url) return;
      if (id === "github-readme") el.href = cfg.github_url.replace(/\/?$/, "") + "#readme";
      else el.href = cfg.github_url;
    });
    fillSelect(
      modelSelect,
      cfg.models && cfg.models.length ? cfg.models : [cfg.model || "unknown"],
      cfg.model
    );
    fillSelect(
      retrievalSelect,
      cfg.retrieval_options || ["hybrid", "keyword", "vector"],
      cfg.retrieval || "hybrid"
    );
    if (currentView === "insights" && !loaded.insights) ensureViewLoaded("insights");
  }

  function bootProduct() {
    const started = Date.now();
    const minMs = 1200;
    let slowTimer = window.setTimeout(function () {
      setBootStatus("Waking free tier… first request can take a minute");
    }, 4000);
    let laterTimer = window.setTimeout(function () {
      setBootStatus("Still starting — Render cold start in progress");
    }, 15000);

    function finish(ok) {
      window.clearTimeout(slowTimer);
      window.clearTimeout(laterTimer);
      setBootStatus(ok ? "Ready" : "Ready (limited config)");
      const wait = Math.max(0, minMs - (Date.now() - started));
      window.setTimeout(hideBoot, wait);
    }

    // Health first (survives cold start), then config.
    fetch("/health")
      .then(function (r) {
        if (!r.ok) throw new Error("health");
        setBootStatus("Loading settings…");
        return fetch("/config");
      })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        applyConfig(data);
        finish(true);
      })
      .catch(function () {
        fillSelect(modelSelect, ["unavailable"], "unavailable");
        finish(false);
      });
  }

  bootProduct();

  /* ---- Hub SPA: Product / Insights / Integrate / GitHub slide ---- */
  const hubNav = document.getElementById("hub-nav");
  const brandHome = document.getElementById("brand-home");
  const insightsFrame = document.getElementById("insights-frame");
  const integrateFrame = document.getElementById("integrate-frame");
  const insightsHint = document.getElementById("insights-hint");
  let currentView = "product";
  let currentOrder = 0;
  let sliding = false;
  const loaded = { product: true, insights: false, integrate: false, github: true };

  function setHubActive(view) {
    if (!hubNav) return;
    hubNav.querySelectorAll(".hub-item[data-view]").forEach(function (el) {
      el.classList.toggle("active", el.getAttribute("data-view") === view);
    });
  }

  function ensureViewLoaded(view) {
    if (view === "insights" && !loaded.insights) {
      if (cfg.insights_url && insightsFrame) {
        insightsFrame.src = cfg.insights_url;
        loaded.insights = true;
        if (insightsHint) insightsHint.hidden = false;
      } else if (insightsHint) {
        insightsHint.hidden = false;
        insightsHint.textContent =
          "Insights URL not configured. Set PRA_INSIGHTS_URL / GRAFANA public URL.";
      }
    }
    if (view === "integrate" && !loaded.integrate && integrateFrame) {
      integrateFrame.src = "/docs";
      loaded.integrate = true;
    }
  }

  function viewUrl(view) {
    if (view === "product") return window.location.origin + "/";
    if (view === "insights") return cfg.insights_url || "";
    if (view === "integrate") return window.location.origin + "/docs";
    if (view === "github") return cfg.github_url || "";
    return "";
  }

  function openViewNewTab(view) {
    const url = viewUrl(view);
    if (!url) return false;
    window.open(url, "_blank", "noopener,noreferrer");
    return true;
  }

  function isModifiedClick(e) {
    return !!(e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1);
  }

  function goToView(nextView, nextOrder) {
    if (sliding || nextView === currentView) return;
    const fromEl = document.getElementById("view-" + currentView);
    const toEl = document.getElementById("view-" + nextView);
    if (!fromEl || !toEl) return;

    ensureViewLoaded(nextView);
    sliding = true;
    const forward = nextOrder > currentOrder;
    const prep = forward ? "is-prep-right" : "is-prep-left";
    const exit = forward ? "is-exit-left" : "is-exit-right";

    toEl.classList.add(prep);
    void toEl.offsetWidth;

    fromEl.classList.add(exit);
    fromEl.classList.remove("is-active");
    toEl.classList.remove(prep);
    toEl.classList.add("is-active");

    setHubActive(nextView);
    currentView = nextView;
    currentOrder = nextOrder;

    window.setTimeout(function () {
      fromEl.classList.remove(exit);
      sliding = false;
    }, 400);
  }

  if (hubNav) {
    hubNav.addEventListener("click", function (e) {
      const item = e.target.closest(".hub-item");
      if (!item || item.id === "ops-btn") return;
      const view = item.getAttribute("data-view");
      if (!view) return;
      e.preventDefault();
      if (isModifiedClick(e)) {
        openViewNewTab(view);
        return;
      }
      const order = parseInt(item.getAttribute("data-order") || "0", 10);
      goToView(view, order);
    });
    hubNav.addEventListener("auxclick", function (e) {
      if (e.button !== 1) return;
      const item = e.target.closest(".hub-item");
      if (!item || item.id === "ops-btn") return;
      const view = item.getAttribute("data-view");
      if (!view) return;
      e.preventDefault();
      openViewNewTab(view);
    });
  }

  if (brandHome) {
    brandHome.addEventListener("click", function (e) {
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) {
        openViewNewTab("product");
        return;
      }
      if (currentView !== "product") {
        goToView("product", 0);
        return;
      }
      const productView = document.getElementById("view-product");
      if (productView) productView.scrollTop = 0;
      if (input) input.focus();
    });
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addMessage(kind, text) {
    const wrap = document.createElement("div");
    wrap.className = "msg " + kind;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    scrollToBottom();
    return wrap;
  }

  let typingTimer = null;

  function showTyping() {
    hideTyping();
    const wrap = document.createElement("div");
    wrap.className = "msg assistant";
    const bubble = document.createElement("div");
    bubble.className = "bubble typing";
    const label = document.createElement("span");
    const phases = toolsToggle.checked
      ? [
          "Checking order tools & policy…",
          "Running agent tools…",
          "Drafting grounded answer…",
        ]
      : [
          "Searching policy…",
          "Ranking citations…",
          "Drafting grounded answer…",
        ];
    let phase = 0;
    label.textContent = phases[0];
    const dots = document.createElement("span");
    dots.className = "dots";
    for (let i = 0; i < 3; i++) {
      const d = document.createElement("span");
      d.className = "dot";
      dots.appendChild(d);
    }
    bubble.appendChild(label);
    bubble.appendChild(dots);
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    typingEl = wrap;
    typingTimer = window.setInterval(function () {
      phase = (phase + 1) % phases.length;
      label.textContent = phases[phase];
    }, 2800);
    scrollToBottom();
  }

  function hideTyping() {
    if (typingTimer) {
      window.clearInterval(typingTimer);
      typingTimer = null;
    }
    if (typingEl) {
      typingEl.remove();
      typingEl = null;
    }
  }

  function addCitations(wrap, citations, retrieval) {
    if (!Array.isArray(citations) || !citations.length) return;
    const details = document.createElement("details");
    details.className = "citations";
    const summary = document.createElement("summary");
    summary.textContent =
      "Citations (" + citations.length + ")" + (retrieval ? " · " + retrieval : "");
    details.appendChild(summary);
    citations.forEach(function (c) {
      const box = document.createElement("div");
      box.className = "cite";
      const head = document.createElement("b");
      head.textContent = c.section || c.id || "Policy section";
      const body = document.createElement("div");
      const text = (c.text || "").trim();
      body.textContent = text.length > 420 ? text.slice(0, 420) + "…" : text;
      box.appendChild(head);
      box.appendChild(body);
      details.appendChild(box);
    });
    wrap.appendChild(details);
  }

  function addFeedback(wrap, logId) {
    const meta = document.createElement("div");
    meta.className = "meta";
    if (logId == null) {
      const hint = document.createElement("span");
      hint.className = "hint";
      hint.textContent = "Feedback unavailable (no log id)";
      meta.appendChild(hint);
      wrap.appendChild(meta);
      return;
    }

    function send(val, btn) {
      btn.disabled = true;
      fetch("/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ log_id: logId, feedback: val }),
      })
        .then(function (resp) {
          if (resp.ok) {
            btn.classList.add("on");
            up.disabled = true;
            down.disabled = true;
          } else btn.disabled = false;
        })
        .catch(function () {
          btn.disabled = false;
        });
    }

    const up = document.createElement("button");
    up.type = "button";
    up.className = "fb";
    up.textContent = "👍 Helpful";
    up.addEventListener("click", function () {
      send(1, up);
    });

    const down = document.createElement("button");
    down.type = "button";
    down.className = "fb";
    down.textContent = "👎 Not helpful";
    down.addEventListener("click", function () {
      send(-1, down);
    });

    meta.appendChild(up);
    meta.appendChild(down);
    wrap.appendChild(meta);
  }

  function renderAssistant(data) {
    const answer =
      data.answer ||
      (data.citations && data.citations.length
        ? "(Retrieval-only — no LLM answer)"
        : "No answer returned.");
    const wrap = addMessage("assistant", answer);
    addCitations(wrap, data.citations, data.retrieval);
    if (data.latency_s != null || data.language) {
      const hint = document.createElement("div");
      hint.className = "hint";
      const bits = [];
      if (data.latency_s != null) bits.push(data.latency_s + "s");
      if (data.language) bits.push(data.language);
      hint.textContent = bits.join(" · ");
      wrap.appendChild(hint);
    }
    addFeedback(wrap, data.log_id);
  }

  function setBusy(busy) {
    if (input) {
      input.disabled = busy;
      input.placeholder = busy
        ? "Working..."
        : "Ask about refunds, returns, or order ZK-1001...";
    }
    if (sendBtn) sendBtn.disabled = busy;
    if (toolsToggle) toolsToggle.disabled = busy;
    if (modelSelect) modelSelect.disabled = busy;
    if (retrievalSelect) retrievalSelect.disabled = busy;
    if (chips) {
      chips.querySelectorAll("button").forEach(function (b) {
        b.disabled = busy;
      });
    }
  }

  function ask(question) {
    const q = (question || "").trim();
    if (!q) return;
    const welcome = document.getElementById("welcome");
    if (welcome) welcome.remove();
    addMessage("user", q);
    if (input) input.value = "";
    setBusy(true);
    showTyping();

    fetch("/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: q,
        num_results: 3,
        use_llm: true,
        use_tools: !!(toolsToggle && toolsToggle.checked),
        method: retrievalSelect ? retrievalSelect.value : "hybrid",
        model: modelSelect ? modelSelect.value : undefined,
      }),
    })
      .then(function (resp) {
        return resp.json().then(function (data) {
          return { ok: resp.ok, data: data };
        });
      })
      .then(function (res) {
        if (res.ok) renderAssistant(res.data);
        else {
          const detail =
            (res.data && (res.data.detail || res.data.message)) ||
            "Request failed. Try again.";
          addMessage("error", typeof detail === "string" ? detail : JSON.stringify(detail));
        }
      })
      .catch(function () {
        addMessage("error", "Network error — could not reach the agent.");
      })
      .finally(function () {
        hideTyping();
        setBusy(false);
        if (input) input.focus();
      });
  }

  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      ask(input ? input.value : "");
    });
  }

  if (chips) {
    chips.addEventListener("click", function (e) {
      const btn = e.target.closest("button[data-q]");
      if (!btn || btn.disabled) return;
      ask(btn.getAttribute("data-q"));
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      messagesEl.innerHTML = "";
      const wrap = document.createElement("div");
      wrap.className = "msg assistant welcome";
      wrap.id = "welcome";
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.innerHTML =
        "Chat cleared. Try a chip above, or ask about refunds / order <b>ZK-1001</b>.";
      wrap.appendChild(bubble);
      messagesEl.appendChild(wrap);
    });
  }

  function openOps() {
    if (!opsModal) return;
    opsError.hidden = true;
    opsResult.hidden = true;
    opsResult.textContent = "";
    opsPassword.value = "";
    opsModal.hidden = false;
    opsPassword.focus();
  }

  function closeOps() {
    if (opsModal) opsModal.hidden = true;
  }

  if (opsBtn) opsBtn.addEventListener("click", openOps);
  if (opsCancel) opsCancel.addEventListener("click", closeOps);
  if (opsModal) {
    opsModal.addEventListener("click", function (e) {
      if (e.target === opsModal) closeOps();
    });
  }
  if (opsSubmit) {
    opsSubmit.addEventListener("click", function () {
      opsError.hidden = true;
      if (!cfg.ops_configured) {
        opsError.textContent = "Ops password not configured on this deploy (PRA_OPS_PASSWORD).";
        opsError.hidden = false;
        return;
      }
      opsSubmit.disabled = true;
      fetch("/ops/unlock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: opsPassword.value || "" }),
      })
        .then(function (resp) {
          return resp.json().then(function (data) {
            return { ok: resp.ok, data: data };
          });
        })
        .then(function (res) {
          if (!res.ok) {
            opsError.textContent =
              (res.data && res.data.detail) || "Unlock failed";
            opsError.hidden = false;
            return;
          }
          const local = res.data.local || {};
          opsResult.textContent = [
            res.data.note,
            "",
            "Grafana Ops: " + (local.grafana_ops || ""),
            "Postgres:     " + (local.postgres || ""),
            "Kestra:       " + (local.kestra || ""),
            "Compose:      " + (local.compose || ""),
            "",
            res.data.insights_admin || "",
          ].join("\n");
          opsResult.hidden = false;
        })
        .catch(function () {
          opsError.textContent = "Network error";
          opsError.hidden = false;
        })
        .finally(function () {
          opsSubmit.disabled = false;
        });
    });
  }
})();
