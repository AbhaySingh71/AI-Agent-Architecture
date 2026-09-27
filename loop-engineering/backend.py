import os
from typing import Literal, TypedDict

from ddgs import DDGS
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_REVISIONS = int(os.getenv("MAX_REVISIONS", "2"))

model = ChatGroq(
    model=MODEL,
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)


def search_duckduckgo(query: str, max_results: int = 3) -> str:
    """Fetch live web search context using DuckDuckGo."""
    try:
        results = list(DDGS().text(query, max_results=max_results))
        if not results:
            return "No web search results found for this topic."
        formatted = []
        for idx, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            body = r.get("body", "No summary available.")
            href = r.get("href", "")
            formatted.append(f"Source [{idx}]: {title}\nSummary: {body}\nURL: {href}")
        return "\n\n".join(formatted)
    except Exception as exc:
        return f"Web search error: {str(exc)}"


# --- Evaluator Structured Schemas ---
class FactReview(BaseModel):
    decision: Literal["PASS", "REVISE"] = Field(
        description="PASS if all claims match factual search context; otherwise REVISE."
    )
    feedback: str = Field(
        description="Specific feedback regarding factual errors or missing core concepts."
    )


class ClarityReview(BaseModel):
    decision: Literal["PASS", "REVISE"] = Field(
        description="PASS if beginner-friendly with a clear everyday analogy; otherwise REVISE."
    )
    feedback: str = Field(
        description="Specific feedback on tone simplicity or analogy quality."
    )


class StructureReview(BaseModel):
    decision: Literal["PASS", "REVISE"] = Field(
        description="PASS if focused on topic, concise (120-170 words), with a tiny concrete example."
    )
    feedback: str = Field(
        description="Specific feedback regarding focus, length, or example quality."
    )


class ConsensusDecision(BaseModel):
    decision: Literal["PASS", "REVISE"] = Field(
        description="PASS if overall answer is acceptable; REVISE if any major issues remain."
    )
    action_plan: str = Field(
        description="Unified, prioritized instructions for the reviser."
    )


fact_evaluator_model = model.with_structured_output(FactReview)
clarity_evaluator_model = model.with_structured_output(ClarityReview)
structure_evaluator_model = model.with_structured_output(StructureReview)
consensus_judge_model = model.with_structured_output(ConsensusDecision)


class State(TypedDict):
    topic: str
    search_context: str
    draft: str
    fact_review: dict
    clarity_review: dict
    structure_review: dict
    consensus_decision: str
    synthesized_feedback: str
    revision_count: int


def web_search_node(state: State):
    """Step 1: Gather ground-truth context via DuckDuckGo Search."""
    context = search_duckduckgo(state["topic"])
    return {"search_context": context}


def writer_node(state: State):
    """Step 2: Generate initial draft using web search context."""
    response = model.invoke(
        [
            {
                "role": "system",
                "content": (
                    "You are an expert teacher. Write a beginner-friendly explanation of the topic in 120-160 words.\n"
                    "Use the provided Web Search Context for factual accuracy.\n"
                    "Requirements:\n"
                    "1. Simple, clear tone.\n"
                    "2. One everyday analogy.\n"
                    "3. One tiny concrete example.\n"
                    "4. Accurate facts grounded in search results."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Topic: {state['topic']}\n\n"
                    f"Web Search Context:\n{state['search_context']}"
                ),
            },
        ]
    )
    return {
        "draft": response.content,
        "fact_review": {},
        "clarity_review": {},
        "structure_review": {},
        "consensus_decision": "",
        "synthesized_feedback": "",
        "revision_count": 0,
    }


def fact_checker_evaluator(state: State):
    """Jury Member 1: Verifies factual accuracy against DuckDuckGo web results."""
    review = fact_evaluator_model.invoke(
        [
            {
                "role": "system",
                "content": (
                    "You are a strict Fact-Checker Evaluator. Verify if the draft is factually accurate "
                    "and matches the Web Search Context. If incorrect or misleading, select REVISE with feedback."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Topic: {state['topic']}\n"
                    f"Search Context:\n{state['search_context']}\n\n"
                    f"Draft:\n{state['draft']}"
                ),
            },
        ]
    )
    return {"fact_review": {"decision": review.decision, "feedback": review.feedback}}


