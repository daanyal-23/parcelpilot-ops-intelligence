"""
Agent-facing tools and server-side authorization enforcement.
All business rules, authorizations, and mutations are executed deterministically in code.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import pytz

from backend.db import get_db_connection, DATASET_SNAPSHOT_TIME
from backend.docs_index import search_documents_index, source_resolution
from backend.rules_engine import (
    classify_severity,
    calculate_cancellation_fee,
    calculate_service_credit,
    calculate_sla_status,
    parse_iso_dt,
    SNAPSHOT_DT
)

IST = pytz.timezone("Asia/Kolkata")

# Error Types
ERROR_NOT_FOUND = "NOT_FOUND"
ERROR_UNAUTHORIZED = "UNAUTHORIZED"
ERROR_INVALID_INPUT = "INVALID_INPUT"
ERROR_INSUFFICIENT_AUTHORITY = "INSUFFICIENT_AUTHORITY"
ERROR_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
ERROR_CONFLICTING_SOURCES = "CONFLICTING_SOURCES"
ERROR_ACTION_REQUIRES_CONFIRMATION = "ACTION_REQUIRES_CONFIRMATION"
ERROR_ACTION_EXPIRED = "ACTION_EXPIRED"
ERROR_INTERNAL_ERROR = "INTERNAL_ERROR"

def search_documents(
    query: str = "",
    topic: Optional[str] = None,
    account_id: Optional[str] = None,
    include_historical: bool = False
) -> Dict[str, Any]:
    """
    Search policy documents, agreements, SOPs, and product guides.
    Historical ticket resolutions are NEVER returned here.
    """
    return search_documents_index(
        query=query,
        topic=topic,
        account_id=account_id,
        include_historical=include_historical
    )

def lookup_data(
    entity: str,
    identifier: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    account_id: Optional[str] = None,
    role: str = "support_agent"
) -> Dict[str, Any]:
    """
    Look up raw structured facts from SQLite database.
    Returns raw facts only — never business decisions.
    Historical resolutions are tagged authoritative: False.
    """
    entity_clean = entity.lower().strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if entity_clean in ["account", "accounts"]:
            # 1. Exact ID lookup
            target_id = identifier or account_id or (filters.get("account_id") if filters else None)
            target_name = (filters.get("account_name") or filters.get("name")) if filters else None

            if target_id and not target_name:
                cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (target_id.strip(),))
                row = cursor.fetchone()
                if row:
                    return {"status": "success", "data": dict(row)}
                # If identifier was not an exact account_id, try matching by account_name
                cursor.execute("SELECT * FROM accounts WHERE LOWER(account_name) = LOWER(?)", (target_id.strip(),))
                row = cursor.fetchone()
                if row:
                    return {"status": "success", "data": dict(row)}
                cursor.execute("SELECT * FROM accounts WHERE LOWER(account_name) LIKE LOWER(?)", (f"%{target_id.strip()}%",))
                row = cursor.fetchone()
                if row:
                    return {"status": "success", "data": dict(row)}
                return {"status": "error", "error_type": ERROR_NOT_FOUND, "message": f"Account '{target_id}' not found"}

            elif target_name:
                cursor.execute("SELECT * FROM accounts WHERE LOWER(account_name) = LOWER(?)", (target_name.strip(),))
                row = cursor.fetchone()
                if row:
                    return {"status": "success", "data": dict(row)}
                cursor.execute("SELECT * FROM accounts WHERE LOWER(account_name) LIKE LOWER(?)", (f"%{target_name.strip()}%",))
                row = cursor.fetchone()
                if row:
                    return {"status": "success", "data": dict(row)}
                return {"status": "error", "error_type": ERROR_NOT_FOUND, "message": f"Account with name '{target_name}' not found"}

            else:
                cursor.execute("SELECT * FROM accounts")
                rows = [dict(r) for r in cursor.fetchall()]
                return {"status": "success", "data": rows}

        elif entity_clean in ["order", "orders"]:
            if identifier:
                cursor.execute("SELECT * FROM orders WHERE order_id = ?", (identifier.strip(),))
                row = cursor.fetchone()
                if not row:
                    return {"status": "error", "error_type": ERROR_NOT_FOUND, "message": f"Order {identifier} not found"}
                order_data = dict(row)
                if account_id and order_data.get("account_id") and order_data["account_id"] != account_id:
                    return {
                        "status": "error",
                        "error_type": "ACCOUNT_MISMATCH",
                        "message": f"Account Mismatch: Order '{identifier}' belongs to account '{order_data['account_id']}', not '{account_id}'.",
                        "target_id": identifier,
                        "target_account_id": order_data["account_id"],
                        "resolved_account_id": account_id
                    }
                return {"status": "success", "data": order_data}
            elif account_id:
                cursor.execute("SELECT * FROM orders WHERE account_id = ?", (account_id,))
                rows = [dict(r) for r in cursor.fetchall()]
                return {"status": "success", "data": rows}
            else:
                cursor.execute("SELECT * FROM orders")
                rows = [dict(r) for r in cursor.fetchall()]
                return {"status": "success", "data": rows}

        elif entity_clean in ["ticket", "tickets"]:
            if identifier:
                cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (identifier.strip(),))
                row = cursor.fetchone()
                if not row:
                    return {"status": "error", "error_type": ERROR_NOT_FOUND, "message": f"Ticket {identifier} not found"}
                data = dict(row)
                if account_id and data.get("account_id") and data["account_id"] != account_id:
                    return {
                        "status": "error",
                        "error_type": "ACCOUNT_MISMATCH",
                        "message": f"Account Mismatch: Ticket '{identifier}' belongs to account '{data['account_id']}', not '{account_id}'.",
                        "target_id": identifier,
                        "target_account_id": data["account_id"],
                        "resolved_account_id": account_id
                    }
                hist = data.get("historical_resolution")
                data["historical_resolution_info"] = {
                    "text": hist,
                    "authoritative": False,
                    "disclaimer": "Historical ticket resolutions are past context only and may contain incorrect guidance. Never use as authoritative policy."
                }
                return {"status": "success", "data": data}
            elif account_id:
                cursor.execute("SELECT * FROM tickets WHERE account_id = ?", (account_id,))
                rows = []
                for r in cursor.fetchall():
                    d = dict(r)
                    h = d.get("historical_resolution")
                    d["historical_resolution_info"] = {
                        "text": h,
                        "authoritative": False,
                        "disclaimer": "Historical ticket resolutions are past context only and may contain incorrect guidance. Never use as authoritative policy."
                    }
                    rows.append(d)
                return {"status": "success", "data": rows}
            else:
                cursor.execute("SELECT * FROM tickets")
                rows = []
                for r in cursor.fetchall():
                    d = dict(r)
                    h = d.get("historical_resolution")
                    d["historical_resolution_info"] = {
                        "text": h,
                        "authoritative": False,
                        "disclaimer": "Historical ticket resolutions are past context only and may contain incorrect guidance. Never use as authoritative policy."
                    }
                    rows.append(d)
                return {"status": "success", "data": rows}

        else:
            return {
                "status": "error",
                "error_type": ERROR_INVALID_INPUT,
                "message": f"Unknown entity '{entity}'. Allowed: account, order, ticket"
            }

    finally:
        conn.close()

def calculate(
    calculation_type: str,
    inputs: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Deterministic calculation tool.
    Available types: 'cancellation_fee', 'service_credit', 'sla_status'
    """
    calc_type = calculation_type.lower().strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if calc_type == "cancellation_fee":
            order_id = inputs.get("order_id")
            order = inputs.get("order")
            account = inputs.get("account")

            if not order and order_id:
                cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
                row = cursor.fetchone()
                if row:
                    order = dict(row)

            if not order:
                return {
                    "status": "error",
                    "error_type": ERROR_NOT_FOUND,
                    "message": f"Order data or order_id required for cancellation_fee calculation"
                }

            resolved_acc_id = (context or {}).get("resolved_account_id")
            if resolved_acc_id and order.get("account_id") and order["account_id"] != resolved_acc_id:
                return {
                    "status": "error",
                    "error_type": "ACCOUNT_MISMATCH",
                    "message": f"Account Mismatch: Order '{order.get('order_id')}' belongs to account '{order['account_id']}', which does not match active customer context '{resolved_acc_id}'."
                }

            if not account and order.get("account_id"):
                cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (order["account_id"],))
                row = cursor.fetchone()
                if row:
                    account = dict(row)

            result = calculate_cancellation_fee(order, account)
            return {"status": "success", "calculation_type": calc_type, "result": result}

        elif calc_type == "service_credit":
            order_id = inputs.get("order_id")
            order = inputs.get("order")
            account = inputs.get("account")
            user_role = (context or {}).get("role", "support_agent")

            if not order and order_id:
                cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
                row = cursor.fetchone()
                if row:
                    order = dict(row)

            if not order:
                return {
                    "status": "error",
                    "error_type": ERROR_NOT_FOUND,
                    "message": "Order data or order_id required for service_credit calculation"
                }

            resolved_acc_id = (context or {}).get("resolved_account_id")
            if resolved_acc_id and order.get("account_id") and order["account_id"] != resolved_acc_id:
                return {
                    "status": "error",
                    "error_type": "ACCOUNT_MISMATCH",
                    "message": f"Account Mismatch: Order '{order.get('order_id')}' belongs to account '{order['account_id']}', which does not match active customer context '{resolved_acc_id}'."
                } 

            if not account and order.get("account_id"):
                cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (order["account_id"],))
                row = cursor.fetchone()
                if row:
                    account = dict(row)

            result = calculate_service_credit(order, account, user_role=user_role)
            return {"status": "success", "calculation_type": calc_type, "result": result}

        elif calc_type == "sla_status":
            ticket_id = inputs.get("ticket_id")
            ticket = inputs.get("ticket")
            account = inputs.get("account")

            if not ticket and ticket_id:
                cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
                row = cursor.fetchone()
                if row:
                    ticket = dict(row)

            if not ticket:
                return {
                    "status": "error",
                    "error_type": ERROR_NOT_FOUND,
                    "message": "Ticket data or ticket_id required for sla_status calculation"
                }

            if not account and ticket.get("account_id"):
                cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (ticket["account_id"],))
                row = cursor.fetchone()
                if row:
                    account = dict(row)

            result = calculate_sla_status(ticket, account)
            return {"status": "success", "calculation_type": calc_type, "result": result}

        elif calc_type == "elapsed_time":
            start_time_str = inputs.get("start_time")
            end_time_str = inputs.get("end_time") or DATASET_SNAPSHOT_TIME
            start_dt = parse_iso_dt(start_time_str)
            end_dt = parse_iso_dt(end_time_str)

            if not start_dt or not end_dt:
                return {
                    "status": "error",
                    "error_type": ERROR_INVALID_INPUT,
                    "message": "Valid start_time (and optional end_time) ISO string required"
                }

            elapsed_seconds = (end_dt - start_dt).total_seconds()
            elapsed_minutes = elapsed_seconds / 60.0
            elapsed_hours = elapsed_minutes / 60.0

            return {
                "status": "success",
                "calculation_type": calc_type,
                "result": {
                    "start_time": start_dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "elapsed_minutes": round(elapsed_minutes, 1),
                    "elapsed_hours": round(elapsed_hours, 2),
                    "formatted": f"{int(elapsed_hours)}h {int(elapsed_minutes % 60)}m"
                }
            }

        else:
            return {
                "status": "error",
                "error_type": ERROR_INVALID_INPUT,
                "message": f"Unknown calculation_type '{calculation_type}'. Allowed types: cancellation_fee, service_credit, sla_status, elapsed_time"
            }

    finally:
        conn.close()

