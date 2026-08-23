"""
Proactive Issue Detection Engine (Bonus Feature).
Deterministic pipeline surfacing P1 tickets, SLA-risk tickets, known-issue correlations,
and cross-customer pattern detection.
"""

from typing import Dict, Any, List
import re

from backend.db import get_db_connection, DATASET_SNAPSHOT_TIME
from backend.rules_engine import classify_severity, calculate_sla_status, parse_iso_dt, SNAPSHOT_DT

def correlate_known_issue(ticket: Dict[str, Any]) -> Dict[str, Any]:
    """
    Explicit rule-based matching against the 3 Known Issues.
    Explains matches deterministically.
    """
    subject = str(ticket.get("subject", "")).lower()
    description = str(ticket.get("description", "")).lower()
    text = f"{subject} {description}"

    # KI-208: Bulk Upload failures on CSV > 3,000 rows
    if "bulk" in text or "csv" in text or "upload" in text:
        if re.search(r"fail|error|70%|row|limit", text):
            return {
                "matched": True,
                "issue_id": "KI-208",
                "title": "Bulk Upload failures on large CSVs",
                "status": "Investigating (Open)",
                "confidence": "High",
                "workaround": "Split CSV into files below 3,000 rows. Individual shipment creation is unaffected.",
                "supported_product_limit": "5,000 rows per CSV",
                "root_cause_summary": "Intermittent failure above ~3,000 rows despite product support up to 5,000 rows.",
                "source_reference": "04_Product_Operations_Guide_and_Known_Issues.pdf, §2 (KI-208)"
            }

    # KI-211: SwiftShip pickup webhook delay (up to 20 mins)
    if "swiftship" in text or "webhook" in text or ("driver" in text and "booked" in text) or ("pickup" in text and "booked" in text):
        return {
            "matched": True,
            "issue_id": "KI-211",
            "title": "SwiftShip pickup webhook delay",
            "status": "Monitoring (Open)",
            "confidence": "High",
            "guidance": "SwiftShip confirmation webhooks lag up to 20 minutes. Order may show BOOKED after physical pickup.",
            "source_reference": "04_Product_Operations_Guide_and_Known_Issues.pdf, §2 (KI-211)"
        }

    # KI-176: Address validation (Resolved 18 July 2026)
    # Strictly guarded against false positives! Must not correlate to new tickets.
    # Only matches if specifically asking about historical address validation from July 2026.
    if ("ki-176" in text or "176" in text) and "address" in text and "validation" in text:
        return {
            "matched": True,
            "issue_id": "KI-176",
            "title": "Address validation (Resolved)",
            "status": "Resolved (18 July 2026)",
            "confidence": "Historical Only",
            "note": "This issue was resolved on 18 July 2026. Do not use to explain new incidents unless specifically matching.",
            "source_reference": "04_Product_Operations_Guide_and_Known_Issues.pdf, §3 (KI-176 Resolved)"
        }

    return {
        "matched": False,
        "issue_id": None
    }

