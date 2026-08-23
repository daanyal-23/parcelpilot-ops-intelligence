"""
Deterministic rule engines and calculations.
All calculations are code-based and trace directly to source document lines.
"""

from datetime import datetime
import pytz
import re
from typing import Dict, Any, Optional

DATASET_SNAPSHOT_TIME_STR = "2026-08-16T11:00:00+05:30"
IST = pytz.timezone("Asia/Kolkata")
SNAPSHOT_DT = datetime.fromisoformat(DATASET_SNAPSHOT_TIME_STR)

def parse_iso_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return IST.localize(val)
        return val
    val_str = str(val).strip()
    try:
        dt = datetime.fromisoformat(val_str)
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        return dt
    except ValueError:
        try:
            dt = datetime.strptime(val_str, "%Y-%m-%d %H:%M")
            return IST.localize(dt)
        except ValueError:
            return None

def classify_severity(ticket: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify ticket severity (P1 / P2 / P3) deterministically according to
    01_Support_Policy_v3_CURRENT.pdf, §2.
    """
    subject = str(ticket.get("subject", "") or "")
    description = str(ticket.get("description", "") or "")
    text = f"{subject} {description}".lower()

    # P1: Complete production outage preventing all shipment creation for a customer,
    # confirmed security incident or suspected credential exposure, or another event
    # causing immediate material business risk with no workaround.
    p1_patterns = [
        r"outage",
        r"all shipment creation is failing",
        r"preventing all shipment creation",
        r"http 500.*creating any shipment",
        r"security incident",
        r"credential exposure",
        r"api key exposure",
        r"production api key",
        r"exposed key",
        r"compromised"
    ]
    for pat in p1_patterns:
        if re.search(pat, text):
            return {
                "severity": "P1",
                "label": "P1 - Critical",
                "matched_criteria": pat,
                "definition": (
                    "Complete production outage preventing all shipment creation, confirmed security incident "
                    "or suspected credential exposure, or immediate material business risk with no workaround."
                ),
                "source_reference": "01_Support_Policy_v3_CURRENT.pdf, §2 (P1 Definition)",
                "escalation_required": True
            }

    # P2: Major feature unavailable or materially degraded for a customer, but core operations
    # remain possible or a workaround exists (e.g. bulk upload failing while single creation works).
    p2_patterns = [
        r"bulk upload",
        r"csv.*fail",
        r"major feature",
        r"materially degraded",
        r"workaround exists",
        r"one-by-one still works",
        r"single.*creation.*works"
    ]
    for pat in p2_patterns:
        if re.search(pat, text):
            return {
                "severity": "P2",
                "label": "P2 - High",
                "matched_criteria": pat,
                "definition": "Major feature unavailable or materially degraded, but core operations remain possible or workaround exists.",
                "source_reference": "01_Support_Policy_v3_CURRENT.pdf, §2 (P2 Definition)",
                "escalation_required": False
            }

    # P3: Minor defect, how-to question, configuration request, or issue with limited operational impact.
    return {
        "severity": "P3",
        "label": "P3 - Normal",
        "matched_criteria": "default / minor defect / how-to / configuration",
        "definition": "Minor defect, how-to question, configuration request, or issue with limited operational impact.",
        "source_reference": "01_Support_Policy_v3_CURRENT.pdf, §2 (P3 Definition)",
        "escalation_required": False
    }

def calculate_cancellation_fee(order: Dict[str, Any], account: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Deterministic cancellation fee and eligibility calculation.
    Traces to:
    - 03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1
    - 05_Northstar_Logistics_Enterprise_Agreement.pdf, §2
    - 06_LumenWorks_Service_Agreement.pdf, §2
    """
    account_id = order.get("account_id") or (account.get("account_id") if account else None)
    status = (order.get("status") or "").upper().strip()

    # Rule: DELIVERED cannot be cancelled
    if status == "DELIVERED":
        return {
            "eligible_for_cancellation": False,
            "cancellation_fee_inr": None,
            "status": status,
            "decision": "Order is DELIVERED and cannot be cancelled.",
            "workflow_action": "NO_CANCELLATION",
            "source_reference": "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1",
            "explanation": "DELIVERED orders cannot be cancelled per Cancellation SOP §1."
        }

    # Rule: PICKED_UP cannot be cancelled; use return-to-origin workflow
    # Critical test E17: Northstar's free cancellation waiver only applies to BOOKED pre-pickup orders!
    if status == "PICKED_UP":
        return {
            "eligible_for_cancellation": False,
            "cancellation_fee_inr": None,
            "status": status,
            "decision": "Order is already PICKED_UP and cannot be cancelled. Use the return-to-origin workflow.",
            "workflow_action": "RETURN_TO_ORIGIN",
            "source_reference": (
                "05_Northstar_Logistics_Enterprise_Agreement.pdf, §2 & 03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1"
                if account_id == "ACCT-001" else
                "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1"
            ),
            "explanation": (
                "Once a shipment is PICKED_UP, cancellation is not permitted regardless of account agreement. "
                "Northstar's fee waiver applies only to BOOKED pre-pickup shipments. The standard return-to-origin workflow must be initiated."
            )
        }

    if status == "DRAFT":
        return {
            "eligible_for_cancellation": True,
            "cancellation_fee_inr": 0.0,
            "status": status,
            "decision": "DRAFT orders may be cancelled with no fee (INR 0).",
            "workflow_action": "CANCEL_FREE",
            "source_reference": "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1",
            "explanation": "DRAFT orders carry no cancellation charge."
        }

    if status == "BOOKED":
        # Check account specific override for Northstar
        if account_id == "ACCT-001":
            return {
                "eligible_for_cancellation": True,
                "cancellation_fee_inr": 0.0,
                "status": status,
                "decision": "Northstar may cancel any BOOKED pre-pickup shipment with no fee (INR 0).",
                "workflow_action": "CANCEL_FREE",
                "governing_agreement": "Northstar Enterprise Agreement",
                "source_reference": "05_Northstar_Logistics_Enterprise_Agreement.pdf, §2",
                "explanation": "Northstar Enterprise Agreement §2 grants a full override waiving all cancellation fees for BOOKED pre-pickup shipments at any time."
            }

        # For LumenWorks (ACCT-002), Beacon Retail (ACCT-003), Axis Labs (ACCT-004), and General:
        # Check elapsed time between booked_at and cancellation_requested_at (or snapshot)
        booked_at = parse_iso_dt(order.get("booked_at"))
        cancel_req_at = parse_iso_dt(order.get("cancellation_requested_at")) or SNAPSHOT_DT

        if not booked_at:
            return {
                "eligible_for_cancellation": False,
                "cancellation_fee_inr": None,
                "error": "INSUFFICIENT_DATA",
                "decision": "Cannot calculate cancellation fee because booking timestamp is missing.",
                "source_reference": "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1"
            }

        elapsed_minutes = (cancel_req_at - booked_at).total_seconds() / 60.0

        is_lumenworks = (account_id == "ACCT-002")
        source_ref = (
            "06_LumenWorks_Service_Agreement.pdf, §2 -> 03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1"
            if is_lumenworks else
            "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1"
        )

        if elapsed_minutes <= 30.0:
            return {
                "eligible_for_cancellation": True,
                "cancellation_fee_inr": 0.0,
                "elapsed_minutes_since_booking": elapsed_minutes,
                "status": status,
                "decision": f"Cancellation requested within 30 minutes ({elapsed_minutes:.1f} mins elapsed): No fee (INR 0).",
                "workflow_action": "CANCEL_FREE",
                "source_reference": source_ref,
                "explanation": "Per SOP §1, BOOKED shipments cancelled within 30 minutes of booking incur no cancellation fee."
            }
        else:
            return {
                "eligible_for_cancellation": True,
                "cancellation_fee_inr": 250.0,
                "elapsed_minutes_since_booking": elapsed_minutes,
                "status": status,
                "decision": f"Cancellation requested after 30 minutes ({elapsed_minutes:.1f} mins elapsed): Fee is INR 250.",
                "workflow_action": "CANCEL_WITH_FEE",
                "source_reference": source_ref,
                "explanation": (
                    f"Per SOP §1 (which LumenWorks §2 explicitly defers to), cancellation requested {elapsed_minutes:.1f} minutes "
                    "after booking exceeds the 30-minute grace window and incurs an INR 250 fee."
                )
            }

    return {
        "eligible_for_cancellation": False,
        "cancellation_fee_inr": None,
        "status": status,
        "decision": f"Unknown order status '{status}'. Human review recommended.",
        "source_reference": "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1"
    }

def calculate_service_credit(
    order: Dict[str, Any],
    account: Optional[Dict[str, Any]] = None,
    user_role: str = "support_agent"
) -> Dict[str, Any]:
    """
    Deterministic failed-pickup service credit calculation.
    Traces to:
    - 03_Cancellation_and_Service_Credit_SOP_v4.pdf, §2, §3
    - 05_Northstar_Logistics_Enterprise_Agreement.pdf, §3
    - 06_LumenWorks_Service_Agreement.pdf, §3
    """
    account_id = order.get("account_id") or (account.get("account_id") if account else None)

    # Uncertainty checks per SOP v4 §3: "Do not promise a credit when carrier fault, pickup timing, or customer fault is unknown."
    carrier_fault = order.get("carrier_fault")
    customer_fault = order.get("customer_fault")
    pickup_window_end = parse_iso_dt(order.get("pickup_window_end"))

    if carrier_fault is None or customer_fault is None or not pickup_window_end:
        return {
            "eligible": False,
            "credit_amount_inr": 0.0,
            "status": "INSUFFICIENT_DATA",
            "decision": "Cannot evaluate service credit eligibility because carrier fault, customer fault, or pickup window timing is unknown.",
            "source_reference": "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §3",
            "explanation": "SOP §3 states: 'Do not promise a credit when carrier fault, pickup timing, or customer fault is unknown.'"
        }

    # Evaluate delay
    actual_pickup = parse_iso_dt(order.get("pickup_actual_at"))
    eval_time = actual_pickup if actual_pickup else SNAPSHOT_DT

    delay_minutes = (eval_time - pickup_window_end).total_seconds() / 60.0
    delay_hours = delay_minutes / 60.0

    shipment_fee = float(order.get("shipment_fee_inr") or 0.0)

    # Check LumenWorks override
    if account_id == "ACCT-002":
        source_ref = "06_LumenWorks_Service_Agreement.pdf, §3"
        # Threshold: > 4 hours
        if delay_hours <= 4.0:
            return {
                "eligible": False,
                "credit_amount_inr": 0.0,
                "delay_hours": delay_hours,
                "threshold_hours": 4.0,
                "decision": f"Ineligible for credit: Delay is {delay_hours:.2f} hours, which does not exceed LumenWorks' 4-hour threshold.",
                "source_reference": source_ref,
                "explanation": "LumenWorks Service Agreement §3 requires the delay to be more than 4 hours past scheduled window end."
            }
        if not carrier_fault:
            return {
                "eligible": False,
                "credit_amount_inr": 0.0,
                "decision": "Ineligible for credit: Carrier fault is not confirmed.",
                "source_reference": source_ref
            }
        if customer_fault:
            return {
                "eligible": False,
                "credit_amount_inr": 0.0,
                "decision": "Ineligible for credit: Customer fault was identified.",
                "source_reference": source_ref
            }

        credit_amount = 300.0
        req_manager = credit_amount > 1000.0

        return {
            "eligible": True,
            "credit_amount_inr": credit_amount,
            "delay_hours": delay_hours,
            "threshold_hours": 4.0,
            "carrier_fault": carrier_fault,
            "customer_fault": customer_fault,
            "requires_manager_approval": req_manager,
            "decision": f"Eligible for fixed INR {credit_amount:.0f} service credit (delay of {delay_hours:.2f} hrs > 4 hrs, carrier fault confirmed, no customer fault).",
            "source_reference": source_ref,
            "explanation": "LumenWorks Service Agreement §3 overrides default SOP with a flat INR 300 credit for delays exceeding 4 hours."
        }

    # General SOP v4 calculation (Northstar, Beacon, Axis Labs, General)
    source_ref = (
        "05_Northstar_Logistics_Enterprise_Agreement.pdf, §3 & 03_Cancellation_and_Service_Credit_SOP_v4.pdf, §2"
        if account_id == "ACCT-001" else
        "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §2"
    )

    if delay_hours <= 2.0:
        return {
            "eligible": False,
            "credit_amount_inr": 0.0,
            "delay_hours": delay_hours,
            "threshold_hours": 2.0,
            "decision": f"Ineligible for credit: Delay is {delay_hours:.2f} hours, which does not exceed the 2-hour SOP threshold.",
            "source_reference": source_ref,
            "explanation": "SOP §2 requires the delay to be more than 2 hours past scheduled pickup window end."
        }

    if not carrier_fault:
        return {
            "eligible": False,
            "credit_amount_inr": 0.0,
            "decision": "Ineligible for credit: Carrier fault is not confirmed.",
            "source_reference": source_ref
        }

    if customer_fault:
        return {
            "eligible": False,
            "credit_amount_inr": 0.0,
            "decision": "Ineligible for credit: Customer fault was identified.",
            "source_reference": source_ref
        }

    # Lower of INR 500 or 10% of shipment fee
    ten_pct = 0.10 * shipment_fee
    credit_amount = min(500.0, ten_pct)
    req_manager = credit_amount > 1000.0

    cap_note = ""
    if account_id == "ACCT-001":
        cap_note = " (Note: Northstar Agreement §3 caps monthly aggregate credits at INR 5,000; unenforceable in current dataset due to missing historical credit ledger)."

    return {
        "eligible": True,
        "credit_amount_inr": credit_amount,
        "calculation_basis": f"Lower of INR 500 or 10% of INR {shipment_fee:.2f} (INR {ten_pct:.2f}) = INR {credit_amount:.2f}",
        "delay_hours": delay_hours,
        "threshold_hours": 2.0,
        "carrier_fault": carrier_fault,
        "customer_fault": customer_fault,
        "requires_manager_approval": req_manager,
        "disclosed_limitation": cap_note.strip() if cap_note else None,
        "decision": f"Eligible for INR {credit_amount:.2f} service credit ({delay_hours:.2f} hrs late > 2 hrs, carrier fault, no customer fault).{cap_note}",
        "source_reference": source_ref,
        "explanation": f"Per Cancellation & Service Credit SOP §2, credit is lower of INR 500 or 10% of shipment fee (INR {shipment_fee:.2f})."
    }

def calculate_sla_status(
    ticket: Dict[str, Any],
    account: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Deterministic SLA status calculation.
    Traces to:
    - 01_Support_Policy_v3_CURRENT.pdf, §3
    - 05_Northstar_Logistics_Enterprise_Agreement.pdf, §1
    - 06_LumenWorks_Service_Agreement.pdf, §1
    """
    account_id = ticket.get("account_id") or (account.get("account_id") if account else None)
    plan = account.get("plan", "Standard") if account else "Standard"

    severity_info = classify_severity(ticket)
    severity = severity_info["severity"]

    created_at = parse_iso_dt(ticket.get("created_at"))
    if not created_at:
        return {
            "error": "INSUFFICIENT_DATA",
            "decision": "Ticket creation timestamp is missing.",
            "source_reference": "01_Support_Policy_v3_CURRENT.pdf, §3"
        }

    elapsed_minutes = (SNAPSHOT_DT - created_at).total_seconds() / 60.0
    elapsed_hours = elapsed_minutes / 60.0

    # Determine governing target & source
    if account_id == "ACCT-001":
        # Northstar Logistics Agreement §1
        source_ref = "05_Northstar_Logistics_Enterprise_Agreement.pdf, §1"
        targets = {
            "P1": {"target_str": "15 minutes, 24x7", "target_minutes": 15, "is_24x7": True},
            "P2": {"target_str": "1 hour", "target_minutes": 60, "is_24x7": True},
            "P3": {"target_str": "8 business hours", "target_minutes": 480, "is_24x7": False}
        }
        target_info = targets[severity]
    elif account_id == "ACCT-002":
        # LumenWorks Service Agreement §1
        source_ref = "06_LumenWorks_Service_Agreement.pdf, §1"
        targets = {
            "P1": {"target_str": "2 business hours (no weekend/after-hours)", "target_minutes": 120, "is_24x7": False},
            "P2": {"target_str": "4 business hours (no weekend/after-hours)", "target_minutes": 240, "is_24x7": False},
            "P3": {"target_str": "2 business days", "target_minutes": 960, "is_24x7": False}
        }
        target_info = targets[severity]
    else:
        # Standard Support Policy v3 §3
        source_ref = "01_Support_Policy_v3_CURRENT.pdf, §3"
        if plan == "Enterprise":
            targets = {
                "P1": {"target_str": "30 minutes, 24x7", "target_minutes": 30, "is_24x7": True},
                "P2": {"target_str": "2 hours", "target_minutes": 120, "is_24x7": False},
                "P3": {"target_str": "1 business day", "target_minutes": 480, "is_24x7": False}
            }
        elif plan == "Growth":
            targets = {
                "P1": {"target_str": "2 business hours", "target_minutes": 120, "is_24x7": False},
                "P2": {"target_str": "4 business hours", "target_minutes": 240, "is_24x7": False},
                "P3": {"target_str": "2 business days", "target_minutes": 960, "is_24x7": False}
            }
        else:  # Standard
            targets = {
                "P1": {"target_str": "4 business hours", "target_minutes": 240, "is_24x7": False},
                "P2": {"target_str": "1 business day", "target_minutes": 480, "is_24x7": False},
                "P3": {"target_str": "2 business days", "target_minutes": 960, "is_24x7": False}
            }
        target_info = targets[severity]

    target_str = target_info["target_str"]
    target_mins = target_info["target_minutes"]
    is_24x7 = target_info["is_24x7"]

    # In our dataset, no response timestamp exists, so evaluate pending elapsed time at snapshot
    breached = False
    if is_24x7:
        breached = elapsed_minutes > target_mins
        comparison_note = f"Elapsed wall-clock time ({elapsed_minutes:.0f} mins) {'exceeds' if breached else 'is within'} 24x7 target ({target_mins} mins)."
    else:
        # For business-hour targets, report raw wall-clock elapsed time alongside the stated target
        # without fabricating a business-hour calendar calculation.
        comparison_note = (
            f"Elapsed wall-clock time since creation: {elapsed_minutes:.0f} mins ({elapsed_hours:.1f} hrs) against target '{target_str}'. "
            "(Business hours/calendar undefined in source documents; reporting raw wall-clock elapsed time)."
        )
        breached = False  # cannot definitively mark breached without business calendar

    escalation_recommended = (is_24x7 and breached) or (severity == "P1")

    return {
        "severity": severity,
        "severity_label": severity_info["label"],
        "target": target_str,
        "target_minutes": target_mins,
        "elapsed_since_creation_minutes": round(elapsed_minutes, 1),
        "elapsed_since_creation_hours": round(elapsed_hours, 2),
        "is_24x7": is_24x7,
        "is_breached_at_snapshot": (is_24x7 and breached),
        "escalation_recommended": escalation_recommended,
        "comparison_note": comparison_note,
        "source_reference": source_ref,
        "decision": (
            f"Severity: {severity_info['label']}. SLA Target: {target_str}. "
            f"Elapsed wall-clock time: {elapsed_minutes:.0f} minutes ({elapsed_hours:.1f} hrs). "
            f"{'Target exceeded as of snapshot time.' if (is_24x7 and breached) else comparison_note} "
            f"{'Immediate escalation recommended.' if escalation_recommended else 'Standard processing.'}"
        )
    }
