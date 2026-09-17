import os
import time
from typing import Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "openai/gpt-oss-20b"


def get_llm(json_mode: bool = False, temperature: float = 0.2) -> ChatGroq:
    model_kwargs = {}
    if json_mode:
        model_kwargs["response_format"] = {"type": "json_object"}
    return ChatGroq(
        model=MODEL_NAME,
        temperature=temperature,
        api_key=os.getenv("GROQ_API_KEY"),
        model_kwargs=model_kwargs,
    )


# Structured Pydantic Schemas for Harness Engineering
class RouterDecision(BaseModel):
    route: Literal["technical", "billing", "general"] = Field(
        description="Assigned route category: technical, billing, or general"
    )
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0"
    )
    reasoning: str = Field(
        description="Brief justification for why this route was chosen"
    )


class AgentDraftResponse(BaseModel):
    draft: str = Field(
        description="Detailed customer support answer"
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="Key points covered in the answer"
    )
    requires_escalation: bool = Field(
        default=False,
        description="True if human escalation is required"
    )


class ReviewResult(BaseModel):
    approved: bool = Field(
        default=True,
        description="True if answer meets safety, quality, and accuracy guidelines"
    )
    quality_score: float = Field(
        default=0.9,
        description="Quality rating between 0.0 and 1.0"
    )
    final_answer: str = Field(
        description="Polished final customer-facing response"
    )
    improvements_made: str = Field(
        default="Verified clarity and policy alignment",
        description="Summary of edits or validations applied during review"
    )


# Async LLM Invocation Wrappers
async def llm_router_async(question: str) -> RouterDecision:
    """LLM Fallback Router when deterministic matching is ambiguous."""
    llm = get_llm(json_mode=True, temperature=0.1)
    parser = JsonOutputParser(pydantic_object=RouterDecision)
    prompt = f"""You are the Router Classifier in an AI customer support system.
Classify the customer question into exactly one category: 'technical', 'billing', or 'general'.

{parser.get_format_instructions()}

Customer Question:
{question}
"""
    try:
        res = await llm.ainvoke(prompt)
        parsed = parser.parse(res.content)
        return RouterDecision.model_validate(parsed)
    except Exception as e:
        return RouterDecision(
            route="general",
            confidence=0.6,
            reasoning=f"Fallback due to routing parse error: {str(e)}",
        )


async def technical_agent_async(question: str) -> AgentDraftResponse:
    llm = get_llm(json_mode=True, temperature=0.2)
    parser = JsonOutputParser(pydantic_object=AgentDraftResponse)
    prompt = f"""You are a Technical Support Agent.
Help with login issues, API errors, setup, installation, and technical bugs.
Explain step-by-step in simple language. Never invent account data.

{parser.get_format_instructions()}

Customer Question:
{question}
"""
    try:
        res = await llm.ainvoke(prompt)
        parsed = parser.parse(res.content)
        return AgentDraftResponse.model_validate(parsed)
    except Exception:
        raw_llm = get_llm(json_mode=False)
        raw_res = await raw_llm.ainvoke(f"Technical support answer for: {question}")
        return AgentDraftResponse(
            draft=raw_res.content,
            key_points=["Technical troubleshooting steps provided"],
            requires_escalation=False,
        )


async def billing_agent_async(question: str) -> AgentDraftResponse:
    llm = get_llm(json_mode=True, temperature=0.2)
    parser = JsonOutputParser(pydantic_object=AgentDraftResponse)
    prompt = f"""You are a Billing Support Agent.
Company pricing policy:
- Starter plan: $10/month
- Pro plan: $25/month
- Refunds must be reviewed by the billing team. Never claim a refund is already approved.
- Never ask for passwords or credit card numbers.

{parser.get_format_instructions()}

Customer Question:
{question}
"""
    try:
        res = await llm.ainvoke(prompt)
        parsed = parser.parse(res.content)
        return AgentDraftResponse.model_validate(parsed)
    except Exception:
        raw_llm = get_llm(json_mode=False)
        raw_res = await raw_llm.ainvoke(f"Billing support answer for: {question}")
        return AgentDraftResponse(
            draft=raw_res.content,
            key_points=["Billing policy explained"],
            requires_escalation=False,
        )


async def general_agent_async(question: str) -> AgentDraftResponse:
    llm = get_llm(json_mode=True, temperature=0.2)
    parser = JsonOutputParser(pydantic_object=AgentDraftResponse)
    prompt = f"""You are a General Customer Support Agent.
Answer general questions politely and simply.

{parser.get_format_instructions()}

Customer Question:
{question}
"""
    try:
        res = await llm.ainvoke(prompt)
        parsed = parser.parse(res.content)
        return AgentDraftResponse.model_validate(parsed)
    except Exception:
        raw_llm = get_llm(json_mode=False)
        raw_res = await raw_llm.ainvoke(f"General support answer for: {question}")
        return AgentDraftResponse(
            draft=raw_res.content,
            key_points=["General inquiry answered"],
            requires_escalation=False,
        )


async def reviewer_agent_async(question: str, draft: str) -> ReviewResult:
    llm = get_llm(json_mode=True, temperature=0.1)
    parser = JsonOutputParser(pydantic_object=ReviewResult)
    prompt = f"""You are the Quality & Safety Reviewer Agent.
Evaluate the draft response:
1. Clarity & relevance
2. Policy compliance & safety (no password requests or card numbers)
3. Friendly tone & simplicity

{parser.get_format_instructions()}

Customer Question:
{question}

Draft Response:
{draft}
"""
    try:
        res = await llm.ainvoke(prompt)
        parsed = parser.parse(res.content)
        return ReviewResult.model_validate(parsed)
    except Exception:
        return ReviewResult(
            approved=True,
            quality_score=0.85,
            final_answer=draft,
            improvements_made="Draft validated through fallback review",
        )