def clarity_evaluator(state: State):
    """Jury Member 2: Evaluates beginner simplicity and analogy quality."""
    review = clarity_evaluator_model.invoke(
        [
            {
                "role": "system",
                "content": (
                    "You are a Pedagogy & Clarity Evaluator. Check if the draft is easy for a beginner "
                    "and contains an effective everyday analogy. If jargon is unexplained or analogy is missing/weak, select REVISE."
                ),
            },
            {
                "role": "user",
                "content": f"Topic: {state['topic']}\n\nDraft:\n{state['draft']}",
            },
        ]
    )
    return {"clarity_review": {"decision": review.decision, "feedback": review.feedback}}


def structure_evaluator(state: State):
    """Jury Member 3: Checks topic focus, length budget, and concrete example."""
    review = structure_evaluator_model.invoke(
        [
            {
                "role": "system",
                "content": (
                    "You are a Structural Evaluator. Check if the draft is focused, stays within 120-170 words, "
                    "and includes a tiny concrete example. Select REVISE if any check fails."
                ),
            },
            {
                "role": "user",
                "content": f"Topic: {state['topic']}\n\nDraft:\n{state['draft']}",
            },
        ]
    )
    return {"structure_review": {"decision": review.decision, "feedback": review.feedback}}


def consensus_judge(state: State):
    """Jury Aggregator Node: Combines feedback from all 3 evaluators and issues final verdict."""
    judge = consensus_judge_model.invoke(
        [
            {
                "role": "system",
                "content": (
                    "You are the Chief Consensus Judge. Review the evaluations from 3 jury members:\n"
                    "1. Fact Checker Evaluator\n"
                    "2. Pedagogy & Clarity Evaluator\n"
                    "3. Structural Evaluator\n\n"
                    "If all 3 pass or only minor trivial remarks exist, output PASS.\n"
                    "If any evaluator flagged a real issue, output REVISE and synthesize a clear 2-bullet action plan for the reviser."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Topic: {state['topic']}\n\n"
                    f"Fact Checker Review: {state['fact_review']}\n"
                    f"Clarity Review: {state['clarity_review']}\n"
                    f"Structure Review: {state['structure_review']}\n\n"
                    f"Current Draft:\n{state['draft']}"
                ),
            },
        ]
    )
    return {
        "consensus_decision": judge.decision,
        "synthesized_feedback": judge.action_plan,
    }


def reviser_node(state: State):
    """Improves draft based on Jury Consensus Action Plan & DuckDuckGo context."""
    response = model.invoke(
        [
            {
                "role": "system",
                "content": (
                    "You are an expert Reviser. Improve the answer incorporating the Jury Consensus Action Plan "
                    "and ensuring search facts are respected. Return ONLY the improved answer text."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Topic: {state['topic']}\n\n"
                    f"Web Search Context:\n{state['search_context']}\n\n"
                    f"Current Draft:\n{state['draft']}\n\n"
                    f"Jury Action Plan:\n{state['synthesized_feedback']}"
                ),
            },
        ]
    )
    return {
        "draft": response.content,
        "revision_count": state["revision_count"] + 1,
    }


def route_after_consensus(state: State):
    """Route based on Jury Verdict & Revision Limits."""
    if state["consensus_decision"] == "PASS":
        return "done"
    if state["revision_count"] >= MAX_REVISIONS:
        return "done"
    return "revise"


# Build state graph
builder = StateGraph(State)
builder.add_node("web_search", web_search_node)
builder.add_node("writer", writer_node)
builder.add_node("fact_checker", fact_checker_evaluator)
builder.add_node("clarity_evaluator", clarity_evaluator)
builder.add_node("structure_evaluator", structure_evaluator)
builder.add_node("consensus_judge", consensus_judge)
builder.add_node("reviser", reviser_node)