def prepare_action(
    action_type: str,
    target_id: str,
    payload: Dict[str, Any],
    user_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Two-phase action lifecycle: Phase 1 (Prepare).
    Nothing changes state yet. Generates action_id with pending_confirmation status.
    Server-side validates role authorizations (e.g. credit > INR 1,000 requires manager).
    """
    role = (user_context.get("role") or "support_agent").lower().strip()
    user_id = user_context.get("user_id", "agent_1")

    allowed_actions = ["cancel_order", "issue_credit", "escalate_ticket", "update_ticket_status"]
    if action_type not in allowed_actions:
        return {
            "status": "error",
            "error_type": ERROR_INVALID_INPUT,
            "message": f"Unknown action_type '{action_type}'. Allowed: {allowed_actions}"
        }

    # Server-side account ownership validation using trusted user_context
    resolved_account_id = user_context.get("resolved_account_id")
    if resolved_account_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if action_type in ["cancel_order", "issue_credit"]:
                cursor.execute("SELECT account_id FROM orders WHERE order_id = ?", (target_id.strip(),))
                ord_row = cursor.fetchone()
                if ord_row:
                    actual_acc = ord_row["account_id"]
                    if actual_acc != resolved_account_id:
                        return {
                            "status": "error",
                            "error_type": "INVALID_ACCOUNT_OWNERSHIP",
                            "message": (
                                f"Security Violation: Target order '{target_id}' belongs to account '{actual_acc}', "
                                f"which does not match the requesting customer context '{resolved_account_id}'."
                            )
                        }
            elif action_type in ["escalate_ticket", "update_ticket_status"]:
                cursor.execute("SELECT account_id FROM tickets WHERE ticket_id = ?", (target_id.strip(),))
                tkt_row = cursor.fetchone()
                if tkt_row:
                    actual_acc = tkt_row["account_id"]
                    if actual_acc != resolved_account_id:
                        return {
                            "status": "error",
                            "error_type": "INVALID_ACCOUNT_OWNERSHIP",
                            "message": (
                                f"Security Violation: Target ticket '{target_id}' belongs to account '{actual_acc}', "
                                f"which does not match the requesting customer context '{resolved_account_id}'."
                            )
                        }
        finally:
            conn.close()

    # Role permission check for service credit above INR 1,000 (SOP v4 §3)
    if action_type == "issue_credit":
        credit_amount = float(payload.get("credit_amount_inr") or 0.0)
        if credit_amount > 1000.0 and role != "manager":
            return {
                "status": "error",
                "error_type": ERROR_INSUFFICIENT_AUTHORITY,
                "message": (
                    f"Action rejected: Any individual service credit above INR 1,000 requires manager approval "
                    f"per SOP v4 §3. The current role '{role}' is unauthorized to approve INR {credit_amount:.2f}."
                ),
                "required_role": "manager",
                "source_reference": "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §3"
            }

    action_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"
    summary = payload.get("summary") or f"Prepare {action_type} for target {target_id}"

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO actions (action_id, action_type, target_id, payload, status, created_by_role, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                action_type,
                target_id,
                json.dumps(payload),
                "pending_confirmation",
                role,
                summary,
                DATASET_SNAPSHOT_TIME
            )
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "status": "success",
        "action_id": action_id,
        "action_type": action_type,
        "target_id": target_id,
        "summary": summary,
        "payload": payload,
        "state": "pending_confirmation",
        "confirmation_required": True,
        "message": "Action prepared successfully. It requires explicit user confirmation before execution."
    }

def execute_action(
    action_id: str,
    user_context: Optional[Dict[str, Any]] = None,
    confirmed_by_user: bool = False
) -> Dict[str, Any]:
    """
    Two-phase action lifecycle: Phase 2 (Execute).
    Independently re-validates:
    - Action exists and is in 'pending_confirmation' status
    - Confirmation was explicitly given
    - Role permits it
    - Action not expired (validity window)
    - Order state re-validation for cancellations (Defense-in-depth: rejects PICKED_UP or DELIVERED)
    - Issues credit and records into issued_credits table
    """
    user_ctx = user_context or {}
    role = (user_ctx.get("role") or "support_agent").lower().strip()
    user_id = user_ctx.get("user_id", "authorized_user")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM actions WHERE action_id = ?", (action_id,))
        row = cursor.fetchone()
        if not row:
            return {
                "status": "error",
                "error_type": ERROR_NOT_FOUND,
                "message": f"Action {action_id} not found."
            }

        action = dict(row)
        if action["status"] != "pending_confirmation":
            return {
                "status": "error",
                "error_type": ERROR_INVALID_INPUT,
                "message": f"Action {action_id} is in status '{action['status']}' and cannot be executed."
            }

        if not confirmed_by_user:
            return {
                "status": "error",
                "error_type": ERROR_ACTION_REQUIRES_CONFIRMATION,
                "message": "Action cannot be executed without explicit user confirmation."
            }

        # Check Action Expiry (e.g. created_at vs current execution)
        created_at = parse_iso_dt(action.get("created_at"))
        if created_at:
            elapsed_sec = (SNAPSHOT_DT - created_at).total_seconds()
            # If created more than 24 hours prior to snapshot time, mark expired
            if elapsed_sec > 86400:
                cursor.execute("UPDATE actions SET status = 'expired' WHERE action_id = ?", (action_id,))
                conn.commit()
                return {
                    "status": "error",
                    "error_type": ERROR_ACTION_EXPIRED,
                    "message": f"Action {action_id} has expired and cannot be executed."
                }

        payload = json.loads(action["payload"])
        action_type = action["action_type"]
        target_id = action["target_id"]

        # Defense-in-depth re-validation for cancel_order
        if action_type == "cancel_order":
            cursor.execute("SELECT * FROM orders WHERE order_id = ?", (target_id,))
            ord_row = cursor.fetchone()
            if not ord_row:
                return {
                    "status": "error",
                    "error_type": ERROR_NOT_FOUND,
                    "message": f"Target order {target_id} not found."
                }
            ord_data = dict(ord_row)
            curr_status = ord_data.get("status", "").upper().strip()

            if curr_status == "PICKED_UP":
                return {
                    "status": "error",
                    "error_type": ERROR_CONFLICTING_SOURCES,
                    "message": f"Execution rejected: Order {target_id} is in status 'PICKED_UP'. Cancellation is not permitted once picked up; standard return-to-origin process must be initiated per SOP v4 §1."
                }
            if curr_status == "DELIVERED":
                return {
                    "status": "error",
                    "error_type": ERROR_INVALID_INPUT,
                    "message": f"Execution rejected: Order {target_id} is in status 'DELIVERED' and cannot be cancelled."
                }

            cursor.execute(
                "UPDATE orders SET status = 'CANCELLED', cancellation_requested_at = ? WHERE order_id = ?",
                (DATASET_SNAPSHOT_TIME, target_id)
            )

        elif action_type == "issue_credit":
            credit_amount = float(payload.get("credit_amount_inr") or 0.0)
            if credit_amount > 1000.0 and role != "manager":
                return {
                    "status": "error",
                    "error_type": ERROR_INSUFFICIENT_AUTHORITY,
                    "message": f"Execution rejected: Manager role required to issue credit of INR {credit_amount:.2f}."
                }

            # Lookup order/account
            cursor.execute("SELECT * FROM orders WHERE order_id = ?", (target_id,))
            ord_row = cursor.fetchone()
            account_id = ord_row["account_id"] if ord_row else payload.get("account_id", "ACCT-UNKNOWN")

            credit_id = f"CRD-{uuid.uuid4().hex[:8].upper()}"
            cursor.execute(
                """
                INSERT INTO issued_credits (credit_id, action_id, order_id, account_id, amount_inr, approved_by_user, approved_by_role, issued_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    credit_id,
                    action_id,
                    target_id,
                    account_id,
                    credit_amount,
                    user_id,
                    role,
                    DATASET_SNAPSHOT_TIME,
                    payload.get("summary", "")
                )
            )

            # Update order note
            if ord_row:
                new_notes = (ord_row["notes"] or "") + f" [Service credit {credit_id} of INR {credit_amount:.2f} issued by {user_id} ({role}) on {DATASET_SNAPSHOT_TIME}]"
                cursor.execute("UPDATE orders SET notes = ? WHERE order_id = ?", (new_notes.strip(), target_id))

        elif action_type == "update_ticket_status":
            new_status = payload.get("new_status", "in_progress")
            cursor.execute(
                "UPDATE tickets SET status = ? WHERE ticket_id = ?",
                (new_status, target_id)
            )
        elif action_type == "escalate_ticket":
            cursor.execute(
                "UPDATE tickets SET status = 'escalated' WHERE ticket_id = ?",
                (target_id,)
            )

        cursor.execute(
            "UPDATE actions SET status = 'executed', executed_at = ? WHERE action_id = ?",
            (DATASET_SNAPSHOT_TIME, action_id)
        )
        conn.commit()

        return {
            "status": "success",
            "action_id": action_id,
            "action_type": action_type,
            "target_id": target_id,
            "executed_at": DATASET_SNAPSHOT_TIME,
            "summary": action["summary"],
            "message": f"Action {action_id} ({action_type}) executed successfully."
        }

    finally:
        conn.close()

def cancel_action(action_id: str) -> Dict[str, Any]:
    """
    Explicitly cancel a pending action.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM actions WHERE action_id = ?", (action_id,))
        row = cursor.fetchone()
        if not row:
            return {"status": "error", "error_type": ERROR_NOT_FOUND, "message": f"Action {action_id} not found."}

        cursor.execute("UPDATE actions SET status = 'cancelled' WHERE action_id = ?", (action_id,))
        conn.commit()
        return {"status": "success", "action_id": action_id, "message": "Action cancelled successfully."}
    finally:
        conn.close()
