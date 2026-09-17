import re
import time
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

from agents import (
    llm_router_async,
    technical_agent_async,
    billing_agent_async,
    general_agent_async,
    reviewer_agent_async,
)


class NodeMetric(TypedDict):
    node: str
    latency_ms: float
    mode: str
    details: str


class SupportState(TypedDict):
    question: str
    route: str
    route_mode: str  # "deterministic" or "llm_fallback"
    route_confidence: float
    draft: str
    final_answer: str
    blocked: bool
    quality_score: float
    node_metrics: list[NodeMetric]
    trace: list[str]


async def guardrail_node(state: SupportState):
    """
    Deterministic safety & compliance guardrail layer.
    Enforces password safety, credential checks, and credit card regex filters.
    """
    start_time = time.perf_counter()
    question = state["question"].lower()

    dangerous_phrases = [
        "give me your password",
        "steal password",
        "full credit card number",
        "how to change or reset password?",
        "steal credentials",
        "bypass security",
    ]

    card_pattern = r"\b(?:\d[ -]*?){13,16}\b"
    has_card = bool(re.search(card_pattern, state["question"]))

    blocked = any(phrase in question for phrase in dangerous_phrases) or has_card
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    trace_msg = (
        f"[Guardrail] BLOCKED request - Safety violation detected in {elapsed_ms}ms"
        if blocked
        else f"[Guardrail] Passed safety checks in {elapsed_ms}ms"
    )

    metric: NodeMetric = {
        "node": "Guardrail",
        "latency_ms": elapsed_ms,
        "mode": "deterministic",
        "details": "Blocked unsafe request" if blocked else "Passed safety checks",
    }

    metrics = state.get("node_metrics", []) + [metric]
    trace = state.get("trace", []) + [trace_msg]

    if blocked:
        return {
            "blocked": True,
            "final_answer": (
                "Request Blocked: I cannot fulfill requests involving passwords, "
                "stolen credentials, full payment card numbers, or security bypasses."
            ),
            "quality_score": 0.0,
            "node_metrics": metrics,
            "trace": trace,
        }

    return {
        "blocked": False,
        "node_metrics": metrics,
        "trace": trace,
    }


def after_guardrail(state: SupportState) -> Literal["router", "end"]:
    if state["blocked"]:
        return "end"
    return "router"


async def router_node(state: SupportState):
    """
    Hybrid Router:
    1. Checks deterministic keyword matching for unambiguous queries.
    2. Falls back to structured LLM classification when query is ambiguous.
    """
    start_time = time.perf_counter()
    question = state["question"].lower()

    technical_words = [
        "error", "bug", "login", "api", "install",
        "installation", "code", "server", "technical", "stacktrace", "crash"
    ]
    billing_words = [
        "price", "pricing", "payment", "refund", "bill",
        "billing", "subscription", "plan", "charged", "invoice", "cost"
    ]

    tech_matches = [w for w in technical_words if w in question]
    billing_matches = [w for w in billing_words if w in question]

    if tech_matches and not billing_matches:
        route = "technical"
        route_mode = "deterministic"
        confidence = 1.0
        reasoning = f"Unambiguous keyword match ({', '.join(tech_matches)})"
    elif billing_matches and not tech_matches:
        route = "billing"
        route_mode = "deterministic"
        confidence = 1.0
        reasoning = f"Unambiguous keyword match ({', '.join(billing_matches)})"
    else:
        # Ambiguous query -> Trigger LLM Fallback Router
        llm_decision = await llm_router_async(state["question"])
        route = llm_decision.route
        route_mode = "llm_fallback"
        confidence = llm_decision.confidence
        reasoning = llm_decision.reasoning

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    mode_label = "Deterministic" if route_mode == "deterministic" else "LLM Fallback"

    trace_msg = (
        f"[Router ({mode_label})] Selected '{route}' (Confidence: {int(confidence * 100)}%) - "
        f"{reasoning} in {elapsed_ms}ms"
    )

    metric: NodeMetric = {
        "node": "Router",
        "latency_ms": elapsed_ms,
        "mode": route_mode,
        "details": f"Routed to {route} ({confidence:.0%}) via {mode_label}",
    }

    return {
        "route": route,
        "route_mode": route_mode,
        "route_confidence": confidence,
        "node_metrics": state.get("node_metrics", []) + [metric],
        "trace": state.get("trace", []) + [trace_msg],
    }


def choose_agent(state: SupportState) -> Literal[
    "technical_agent", "billing_agent", "general_agent"
]:
    if state["route"] == "technical":
        return "technical_agent"
    if state["route"] == "billing":
        return "billing_agent"
    return "general_agent"


