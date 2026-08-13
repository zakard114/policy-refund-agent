(function () {
  const messagesEl = document.getElementById("messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("question-input");
  const sendBtn = document.getElementById("send-btn");
  const toolsToggle = document.getElementById("use-tools");
  const chips = document.getElementById("chips");
  let typingEl = null;
  let cfg = { insights_url: "", github_url: "https://github.com/zakard114/policy-refund-agent" };

  fetch("/config")
    .then((r) => r.json())
    .then((data) => {
      cfg = Object.assign(cfg, data || {});
      const insights = document.getElementById("link-insights");
      if (insights && cfg.insights_url) insights.href = cfg.insights_url;
      const gh = document.getElementById("link-github");
      if (gh && cfg.github_url) gh.href = cfg.github_url;
    })
    .catch(function () {});

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

  function showTyping() {
    const wrap = document.createElement("div");
    wrap.className = "msg assistant";
    const bubble = document.createElement("div");
    bubble.className = "bubble typing";
    const label = document.createElement("span");
    label.textContent = toolsToggle.checked
      ? "Checking order tools & policy…"
      : "Searching policy & drafting…";
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
    scrollToBottom();
  }

  function hideTyping() {
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
    if (data.latency_s != null || data.model) {
      const hint = document.createElement("div");
      hint.className = "hint";
      const bits = [];
      if (data.model) bits.push(data.model);
      if (data.latency_s != null) bits.push(data.latency_s + "s");
      if (data.language) bits.push(data.language);
      hint.textContent = bits.join(" · ");
      wrap.appendChild(hint);
    }
    addFeedback(wrap, data.log_id);
  }

  function setBusy(busy) {
    input.disabled = busy;
    sendBtn.disabled = busy;
    toolsToggle.disabled = busy;
    chips.querySelectorAll("button").forEach(function (b) {
      b.disabled = busy;
    });
    input.placeholder = busy
      ? "Working…"
      : "Ask about refunds, returns, or order ZK-1001…";
  }

  function ask(question) {
    const q = (question || "").trim();
    if (!q) return;
    addMessage("user", q);
    input.value = "";
    setBusy(true);
    showTyping();

    fetch("/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: q,
        num_results: 3,
        use_llm: true,
        use_tools: !!toolsToggle.checked,
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
        input.focus();
      });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    ask(input.value);
  });

  chips.addEventListener("click", function (e) {
    const btn = e.target.closest("button[data-q]");
    if (!btn || btn.disabled) return;
    ask(btn.getAttribute("data-q"));
  });
})();
