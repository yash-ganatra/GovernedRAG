#!/usr/bin/env python3
"""
compliance_agent.py — Phase 3: ReAct Execution Loop for Compliance Auditing
============================================================================

Replaces the hardcoded SequentialChain with a ReAct-style agent that
AUTONOMOUSLY decides when to call:

    Tool A  (PolicySearch)   → Search ChromaDB for regulatory text
    Tool B  (LogAnalyzer)    → Query inference_log for operational metrics

The agent follows a structured 5-step compliance reasoning protocol
embedded in its system prompt, but dynamically chooses which tools to
invoke and how many times based on the query.

Flow:
    1. DECOMPOSE — Agent parses the regulatory query
    2. RETRIEVE  — Agent calls PolicySearch (Tool A)
    3. EVIDENCE  — Agent calls LogAnalyzer (Tool B)
    4. GAP ANALYSIS — Agent compares policy vs evidence
    5. ADJUDICATE — Agent produces the final structured report
"""

# ── Fix macOS OpenBLAS / SciPy deadlock ──────────────────────────────────
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import sys
import json
from datetime import datetime, timezone
from typing import Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from agents.retrieval_tools import ALL_TOOLS

# Load environment variables from .env file
load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# ═══════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT — Structured 5-Step Compliance Reasoning Protocol
# ═══════════════════════════════════════════════════════════════════════════

AGENT_SYSTEM_PROMPT = PromptTemplate.from_template(
"""You are a Compliance Audit Agent for AI governance systems.

You follow a strict 5-step compliance reasoning protocol:
STEP 1: DECOMPOSE the query (identify regulations, articles, obligations)
STEP 2: RETRIEVE POLICY by calling the PolicySearch tool
STEP 3: GATHER EVIDENCE by calling the LogAnalyzer tool
STEP 4: GAP ANALYSIS — compare policy requirements vs evidence metrics
STEP 5: ADJUDICATE — produce final compliance determination

You have access to these tools:

{tools}

IMPORTANT RULES:
- You MUST call BOTH PolicySearch AND LogAnalyzer tools before producing the final answer
- NEVER fabricate or assume metrics — use ONLY the exact values returned by LogAnalyzer
- The numbers from LogAnalyzer are DETERMINISTIC — do NOT recalculate or modify them
- review_required=True is a POSITIVE oversight signal (system correctly flagging for human review)
- pending_count is the ACTUAL oversight gap (awaiting human action)
- error_rate measures HTTP reliability, NOT oversight quality
- Pay attention to _metadata.sample_size to know how robust the evidence is

Use the following format:

Thought: I need to think about what to do next
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now have enough information from both tools to perform gap analysis and adjudicate
Final Answer: the final JSON compliance report

When you are ready to produce the final answer, output it as valid JSON with this structure:
{{
  "step_1_decomposition": {{
    "regulations": ["..."],
    "articles": ["..."],
    "obligations": ["..."],
    "system_context": "...",
    "query_intent": "..."
  }},
  "step_2_policy_clauses_summary": "Brief summary of retrieved policy clauses",
  "step_3_evidence_summary": "Brief summary of metrics with EXACT values from LogAnalyzer",
  "step_4_gap_analysis": {{
    "gaps": [
      {{
        "obligation": "...",
        "policy_requirement": "...",
        "policy_source": "...",
        "current_evidence": "exact metric name and value from LogAnalyzer",
        "status": "compliant|partial|non_compliant|insufficient_data",
        "gap_description": "..."
      }}
    ],
    "overall_gap_count": 0,
    "critical_gaps": 0
  }},
  "step_5_adjudication": {{
    "overall_status": "COMPLIANT|PARTIALLY_COMPLIANT|NON_COMPLIANT|INSUFFICIENT_DATA",
    "confidence_score": 0.0,
    "summary": "2-3 sentence summary citing specific articles and exact metric values",
    "citations": [
      {{
        "regulation": "...",
        "article": "...",
        "source_document": "...",
        "relevance": "..."
      }}
    ],
    "recommendations": ["specific actionable recommendation citing the exact gap and metric"]
  }}
}}

Begin!

Question: {input}
{agent_scratchpad}""")


