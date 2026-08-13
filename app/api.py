"""FastAPI Integrate surface: /health, /search, /answer, /docs."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.config import load_app_env, retrieval_method
from app.hybrid import retrieve
from app.query import prepare_search_query

load_app_env()

app = FastAPI(
    title="Policy & Refund Support Agent API",
    description=(
        "Integrate API for Zakard Shop policy RAG — hybrid search and "
        "grounded answers. Official Product UI is separate; this is the JSON surface."
    ),
    version="0.1.0",
)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    num_results: int = Field(default=3, ge=1, le=10)
    use_llm: bool = Field(
        default=True,
        description="If false, skip LLM query rewrite (works without an API key).",
    )


class AnswerRequest(BaseModel):
    query: str = Field(..., min_length=1)
    num_results: int = Field(default=3, ge=1, le=10)
    use_llm: bool = Field(
        default=True,
        description="If false, return retrieval-only payload (no answer LLM).",
    )
    use_tools: bool = Field(
        default=False,
        description="If true and use_llm, run the tool-calling agent path.",
    )


def _serialize_hit(doc: dict[str, Any], method: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": doc.get("id", ""),
        "section": doc.get("section", ""),
        "text": (doc.get("text") or "").strip(),
        "retrieval": method,
    }
    if doc.get("rrf_score") is not None:
        out["rrf_score"] = doc["rrf_score"]
    if doc.get("cosine_sim") is not None:
        out["cosine_sim"] = doc["cosine_sim"]
    return out


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "policy-refund-agent-api"}


@app.post("/search")
def search_endpoint(request: SearchRequest) -> dict[str, Any]:
    prepared = prepare_search_query(request.query, use_llm=request.use_llm)
    hits, method = retrieve(
        prepared.search_query,
        num_results=request.num_results,
        method=retrieval_method(),
    )
    return {
        "query": request.query,
        "search_query": prepared.search_query,
        "language": prepared.language,
        "retrieval": method,
        "results": [_serialize_hit(doc, method) for doc in hits],
    }


@app.post("/answer")
def answer_endpoint(request: AnswerRequest) -> dict[str, Any]:
    if not request.use_llm:
        prepared = prepare_search_query(request.query, use_llm=False)
        hits, method = retrieve(
            prepared.search_query,
            num_results=request.num_results,
            method=retrieval_method(),
        )
        return {
            "query": request.query,
            "search_query": prepared.search_query,
            "language": prepared.language,
            "use_llm": False,
            "retrieval": method,
            "answer": None,
            "citations": [_serialize_hit(doc, method) for doc in hits],
        }

    if request.use_tools:
        from app.agent import answer_with_agent

        result = answer_with_agent(request.query, num_results=request.num_results)
    else:
        from app.llm import answer_question

        result = answer_question(request.query, num_results=request.num_results)

    return {
        "query": request.query,
        "search_query": result.search_query,
        "language": result.language,
        "use_llm": True,
        "use_tools": request.use_tools,
        "retrieval": result.retrieval_method,
        "model": result.model,
        "answer": result.answer,
        "citations": result.citations,
        "latency_s": round(result.elapsed_time, 3),
        "log_id": result.log_id,
        "tokens": {
            "prompt": result.prompt_tokens,
            "completion": result.completion_tokens,
            "total": result.total_tokens,
        },
    }
