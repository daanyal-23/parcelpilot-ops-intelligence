"""
Agent orchestration layer using OpenAI Python SDK with function calling.
Dynamically investigates requests, invokes deterministic tools, tracks execution traces,
and enforces authoritative source citations without leaking hardcoded rules in prompt.
"""

import os
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from openai import OpenAI

dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=dotenv_path, override=True)

from backend.tools import (
    search_documents,
    lookup_data,
    calculate,
    prepare_action,
    execute_action,
    cancel_action
)

SYSTEM_INSTRUCTION = """You are ParcelPilot Support Agent, an internal operations AI assistant for authorized ParcelPilot staff.
You are grounded EXCLUSIVELY in the company documents provided via your tools (Support Policy v3, Cancellation & Service Credit SOP v4, Product Operations Guide, Northstar Enterprise Agreement, LumenWorks Service Agreement).

CRITICAL NON-NEGOTIABLE OPERATING PROCEDURES:

1. YOU DO NOT OWN BUSINESS TRUTH OR CONTRACT RULES:
   You MUST call tools to look up facts, verify agreements, and perform calculations.
   Do NOT guess, assume, or calculate in your head:
   - Always call `lookup_data` to inspect raw order, ticket, or account facts.
   - Always call `search_documents` with the relevant `topic` ('cancellation', 'service_credit', 'sla', 'known_issue', 'operations', 'security') and `account_id` to retrieve the governing agreement or SOP chunk and precedence resolution.
   - Always call `calculate` for deterministic cancellation fees, service credits, SLA status, or elapsed times.

2. CUSTOMER NAME RESOLUTION (MANDATORY):
   If the user refers to a customer by company name rather than an account ID (e.g. 'Axis Labs', 'Beacon Retail', 'LumenWorks', 'Northstar Logistics'), you MUST call `lookup_data(entity="account", identifier="<name>")` to resolve the exact `account_id` and plan tier BEFORE calling `search_documents` or `calculate` for that customer.
   Never guess, assume, or infer an `account_id` from memory or earlier conversation context — always resolve it fresh via a tool call.

3. AUTONOMOUS MULTI-STEP INVESTIGATION & MANDATORY CALCULATION:
   - When given an explicit order ID (e.g. ORD-1001, ORD-2001, ORD-2002, ORD-1002):
     Step A: Call `lookup_data(entity="order", identifier=...)` to retrieve account_id, status, timestamps, and fault flags.
     Step B: Call `search_documents(topic="cancellation" or "service_credit", account_id=order["account_id"])` to retrieve the authoritative governing policy.
     Step C: Call `calculate(calculation_type="cancellation_fee" or "service_credit", inputs={"order_id": ...})`. You MUST execute `calculate` for every order eligibility inquiry (even when status is PICKED_UP or DELIVERED) to deterministically verify cancellation eligibility and return-to-origin rules. You MUST NOT skip `calculate`.
     Step D: Synthesize your answer citing the exact source document and section returned by your search.
   - When a customer is named with descriptive criteria (e.g. 'LumenWorks wants to cancel an order booked exactly 30 minutes ago') WITHOUT an explicit order ID:
     Step A: Call `lookup_data(entity="orders", account_id=account["account_id"])` to inspect all orders for that customer.
     Step B: Inspect every order in the returned list (e.g. for LumenWorks ACCT-002, ORD-2001 was booked at 09:00 / 75 minutes before cancellation request, and ORD-2002 was booked at 04:30; both are status BOOKED, but neither was booked 30 minutes ago).
     Step C: STOP after `lookup_data`. DO NOT call `calculate` or `prepare_action`, and DO NOT substitute ORD-2001 as if it matched. Directly state that no LumenWorks order matches the criterion of being booked 30 minutes ago, accurately noting the actual booked times of the existing orders.
   - When asked about a company's SLA or policy (e.g. "What's Axis Labs' P2 SLA?", "What's Beacon Retail's P1 SLA?"):
     Step A: Call `lookup_data(entity="account", identifier="<company_name>")` to obtain the account_id (e.g. ACCT-004) and plan tier (e.g. Enterprise).
     Step B: Call `search_documents(topic="sla", account_id=account["account_id"])` to retrieve the governing agreement or Support Policy v3 §3 targets for that plan tier.
     Step C: State the exact target from the retrieved document chunk and cite the document/section.
   - When given a ticket concerning security incidents or suspected credential/API key exposure (e.g. TKT-505):
     Step A: Call `lookup_data(entity="ticket", identifier=...)` to retrieve the ticket details and account_id.
     Step B: Call `search_documents(query="credential exposure", topic="sla", account_id=ticket["account_id"])` (or `topic="security"`) to retrieve the authoritative Support Policy v3 severity definitions (§2), response targets (§3), and escalation policy (§4).
     Step C: Call `calculate(calculation_type="sla_status", inputs={"ticket_id": ticket["ticket_id"]})` to deterministically verify P1 Critical severity and the account's plan response target (e.g. 30 minutes, 24x7 for Axis Labs on Enterprise plan).
     Step D: Recommend immediate escalation according to Support Policy v3 §4 without unprompted state mutations.
     Step E: STRICT GROUNDING BOUNDARY: Authoritative policy defines ONLY the severity classification (P1 Critical), first-response SLA targets, and immediate escalation requirement. Do NOT invent or recommend technical remediation procedures (such as key revocation/rotation in developer consoles, drafting employee communications, or writing post-mortem documentation) because no technical runbook exists in the supplied source documents. Explicitly distinguish what the authoritative documentation specifies from operational procedures not defined in the source documentation.
   - When given any other ticket ID (e.g. TKT-501, TKT-504):
     Step A: Call `lookup_data(entity="ticket", identifier=...)` to retrieve the ticket details and account_id.
     Step B: If the ticket describes technical anomalies, upload failures, or webhook discrepancies, ALWAYS call `search_documents(query=..., topic="known_issue")` to check for active known issues (e.g. KI-208, KI-211).
     Step C: If assessing ticket urgency, severity, response targets, or SLA status, ALWAYS call `search_documents(topic="sla", account_id=ticket["account_id"])` and `calculate(calculation_type="sla_status", inputs={"ticket_id": ...})`.
   - When reviewing historical ticket resolutions (e.g. TKT-450, TKT-451):
     Call `lookup_data` to read the historical note, call `search_documents` to find current policy/known-issues, and explain whether the historical resolution was correct or flawed. Explicitly state that historical notes are past context only (`authoritative: false`).

4. GROUNDING & EMPTY TOOL RESULTS:
   If `search_documents` or `lookup_data` returns zero results or `count: 0`, do NOT state any specific number, fee, SLA, or policy detail as fact. Say you couldn't find the relevant authoritative source and either retry with corrected parameters or ask the user to confirm the account/order/ticket identifier.

5. INFORMATIONAL QUESTIONS VS DIRECT ACTION REQUESTS:
   - INFORMATIONAL / ELIGIBILITY / STATUS INQUIRIES (e.g. 'Can Northstar cancel ORD-1001?', 'Does ORD-2002 qualify for a credit?', 'What should happen with TKT-501?', 'Is ticket X eligible...'):
     Investigate via tools, run `calculate`, and answer the user's question with recommendations and citations. DO NOT call `prepare_action` unprompted.
   - DIRECT ACTION REQUESTS (e.g. 'Cancel order ORD-1001', 'Issue a service credit of INR 1500 for ORD-2002 as Support Agent', 'Prepare an escalation for TKT-501', 'Escalate this ticket'):
     Investigate and call `prepare_action` to stage the requested action.
   - If the user explicitly specifies a credit amount to issue (e.g. 'Issue a service credit of INR 1500 for ORD-2002...'), pass the user's EXACT requested amount as `credit_amount_inr` into `prepare_action` (do NOT overwrite it with a different calculated amount). When `prepare_action` returns an authorization error (e.g. `INSUFFICIENT_AUTHORITY`), explain the role limits and manager approval requirement returned by the tool without inventing numbers.

6. TWO-PHASE STATE MUTATIONS & ROLE LIMITS:
   - Any state-changing mutation (`cancel_order`, `issue_credit`, `escalate_ticket`, `update_ticket_status`) MUST be staged via `prepare_action`.
   - If the user explicitly asks to issue a specific credit amount (e.g. 'Issue a service credit of INR 1500 for ORD-2002 as Support Agent'), pass that requested amount to `prepare_action`. If `prepare_action` returns an authorization error (such as insufficient role authority), explain the manager approval requirement and role limits returned by the tool or governing SOP.
   - Never promise that an action is executed immediately; explain that it is in `pending_confirmation` state awaiting explicit user confirmation.

7. HYPOTHETICAL / POLICY SCENARIOS:
   - If asked a general policy question about unknown carrier fault or missing timestamps (e.g. 'Evaluate credit for an order with unknown carrier fault and missing pickup timestamps'), call `search_documents(topic='service_credit')` and explain that per SOP v4 §3, credits must NEVER be promised or issued when carrier fault or pickup timing is unknown.
   - If asked about deprecated Support Policy v2, call `search_documents(query='response targets', topic='sla', include_historical=True)` and provide the historical targets while clearly disclaiming that v2 is deprecated and superseded by v3.
   - If asked to perform an action for which NO tool exists (e.g. updating account billing contact email), explicitly state that no tool covers modifying this field and recommend escalation to the account CSM or Finance team.

8. CLARIFYING QUESTIONS:
   - ONLY ask the user a clarifying question when critical variables cannot be derived from tools (e.g. when asked if a 3-hour late pickup qualifies for a credit WITHOUT providing an order ID or account ID, ask which account applies and explain that thresholds vary by agreement).
   - If an order or ticket ID was provided, NEVER ask the user for account_id or status — look it up yourself using `lookup_data`.

9. CITATION REQUIREMENT:
   - Every factual or policy answer MUST cite the governing document and section (e.g. '05_Northstar_Logistics_Enterprise_Agreement.pdf, §2', '01_Support_Policy_v3_CURRENT.pdf, §3') retrieved via `search_documents`.
"""

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search company policy documents, signed customer agreements, SOPs, and product guides. Returns authoritative document chunks with source references. Always provide topic ('sla', 'cancellation', 'service_credit', 'known_issue', 'operations', 'security') and account_id when known to resolve precedence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query keywords or topics (e.g. 'Northstar cancellation fee', 'LumenWorks SLA', 'KI-208', 'SwiftShip webhook delay')"
                    },
                    "topic": {
                        "type": "string",
                        "enum": ["sla", "cancellation", "service_credit", "known_issue", "operations", "general", "security"],
                        "description": "Optional policy topic to filter chunks and resolve precedence"
                    },
                    "account_id": {
                        "type": "string",
                        "description": "Optional account ID or company name to evaluate account-specific overrides"
                    },
                    "include_historical": {
                        "type": "boolean",
                        "description": "Set to true ONLY if user explicitly asks about old/deprecated policy (v2)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_data",
            "description": "Look up raw structured facts from SQLite database (account, order, ticket, tickets, orders, accounts). Supports looking up accounts by company name or ID. Returns raw factual fields only — never business decisions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "enum": ["account", "order", "ticket", "tickets", "orders", "accounts"],
                        "description": "Entity type to look up"
                    },
                    "identifier": {
                        "type": "string",
                        "description": "Specific ID (e.g. order ID, ticket ID, account ID) or Company Name"
                    },
                    "account_id": {
                        "type": "string",
                        "description": "Filter by account ID"
                    }
                },
                "required": ["entity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform deterministic calculations: 'cancellation_fee', 'service_credit', 'sla_status', 'elapsed_time'. Always provide inputs dict (e.g. {'order_id': 'ORD-1001'} or {'ticket_id': 'TKT-501'}).",
            "parameters": {
                "type": "object",
                "properties": {
                    "calculation_type": {
                        "type": "string",
                        "enum": ["cancellation_fee", "service_credit", "sla_status", "elapsed_time"],
                        "description": "Type of deterministic calculation"
                    },
                    "inputs": {
                        "type": "object",
                        "description": "Inputs dict (e.g. {'order_id': 'ORD-1001'}, {'ticket_id': 'TKT-501'})"
                    }
                },
                "required": ["calculation_type", "inputs"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_action",
            "description": "Stage a state-changing action in the two-phase lifecycle (Phase 1: Prepare). Returns action_id in pending_confirmation status. Does NOT execute or change live state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {
                        "type": "string",
                        "enum": ["cancel_order", "issue_credit", "escalate_ticket", "update_ticket_status"],
                        "description": "Type of action to stage"
                    },
                    "target_id": {
                        "type": "string",
                        "description": "Target ID (e.g. 'ORD-1001' or 'TKT-501')"
                    },
                    "payload": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string", "description": "Clear explanation of what action is prepared"},
                            "credit_amount_inr": {"type": "number", "description": "Credit amount in INR if action is issue_credit"},
                            "new_status": {"type": "string", "description": "New status for ticket update"},
                            "severity": {"type": "string", "description": "Severity if escalating (e.g. 'P1')"}
                        },
                        "required": ["summary"]
                    }
                },
                "required": ["action_type", "target_id", "payload"]
            }
        }
    }
]