# ═══════════════════════════════════════════════════════════════════════════
#  AGENT BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def build_compliance_agent(
    model_name: Optional[str] = None,
    temperature: float = 0.1,
    verbose: bool = True,
) -> AgentExecutor:
    """
    Build and return the ReAct compliance audit agent.

    The agent autonomously:
        1. Decomposes the query
        2. Calls PolicySearch (Tool A) — one or more times
        3. Calls LogAnalyzer (Tool B) — one or more times
        4. Performs gap analysis
        5. Produces structured JSON report
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY is missing or not set in the .env file. "
            "Please paste your valid Groq API key into the .env file."
        )

    llm = ChatGroq(
        model_name=model_name or GROQ_MODEL,
        temperature=temperature,
        api_key=api_key,
    )

    # Create ReAct agent with our tools and structured prompt
    agent = create_react_agent(
        llm=llm,
        tools=ALL_TOOLS,
        prompt=AGENT_SYSTEM_PROMPT,
    )

    # Wrap in AgentExecutor with error handling
    executor = AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=verbose,
        handle_parsing_errors=True,
        max_iterations=10,        # Allow multiple tool calls
        max_execution_time=120,   # 2-minute timeout
        return_intermediate_steps=True,
    )

    return executor


# ═══════════════════════════════════════════════════════════════════════════
#  EXECUTION LOOP
# ═══════════════════════════════════════════════════════════════════════════

def run_agent_audit(
    query: str,
    model_name: Optional[str] = None,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Run the Phase 3 compliance audit via the ReAct agent.

    Parameters
    ----------
    query : str
        The regulatory compliance question.
    model_name : str, optional
        Groq model name (default: llama-3.3-70b-versatile).
    verbose : bool
        Whether to print the agent's reasoning trace.

    Returns
    -------
    dict
        Full compliance report with all 5 reasoning steps,
        plus the agent's intermediate tool-call trace.
    """
    executor = build_compliance_agent(model_name=model_name, verbose=verbose)

    # Generate deterministic audit metadata in Python
    now_utc = datetime.now(timezone.utc)
    audit_id = f"AUDIT-{now_utc.strftime('%Y%m%d-%H%M%S')}"
    audit_timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"\n{'='*70}")
    print("  COMPLIANCE AUDIT AGENT — Phase 3 Execution Loop")
    print(f"{'='*70}")
    print(f"  Audit ID: {audit_id}")
    print(f"  Query:    \"{query}\"")
    print(f"  Model:    {model_name or GROQ_MODEL}")
    print(f"  Time:     {audit_timestamp}")
    print(f"{'='*70}\n")

    # Execute the agent
    result = executor.invoke({"input": query})

    # Extract the agent's final answer
    raw_output = result.get("output", "")

    # Parse the structured JSON from the agent's output
    parsed_report = _safe_parse_json(raw_output)

    # Inject deterministic metadata
    if isinstance(parsed_report, dict) and "step_5_adjudication" in parsed_report:
        parsed_report["step_5_adjudication"]["audit_id"] = audit_id
        parsed_report["step_5_adjudication"]["timestamp"] = audit_timestamp

    # Build the full report with agent trace
    tool_trace = []
    for step in result.get("intermediate_steps", []):
        action, observation = step
        tool_trace.append({
            "tool": action.tool,
            "input": action.tool_input,
            "output_preview": str(observation)[:300] + "..." if len(str(observation)) > 300 else str(observation),
        })

    report = {
        "audit_metadata": {
            "audit_id": audit_id,
            "query": query,
            "model": model_name or GROQ_MODEL,
            "timestamp": audit_timestamp,
            "pipeline_version": "3.0.0",
            "execution_mode": "react_agent",
            "tools_called": len(tool_trace),
        },
        "agent_tool_trace": tool_trace,
        "compliance_report": parsed_report,
    }

    return report


def _safe_parse_json(text: str) -> Any:
    """Try to parse JSON from text, falling back to raw string."""
    import re
    if not text:
        return {"raw_output": ""}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON block in markdown code fences
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        # Try bare JSON object
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_output": text}