async def technical_node(state: SupportState):
    start_time = time.perf_counter()
    agent_res = await technical_agent_async(state["question"])
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    metric: NodeMetric = {
        "node": "Technical Agent",
        "latency_ms": elapsed_ms,
        "mode": "structured_llm",
        "details": f"Draft generated with {len(agent_res.key_points)} key points",
    }

    return {
        "draft": agent_res.draft,
        "node_metrics": state.get("node_metrics", []) + [metric],
        "trace": state.get("trace", []) + [f"[Technical Agent] Draft generated in {elapsed_ms}ms"],
    }


async def billing_node(state: SupportState):
    start_time = time.perf_counter()
    agent_res = await billing_agent_async(state["question"])
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    metric: NodeMetric = {
        "node": "Billing Agent",
        "latency_ms": elapsed_ms,
        "mode": "structured_llm",
        "details": f"Draft generated with {len(agent_res.key_points)} key points",
    }

    return {
        "draft": agent_res.draft,
        "node_metrics": state.get("node_metrics", []) + [metric],
        "trace": state.get("trace", []) + [f"[Billing Agent] Draft generated in {elapsed_ms}ms"],
    }


async def general_node(state: SupportState):
    start_time = time.perf_counter()
    agent_res = await general_agent_async(state["question"])
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    metric: NodeMetric = {
        "node": "General Agent",
        "latency_ms": elapsed_ms,
        "mode": "structured_llm",
        "details": f"Draft generated with {len(agent_res.key_points)} key points",
    }

    return {
        "draft": agent_res.draft,
        "node_metrics": state.get("node_metrics", []) + [metric],
        "trace": state.get("trace", []) + [f"[General Agent] Draft generated in {elapsed_ms}ms"],
    }


async def reviewer_node(state: SupportState):
    start_time = time.perf_counter()
    review_res = await reviewer_agent_async(
        question=state["question"],
        draft=state["draft"],
    )
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    metric: NodeMetric = {
        "node": "Reviewer Agent",
        "latency_ms": elapsed_ms,
        "mode": "structured_validation",
        "details": f"Score: {review_res.quality_score:.2f} | Approved: {review_res.approved}",
    }

    trace_msg = (
        f"[Reviewer Agent] Validated response (Quality Score: {int(review_res.quality_score * 100)}%) - "
        f"{review_res.improvements_made} in {elapsed_ms}ms"
    )

    return {
        "final_answer": review_res.final_answer,
        "quality_score": review_res.quality_score,
        "node_metrics": state.get("node_metrics", []) + [metric],
        "trace": state.get("trace", []) + [trace_msg],
    }


builder = StateGraph(SupportState)

builder.add_node("guardrail", guardrail_node)
builder.add_node("router", router_node)
builder.add_node("technical_agent", technical_node)
builder.add_node("billing_agent", billing_node)
builder.add_node("general_agent", general_node)
builder.add_node("reviewer", reviewer_node)

builder.add_edge(START, "guardrail")

builder.add_conditional_edges(
    "guardrail",
    after_guardrail,
    {
        "router": "router",
        "end": END,
    },
)

builder.add_conditional_edges(
    "router",
    choose_agent,
    {
        "technical_agent": "technical_agent",
        "billing_agent": "billing_agent",
        "general_agent": "general_agent",
    },
)

builder.add_edge("technical_agent", "reviewer")
builder.add_edge("billing_agent", "reviewer")
builder.add_edge("general_agent", "reviewer")
builder.add_edge("reviewer", END)

support_graph = builder.compile()


async def run_support_system_async(question: str):
    start_time = time.perf_counter()
    initial_state: SupportState = {
        "question": question,
        "route": "",
        "route_mode": "deterministic",
        "route_confidence": 1.0,
        "draft": "",
        "final_answer": "",
        "blocked": False,
        "quality_score": 0.0,
        "node_metrics": [],
        "trace": [],
    }

    result = await support_graph.ainvoke(initial_state)
    total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return {
        "route": result.get("route", "blocked"),
        "route_mode": result.get("route_mode", "deterministic"),
        "route_confidence": round(result.get("route_confidence", 1.0), 2),
        "answer": result["final_answer"],
        "blocked": result.get("blocked", False),
        "quality_score": round(result.get("quality_score", 0.9), 2),
        "total_latency_ms": total_latency_ms,
        "node_metrics": result.get("node_metrics", []),
        "trace": result.get("trace", []),
    }