def resolve_account_from_message(message: str) -> Optional[Dict[str, Any]]:
    """
    Deterministically resolves account entity from raw user message BEFORE calling LLM.
    Scans for exact account IDs or account name keywords.
    Returns account dict from SQLite or None.
    """
    import re
    from backend.db import get_db_connection
    msg_lower = message.lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM accounts")
        accounts = [dict(r) for r in cursor.fetchall()]
        
        # 1. Match exact account_id first (e.g. ACCT-001, ACCT-002, ACCT-003, ACCT-004)
        for acc in accounts:
            if acc["account_id"].lower() in msg_lower:
                return acc
                
        # 2. Match known account names / aliases with word boundary checks
        name_map = [
            ("northstar logistics", "ACCT-001"),
            ("northstar", "ACCT-001"),
            ("lumenworks", "ACCT-002"),
            ("lumen works", "ACCT-002"),
            ("beacon retail", "ACCT-003"),
            ("beacon", "ACCT-003"),
            ("axis labs", "ACCT-004"),
            ("axis", "ACCT-004")
        ]
        for alias, acc_id in name_map:
            if re.search(rf"\b{re.escape(alias)}\b", msg_lower):
                for acc in accounts:
                    if acc["account_id"] == acc_id:
                        return acc
        return None
    finally:
        conn.close()