def run_proactive_detection() -> Dict[str, Any]:
    """
    Run complete proactive scan over all tickets and orders.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Load all accounts
        cursor.execute("SELECT * FROM accounts")
        accounts_by_id = {r["account_id"]: dict(r) for r in cursor.fetchall()}

        # Load all tickets
        cursor.execute("SELECT * FROM tickets")
        all_tickets = [dict(r) for r in cursor.fetchall()]

        # Load all orders
        cursor.execute("SELECT * FROM orders")
        all_orders = [dict(r) for r in cursor.fetchall()]

    finally:
        conn.close()

    p1_tickets = []
    sla_breached_tickets = []
    sla_at_risk_tickets = []
    known_issue_correlations = []
    analyzed_tickets = []

    for tkt in all_tickets:
        account = accounts_by_id.get(tkt["account_id"], {})
        account_name = account.get("account_name", tkt["account_id"])

        # 1. Severity Classification
        severity_info = classify_severity(tkt)
        tkt_severity = severity_info["severity"]

        # 2. SLA Computation
        sla_info = calculate_sla_status(tkt, account)

        # 3. Known Issue Correlation
        ki_info = correlate_known_issue(tkt)

        tkt_summary = {
            "ticket_id": tkt["ticket_id"],
            "account_id": tkt["account_id"],
            "account_name": account_name,
            "plan": account.get("plan"),
            "status": tkt["status"],
            "subject": tkt["subject"],
            "description": tkt["description"],
            "created_at": tkt["created_at"],
            "severity": tkt_severity,
            "severity_label": severity_info["label"],
            "sla_target": sla_info.get("target"),
            "is_24x7": sla_info.get("is_24x7", False),
            "elapsed_minutes": sla_info.get("elapsed_since_creation_minutes"),
            "elapsed_hours": sla_info.get("elapsed_since_creation_hours"),
            "is_breached": sla_info.get("is_breached_at_snapshot", False),
            "escalation_recommended": sla_info.get("escalation_recommended", False),
            "known_issue": ki_info if ki_info["matched"] else None,
            "source_reference": sla_info.get("source_reference")
        }

        analyzed_tickets.append(tkt_summary)

        if tkt_severity == "P1":
            p1_tickets.append(tkt_summary)

        if sla_info.get("is_breached_at_snapshot"):
            sla_breached_tickets.append(tkt_summary)
        elif sla_info.get("is_24x7") and sla_info.get("elapsed_since_creation_minutes", 0) > (sla_info.get("target_minutes", 60) * 0.7):
            sla_at_risk_tickets.append(tkt_summary)

        if ki_info["matched"]:
            known_issue_correlations.append({
                "ticket_id": tkt["ticket_id"],
                "account_name": account_name,
                "subject": tkt["subject"],
                "correlation": ki_info
            })

    # Pattern Detection across customer base
    patterns = []
    # Pattern 1: CSV upload issue pattern
    csv_tickets = [t for t in analyzed_tickets if t.get("known_issue") and t["known_issue"]["issue_id"] == "KI-208"]
    if csv_tickets:
        patterns.append({
            "pattern_id": "PAT-CSV-01",
            "title": "Cross-Account Bulk CSV Upload Degradation",
            "severity": "Medium",
            "affected_accounts": list(set(t["account_name"] for t in csv_tickets)),
            "affected_tickets": [t["ticket_id"] for t in csv_tickets],
            "description": "Multiple customers encountering 70% failure on CSV uploads > 3,000 rows. Workaround available.",
            "recommended_action": "Inform customers to split files < 3,000 rows until engineering fix lands."
        })

    # Pattern 2: SwiftShip webhook lag
    swiftship_tickets = [t for t in analyzed_tickets if t.get("known_issue") and t["known_issue"]["issue_id"] == "KI-211"]
    if swiftship_tickets:
        patterns.append({
            "pattern_id": "PAT-SWIFT-01",
            "title": "SwiftShip Pickup Webhook Latency (Up to 20 mins)",
            "severity": "Low/Informational",
            "affected_accounts": list(set(t["account_name"] for t in swiftship_tickets)),
            "affected_tickets": [t["ticket_id"] for t in swiftship_tickets],
            "description": "Drivers have collected parcels but webhook arrives up to 20 min later causing false BOOKED status.",
            "recommended_action": "Advise support agents not to trigger missing pickup refunds before the 20-minute window."
        })

    # Pattern 3: Outage / Security P1s
    if p1_tickets:
        patterns.append({
            "pattern_id": "PAT-CRIT-01",
            "title": f"Active Critical Incidents ({len(p1_tickets)} P1 Tickets)",
            "severity": "Critical",
            "affected_accounts": [t["account_name"] for t in p1_tickets],
            "affected_tickets": [t["ticket_id"] for t in p1_tickets],
            "description": "Critical issues requiring immediate response (outage and API key leaks).",
            "recommended_action": "Prepare escalation and request confirmation; notify account CSMs."
        })

    return {
        "snapshot_time": DATASET_SNAPSHOT_TIME,
        "total_tickets": len(all_tickets),
        "p1_critical_count": len(p1_tickets),
        "sla_breached_count": len(sla_breached_tickets),
        "p1_tickets": p1_tickets,
        "sla_breached_tickets": sla_breached_tickets,
        "sla_at_risk_tickets": sla_at_risk_tickets,
        "known_issue_correlations": known_issue_correlations,
        "cross_customer_patterns": patterns,
        "all_analyzed_tickets": analyzed_tickets
    }
