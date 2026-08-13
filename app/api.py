"""FastAPI Product + Integrate: UI, /health, /search, /answer, /feedback, /docs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import load_app_env, retrieval_method
from app.hybrid import retrieve
from app.query import prepare_search_query

load_app_env()

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DIR = ROOT / "product"
STATIC_DIR = PRODUCT_DIR / "static"

app = FastAPI(
    title="Policy & Refund Support Agent",
    description=(
        "Zakard Shop policy RAG — Product UI + Integrate API "
        "(hybrid search, grounded answers, optional agent tools)."
    ),
    version="0.2.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("PRA_CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/docs", include_in_schema=False)
def integrate_docs() -> HTMLResponse:
    """Swagger UI with Product/Grafana-matching dark theme."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title="Integrate · Policy & Refund Support Agent",
        swagger_css_url="/static/swagger-dark.css?v=1",
        swagger_ui_parameters={
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "syntaxHighlight.theme": "obsidian",
        },
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


class FeedbackRequest(BaseModel):
    log_id: int
    feedback: int = Field(..., description="+1 helpful or -1 not helpful")
    comment: str | None = None


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


@app.get("/")
def product_home() -> FileResponse:
    index = PRODUCT_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Product UI not packaged")
    return FileResponse(index)


@app.get("/config")
def product_config() -> dict[str, str]:
    from app.config import get_model_name

    insights = os.getenv(
        "PRA_INSIGHTS_URL",
        "https://policy-refund-agent-grafana.onrender.com",
    ).rstrip("/")
    # Deep-link the monitoring dashboard (anonymous Viewer on Render).
    if "/d/" not in insights:
        insights = f"{insights}/d/pra-agent-monitoring/pra-agent-monitoring?orgId=1"
    try:
        model = get_model_name()
    except Exception:  # noqa: BLE001
        model = os.getenv("LLM_MODEL") or os.getenv("CEREBRAS_MODEL") or "unknown"
    return {
        "insights_url": insights,
        "github_url": os.getenv(
            "PRA_GITHUB_URL",
            "https://github.com/zakard114/policy-refund-agent",
        ),
        "integrate_path": "/docs",
        "model": model,
        "retrieval": retrieval_method(),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "policy-refund-agent"}


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


@app.post("/feedback")
def feedback_endpoint(request: FeedbackRequest) -> dict[str, Any]:
    if request.feedback not in (1, -1):
        raise HTTPException(status_code=400, detail="feedback must be +1 or -1")
    from app.database import save_feedback

    ok = save_feedback(
        log_id=request.log_id,
        feedback=request.feedback,
        comment=request.comment,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="log_id not found or DB unavailable")
    return {"ok": True, "log_id": request.log_id, "feedback": request.feedback}