builder.add_edge(START, "web_search")
builder.add_edge("web_search", "writer")
builder.add_edge("writer", "fact_checker")
builder.add_edge("fact_checker", "clarity_evaluator")
builder.add_edge("clarity_evaluator", "structure_evaluator")
builder.add_edge("structure_evaluator", "consensus_judge")

builder.add_conditional_edges(
    "consensus_judge",
    route_after_consensus,
    {"revise": "reviser", "done": END},
)
builder.add_edge("reviser", "fact_checker")

graph = builder.compile()


def run_workflow(topic: str):
    """Run graph and stream update events for UI and CLI."""
    initial_state: State = {
        "topic": topic,
        "search_context": "",
        "draft": "",
        "fact_review": {},
        "clarity_review": {},
        "structure_review": {},
        "consensus_decision": "",
        "synthesized_feedback": "",
        "revision_count": 0,
    }

    final_state = initial_state.copy()
    events = []

    for update in graph.stream(initial_state, stream_mode="updates"):
        for node_name, values in update.items():
            final_state.update(values)

            # Emit node-specific event object to prevent draft leakage across evaluators
            event_data = {
                "agent": node_name,
                "revision_count": final_state.get("revision_count", 0),
            }

            if node_name == "web_search":
                event_data["search_context"] = values.get("search_context", "")
            elif node_name in {"writer", "reviser"}:
                event_data["draft"] = values.get("draft", "")
            elif node_name == "fact_checker":
                event_data["fact_review"] = values.get("fact_review", {})
            elif node_name == "clarity_evaluator":
                event_data["clarity_review"] = values.get("clarity_review", {})
            elif node_name == "structure_evaluator":
                event_data["structure_review"] = values.get("structure_review", {})
            elif node_name == "consensus_judge":
                event_data["consensus_decision"] = values.get("consensus_decision", "")
                event_data["synthesized_feedback"] = values.get("synthesized_feedback", "")

            events.append(event_data)

    return {
        "topic": topic,
        "events": events,
        "search_context": final_state["search_context"],
        "final_answer": final_state["draft"],
        "final_decision": final_state["consensus_decision"],
        "revision_count": final_state["revision_count"],
        "provider": "Groq",
        "model": MODEL,
    }



def run_demo(topic: str):
    """CLI runner for testing graph execution directly."""
    result = run_workflow(topic)
    print("\n=== MULTI-ASPECT EVALUATOR JURY & DUCKDUCKGO SEARCH AGENT ===")
    print(f"Provider: {result['provider']} ({result['model']})")
    print(f"Topic: {topic}\n")

    print("\n--- DUCKDUCKGO WEB SEARCH CONTEXT ---")
    print(result["search_context"][:400] + "...")

    for event in result["events"]:
        agent = event["agent"]
        print(f"\n>>> NODE: {agent.upper()}")
        if agent == "web_search":
            print("Web Search complete.")
        elif agent in {"writer", "reviser"}:
            print("Draft Output:")
            print(event["draft"])
        elif agent == "fact_checker":
            print(f"Fact Review: {event['fact_review']}")
        elif agent == "clarity_evaluator":
            print(f"Clarity Review: {event['clarity_review']}")
        elif agent == "structure_evaluator":
            print(f"Structure Review: {event['structure_review']}")
        elif agent == "consensus_judge":
            print(f"Verdict: {event['consensus_decision']}")
            print(f"Action Plan: {event['synthesized_feedback']}")

    print("\n=== FINAL ACCEPTED ANSWER ===")
    print(result["final_answer"])
    print(f"\nFinal Verdict: {result['final_decision']}")
    print(f"Revisions Used: {result['revision_count']}")


if __name__ == "__main__":
    topic = input("Enter a topic (e.g. What is Quantum Computing?): ").strip()
    if not topic:
        topic = "What is Quantum Computing?"
    run_demo(topic)