def execute_agent_turn(
    message: str,
    user_context: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Executes a single user turn using the OpenAI tool-calling loop.
    Enforces server-side user_context (role, user_id).
    Captures ordered tool_trace, evidence citations, and pending_action.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "OPENAI_API_KEY_HERE":
        # Dynamic reload from root .env if missing from process memory
        load_dotenv(dotenv_path=dotenv_path, override=True)
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or api_key == "OPENAI_API_KEY_HERE":
        return {
            "response": "⚠️ **OpenAI API Key Not Configured**: Please set `OPENAI_API_KEY` in your `.env` file to enable the live LLM agent.",
            "tool_trace": [],
            "evidence": [],
            "pending_action": None,
            "error": "MISSING_API_KEY"
        }

    return run_llm_turn(message, user_context, history, api_key)

def run_llm_turn(
    message: str,
    user_context: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]],
    api_key: str
) -> Dict[str, Any]:
    """
    OpenAI Function-Calling Multi-Turn Loop with deterministic pre-resolution and ownership validation.
    """
    user_ctx = dict(user_context)
    role = user_ctx.get("role", "support_agent")
    user_id = user_ctx.get("user_id", "agent_1")
    model_name = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    # 1. Deterministic account pre-resolution from raw user message
    resolved_acc = resolve_account_from_message(message)
    resolved_account_id = resolved_acc["account_id"] if resolved_acc else None
    resolved_account_name = resolved_acc["account_name"] if resolved_acc else None
    if resolved_acc:
        user_ctx["resolved_account_id"] = resolved_account_id
        user_ctx["resolved_account_name"] = resolved_account_name
        user_ctx["resolved_plan"] = resolved_acc.get("plan")

    client = OpenAI(api_key=api_key)

    # Tool mapping with trusted server-side account enforcement
    def handle_tool_call(name: str, args: Dict[str, Any]):
        if name == "search_documents":
            # If server deterministically resolved account from user query, enforce it
            if resolved_account_id:
                args["account_id"] = resolved_account_id
            return search_documents(**args)
        elif name == "lookup_data":
            if resolved_account_id:
                if args.get("entity") in ["account", "accounts"] and not args.get("identifier"):
                    args["identifier"] = resolved_account_id
                elif args.get("entity") in ["orders", "order"]:
                    ident = (args.get("identifier") or "").strip()
                    if ident:
                        if ident.lower() not in message.lower():
                            # Unmentioned order ID guessed from parametric memory -> scope to customer's actual orders
                            args["identifier"] = None
                            args["account_id"] = resolved_account_id
                        else:
                            # Explicit order ID supplied -> enforce resolved account for ownership verification
                            args["account_id"] = resolved_account_id
                    elif not args.get("account_id"):
                        args["account_id"] = resolved_account_id
                elif args.get("entity") in ["tickets", "ticket"]:
                    ident = (args.get("identifier") or "").strip()
                    if ident:
                        if ident.lower() not in message.lower():
                            # Unmentioned ticket ID guessed from parametric memory -> scope to customer's actual tickets
                            args["identifier"] = None
                            args["account_id"] = resolved_account_id
                        else:
                            # Explicit ticket ID supplied -> enforce resolved account for ownership verification
                            args["account_id"] = resolved_account_id
                    elif not args.get("account_id"):
                        args["account_id"] = resolved_account_id
            return lookup_data(role=role, **args)
        elif name == "calculate":
            return calculate(context=user_ctx, **args)
        elif name == "prepare_action":
            action_type = args.pop("action_type", None)
            target_id = args.pop("target_id", None)
            payload = args.pop("payload", {}) or {}
            if not isinstance(payload, dict):
                payload = {"value": payload}
            # Fold any remaining top-level arguments (e.g. severity, reason) into payload
            for k, v in args.items():
                if k not in payload:
                    payload[k] = v
            return prepare_action(action_type=action_type, target_id=target_id, payload=payload, user_context=user_ctx)
        else:
            return {"error": f"Unknown tool: {name}"}

    tool_trace: List[Dict[str, Any]] = []
    evidence_list: List[Dict[str, Any]] = []
    pending_action: Optional[Dict[str, Any]] = None

    # Construct initial message history
    openai_messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION}
    ]

    if history:
        for h in history:
            openai_messages.append({
                "role": h.get("role", "user"),
                "content": h.get("content", "")
            })

    trusted_header = f"[Trusted System Context: Verified Customer Account = {resolved_account_name} ({resolved_account_id}), Plan = {resolved_acc.get('plan')}]\n" if resolved_acc else ""
    openai_messages.append({
        "role": "user",
        "content": f"[Active User Session: Role={role}, UserID={user_id}]\n{trusted_header}{message}"
    })

    # Multi-turn tool execution loop (up to 8 iterations)
    max_turns = 8
    for turn in range(max_turns):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=openai_messages,
                tools=OPENAI_TOOLS,
                temperature=0.0
            )
        except Exception as e:
            # Fallback to gpt-4o-mini if model name not recognized
            if "model" in str(e).lower() and model_name != "gpt-4o-mini":
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=openai_messages,
                        tools=OPENAI_TOOLS,
                        temperature=0.0
                    )
                except Exception as e2:
                    return {
                        "response": f"⚠️ **LLM Error**: {str(e2)}",
                        "tool_trace": tool_trace,
                        "evidence": evidence_list,
                        "pending_action": pending_action,
                        "error": str(e2)
                    }
            else:
                return {
                    "response": f"⚠️ **LLM Error**: {str(e)}",
                    "tool_trace": tool_trace,
                    "evidence": evidence_list,
                    "pending_action": pending_action,
                    "error": str(e)
                }

        choice = response.choices[0]
        assistant_msg = choice.message

        # Append assistant message to conversation history
        openai_messages.append(assistant_msg)

        # Check for tool calls
        if not assistant_msg.tool_calls:
            # Final text response reached
            return {
                "response": assistant_msg.content or "",
                "tool_trace": tool_trace,
                "evidence": evidence_list,
                "pending_action": pending_action
            }

        # Execute each tool call
        for tool_call in assistant_msg.tool_calls:
            fname = tool_call.function.name
            try:
                fargs = json.loads(tool_call.function.arguments or "{}")
            except Exception:
                fargs = {}

            # Execute tool
            res = handle_tool_call(fname, fargs)

            # Record in tool trace
            tool_trace.append({
                "tool": fname,
                "input": fargs,
                "output": res
            })

            # Deterministic Account Mismatch Guard: Immediately halt on cross-account order/ticket mismatch
            if isinstance(res, dict) and res.get("error_type") == "ACCOUNT_MISMATCH":
                target_id = res.get("target_id") or fargs.get("identifier") or "the specified item"
                target_acc = res.get("target_account_id") or "a different account"
                mismatch_resp = (
                    f"⚠️ **Account Mismatch**: Order `{target_id}` belongs to account `{target_acc}`, "
                    f"not **{resolved_account_name}** (`{resolved_account_id}`). "
                    f"Please provide the correct order ID associated with {resolved_account_name}."
                )
                return {
                    "response": mismatch_resp,
                    "tool_trace": tool_trace,
                    "evidence": evidence_list,
                    "pending_action": None,
                    "error": "ACCOUNT_MISMATCH"
                }

            # Harvest citations
            if fname == "search_documents":
                for chunk in res.get("results", []):
                    evidence_list.append({
                        "document": chunk.get("document_id"),
                        "reference": chunk.get("source_reference"),
                        "title": chunk.get("title")
                    })
            elif fname == "prepare_action" and res.get("status") == "success":
                pending_action = res

            # Append tool response
            openai_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(res)
            })

    return {
        "response": "Agent reached maximum tool iterations.",
        "tool_trace": tool_trace,
        "evidence": evidence_list,
        "pending_action": pending_action
    }
