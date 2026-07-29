"""Streamlit chat UI for the Policy & Refund Support Agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import streamlit as st

import app.env_paths  # noqa: F401

if TYPE_CHECKING:
    from app.llm import ChatResult


def main() -> None:
    st.set_page_config(
        page_title="Zakard Shop Policy Support",
        layout="centered",
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.title("Zakard Shop Policy Support")
    st.caption("Answers grounded in the refund & return policy, with section citations.")
    st.caption(
        "Each reply is logged to Postgres (`conversation_logs`). "
        "Use 👍 / 👎 under an answer to leave feedback for monitoring."
    )

    with st.sidebar:
        st.subheader("Settings")
        use_agent = st.toggle(
            "Agent tools (Part 6-1)",
            value=True,
            help="lookup_order / evaluate_refund / search_policy. Demo ids: ZK-1001…ZK-1005.",
        )
        num_results = st.slider("Sections retrieved", min_value=1, max_value=5, value=3)
        try:
            from app.llm import get_model

            st.markdown(f"**Model:** `{get_model()}`")
        except Exception as exc:  # noqa: BLE001
            st.markdown(f"**Model:** *(unavailable: {type(exc).__name__})*")
        if use_agent:
            st.markdown(
                "Agent path: `answer_with_agent` "
                "(tools: `search_policy`, `lookup_order`, `evaluate_refund`)."
            )
            st.caption("Try: *Can I refund order ZK-1001?*")
        else:
            st.markdown("RAG-only path: `answer_question` (no order tools).")
        if st.button("Clear chat"):
            st.session_state.messages = []
            st.rerun()

    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("result"):
                _render_citations(message["result"])
                _render_feedback(idx, message)

    prompt = st.chat_input(
        "Ask about refunds, returns, support hours, or order ZK-1001…"
    )
    if not prompt:
        return

    question = prompt.strip()
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner(
                "Running agent tools…" if use_agent else "Searching policy and drafting a reply…"
            ):
                if use_agent:
                    from app.agent import answer_with_agent

                    result = answer_with_agent(question, num_results=num_results)
                else:
                    from app.llm import answer_question

                    result = answer_question(question, num_results=num_results)
            st.markdown(result.answer)
            _render_citations(result)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result.answer,
                    "result": result,
                    "log_id": result.log_id,
                    "feedback": None,
                }
            )
            _render_feedback(len(st.session_state.messages) - 1, st.session_state.messages[-1])
        except Exception as exc:  # noqa: BLE001 — show API/network errors in UI
            error = f"Request failed: {type(exc).__name__}: {exc}"
            st.error(error)
            st.session_state.messages.append({"role": "assistant", "content": error})


def _render_citations(result: ChatResult) -> None:
    meta = []
    if result.language:
        meta.append(f"language: {result.language}")
    if result.search_query:
        meta.append(f"search: `{result.search_query}`")
    if result.retrieval_method:
        meta.append(f"retrieval: `{result.retrieval_method}`")
    meta.append(f"{result.elapsed_time:.1f}s")
    st.caption(" · ".join(meta))

    if not result.citations:
        st.info("No policy sections retrieved.")
        return

    with st.expander("Citations (retrieved policy sections)", expanded=True):
        for i, cite in enumerate(result.citations, 1):
            section = cite.get("section") or cite.get("id") or f"Section {i}"
            score = cite.get("rrf_score")
            score_bit = f" (RRF {score:.4f})" if isinstance(score, (int, float)) else ""
            st.markdown(f"**[{i}] {section}**{score_bit}")
            text = (cite.get("text") or "").strip()
            if text:
                st.markdown(text)
            st.divider()


def _render_feedback(msg_idx: int, message: dict[str, Any]) -> None:
    """Thumbs + optional comment; one submission per assistant message."""
    from app.database import log_conversation, save_feedback

    log_id = message.get("log_id")
    if message.get("result") is not None and log_id is None:
        log_id = getattr(message["result"], "log_id", None)
        message["log_id"] = log_id

    # Live answer sometimes fails to log (slow LLM / DB blip). Persist once
    # before feedback so thumbs always have a row to UPDATE.
    if not log_id and message.get("role") == "assistant" and message.get("content"):
        result = message.get("result")
        citations = list(getattr(result, "citations", None) or [])
        latency_ms = (
            int(getattr(result, "elapsed_time", 0) * 1000) if result is not None else None
        )
        # Prefer the paired user question from chat history.
        user_q = "UI feedback"
        msgs = st.session_state.get("messages") or []
        if msg_idx > 0 and msgs[msg_idx - 1].get("role") == "user":
            user_q = str(msgs[msg_idx - 1].get("content") or user_q)
        log_id = log_conversation(
            user_question=user_q,
            agent_answer=str(message.get("content") or ""),
            latency_ms=latency_ms,
            used_citations=citations,
        )
        message["log_id"] = log_id
        st.session_state.messages[msg_idx] = message

    if not log_id:
        st.caption("Feedback unavailable (conversation was not logged).")
        return

    existing = message.get("feedback")
    if existing in (1, -1, "up", "down"):
        label = "helpful 👍" if existing in (1, "up") else "not helpful 👎"
        st.caption(f"Feedback recorded: {label}")
        return

    st.markdown("**Was this answer helpful?**")
    c1, c2, c3 = st.columns([1, 1, 4])
    comment_key = f"fb_comment_{msg_idx}_{log_id}"
    with c3:
        comment = st.text_input(
            "Optional comment",
            key=comment_key,
            label_visibility="collapsed",
            placeholder="Optional comment…",
        )
    with c1:
        up = st.button("👍", key=f"fb_up_{msg_idx}_{log_id}", help="Helpful")
    with c2:
        down = st.button("👎", key=f"fb_down_{msg_idx}_{log_id}", help="Not helpful")

    if not up and not down:
        return

    rating = 1 if up else -1
    ok = save_feedback(log_id=int(log_id), feedback=rating, comment=comment or None)
    # Stale log_id (row deleted by old seed script) → insert a fresh row, retry once.
    if not ok:
        result = message.get("result")
        citations = list(getattr(result, "citations", None) or [])
        latency_ms = (
            int(getattr(result, "elapsed_time", 0) * 1000) if result is not None else None
        )
        user_q = "UI feedback"
        msgs = st.session_state.get("messages") or []
        if msg_idx > 0 and msgs[msg_idx - 1].get("role") == "user":
            user_q = str(msgs[msg_idx - 1].get("content") or user_q)
        fresh_id = log_conversation(
            user_question=user_q,
            agent_answer=str(message.get("content") or ""),
            latency_ms=latency_ms,
            used_citations=citations,
        )
        if fresh_id:
            message["log_id"] = fresh_id
            st.session_state.messages[msg_idx] = message
            ok = save_feedback(
                log_id=int(fresh_id), feedback=rating, comment=comment or None
            )
    if ok:
        message["feedback"] = rating
        st.session_state.messages[msg_idx] = message
        st.toast("Thanks — feedback saved." if rating == 1 else "Thanks — we'll use this to improve.")
        st.rerun()
    else:
        st.warning("Could not save feedback (DB). Try again later.")


if __name__ == "__main__":
    main()
