"""Agent tools: policy search + mock order lookup / refund evaluation (Part 6-1)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import DATA_DIR, retrieval_method
from app.hybrid import retrieve

ORDERS_PATH = DATA_DIR / "mock_orders.json"
REFUND_WINDOW_DAYS = 7

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": (
                "Search the Zakard Shop refund & return policy for relevant sections. "
                "Use for policy questions (deadlines, process, non-refundable rules, support hours)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords from the customer question.",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "How many policy sections to return (1-5).",
                        "default": 3,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": (
                "Look up a mock customer order by order_id (e.g. ZK-1001). "
                "Returns delivery age, product condition, and related fields."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order id such as ZK-1001.",
                    }
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_refund",
            "description": (
                "Apply Zakard Shop refund rules to a mock order and return "
                "eligible | ineligible | need_more_info with reasons. "
                "Call after lookup_order (or with a known order_id)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order id such as ZK-1001.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Customer refund reason (e.g. change_of_mind, defect).",
                        "default": "change_of_mind",
                    },
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
]


@lru_cache(maxsize=1)
def _load_orders() -> dict[str, dict[str, Any]]:
    path = Path(ORDERS_PATH)
    payload = json.loads(path.read_text(encoding="utf-8"))
    orders = payload.get("orders") or []
    return {str(o["order_id"]).upper(): o for o in orders}


def search_policy(query: str, num_results: int = 3) -> dict[str, Any]:
    """Wrap hybrid/keyword retrieval for the agent."""
    n = max(1, min(int(num_results or 3), 5))
    results, used_method = retrieve(
        query,
        num_results=n,
        method=retrieval_method(),
    )
    hits = [
        {
            "id": doc.get("id", ""),
            "section": doc.get("section", ""),
            "text": (doc.get("text") or "").strip(),
            "rrf_score": doc.get("rrf_score"),
        }
        for doc in results
    ]
    return {"retrieval": used_method, "results": hits}


def lookup_order(order_id: str) -> dict[str, Any]:
    """Return one mock order or a not-found payload."""
    key = (order_id or "").strip().upper()
    order = _load_orders().get(key)
    if not order:
        return {
            "found": False,
            "order_id": key,
            "message": f"No mock order found for {key}. Known ids: {', '.join(sorted(_load_orders()))}",
        }
    return {"found": True, "order": dict(order)}


def evaluate_refund(order_id: str, reason: str = "change_of_mind") -> dict[str, Any]:
    """Rule-based refund decision aligned with data/refund_policy.md (mock only)."""
    looked = lookup_order(order_id)
    if not looked.get("found"):
        return {
            "order_id": (order_id or "").strip().upper(),
            "decision": "need_more_info",
            "reasons": ["Order not found in mock DB — confirm the order id with the customer."],
            "policy_refs": ["4. Contact Information"],
        }

    order = looked["order"]
    reasons: list[str] = []
    decision = "eligible"
    policy_refs: list[str] = []

    days = order.get("days_since_delivery")
    condition = (order.get("condition") or "").lower()
    category = (order.get("category") or "").lower()
    label_intact = order.get("label_intact")
    powered_on = order.get("powered_on")
    defect = bool(order.get("defect_reported"))
    reason_l = (reason or "change_of_mind").lower()

    if days is None or condition in {"", "unknown"} or label_intact is None:
        return {
            "order_id": order["order_id"],
            "decision": "need_more_info",
            "reasons": [
                "Delivery date and/or product condition is missing from the order record.",
                "Ask the customer for proof of delivery date and item condition photos.",
            ],
            "policy_refs": ["1. Refund Period", "3. Refund Process"],
            "order": order,
        }

    if int(days) > REFUND_WINDOW_DAYS:
        decision = "ineligible"
        reasons.append(
            f"Refund window is {REFUND_WINDOW_DAYS} days; this order is {days} days after delivery."
        )
        policy_refs.append("1. Refund Period")

    if condition in {"damaged_by_customer", "damaged"}:
        decision = "ineligible"
        reasons.append("Product appears damaged due to customer negligence.")
        policy_refs.append("2. Non-Refundable Conditions")

    if label_intact is False:
        decision = "ineligible"
        reasons.append("Label removed or package opened in a way that diminishes product value.")
        policy_refs.append("2. Non-Refundable Conditions")

    if category == "electronics" and powered_on and not defect and reason_l != "defect":
        decision = "ineligible"
        reasons.append(
            "Electronics were powered on and no product defect was reported — refund not accepted."
        )
        policy_refs.append("2. Non-Refundable Conditions")

    if decision == "eligible":
        reasons.append(
            f"Within {REFUND_WINDOW_DAYS}-day window, condition acceptable for reason '{reason}'."
        )
        reasons.append("Guide the customer through My Page → Request Refund (photos required).")
        policy_refs.extend(["1. Refund Period", "3. Refund Process"])

    # de-dupe while preserving order
    seen: set[str] = set()
    uniq_refs = []
    for ref in policy_refs:
        if ref not in seen:
            seen.add(ref)
            uniq_refs.append(ref)

    return {
        "order_id": order["order_id"],
        "decision": decision,
        "reasons": reasons,
        "policy_refs": uniq_refs,
        "order": order,
    }


def dispatch_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Run a tool by name; unknown names return an error dict."""
    if name == "search_policy":
        return search_policy(
            query=str(arguments.get("query") or ""),
            num_results=int(arguments.get("num_results") or 3),
        )
    if name == "lookup_order":
        return lookup_order(str(arguments.get("order_id") or ""))
    if name == "evaluate_refund":
        return evaluate_refund(
            order_id=str(arguments.get("order_id") or ""),
            reason=str(arguments.get("reason") or "change_of_mind"),
        )
    return {"error": f"Unknown tool: {name}"}


def list_demo_order_ids() -> list[str]:
    return sorted(_load_orders())
