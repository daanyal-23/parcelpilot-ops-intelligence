"""
Document index with structured metadata, topic tags, and precedence resolution engine.
Grounded strictly in the 6 supplied PDFs. Historical resolutions are explicitly excluded.
"""

from typing import List, Dict, Any, Optional

DOCUMENT_CHUNKS: List[Dict[str, Any]] = [
    # --- 01_Support_Policy_v3_CURRENT.pdf ---
    {
        "chunk_id": "DOC-01-SEC-01",
        "document_id": "01_Support_Policy_v3_CURRENT.pdf",
        "title": "Scope and source precedence",
        "source_type": "policy",
        "status": "current",
        "effective_date": "2026-05-01",
        "scope": "general",
        "account_id": None,
        "topic": "general",
        "topic_rules": [
            {
                "topic": "precedence",
                "relationship": "general_rule",
                "hierarchy": [
                    "signed_customer_agreement",
                    "current_support_policy",
                    "current_product_documentation"
                ],
                "historical_note": "Historical tickets and internal notes are context only and may contain incorrect past guidance."
            }
        ],
        "content": (
            "This policy defines default support severity and response targets. A signed customer agreement may override "
            "these defaults. When sources conflict, use the signed customer agreement first, then the current support policy, "
            "then current product documentation. Historical tickets and internal notes are context only and may contain "
            "incorrect past guidance."
        ),
        "source_reference": "01_Support_Policy_v3_CURRENT.pdf, §1 (Scope and source precedence)"
    },
    {
        "chunk_id": "DOC-01-SEC-02",
        "document_id": "01_Support_Policy_v3_CURRENT.pdf",
        "title": "Severity definitions",
        "source_type": "policy",
        "status": "current",
        "effective_date": "2026-05-01",
        "scope": "general",
        "account_id": None,
        "topic": "sla",
        "topics": ["sla", "security", "severity_definitions"],
        "keywords": ["security", "security incident", "credential exposure", "api key", "api key exposure", "p1 critical", "p1", "severity"],
        "topic_rules": [
            {
                "topic": "severity_definitions",
                "relationship": "general_rule"
            },
            {
                "topic": "security",
                "relationship": "general_rule"
            }
        ],
        "content": (
            "● P1 - Critical: Complete production outage preventing all shipment creation for a customer, confirmed security "
            "incident or suspected credential exposure, or another event causing immediate material business risk with no workaround.\n"
            "● P2 - High: Major feature unavailable or materially degraded for a customer, but core operations remain possible or "
            "a workaround exists.\n"
            "● P3 - Normal: Minor defect, how-to question, configuration request, or issue with limited operational impact."
        ),
        "source_reference": "01_Support_Policy_v3_CURRENT.pdf, §2 (Severity definitions)"
    },
    {
        "chunk_id": "DOC-01-SEC-03",
        "document_id": "01_Support_Policy_v3_CURRENT.pdf",
        "title": "Default first-response targets",
        "source_type": "policy",
        "status": "current",
        "effective_date": "2026-05-01",
        "scope": "general",
        "account_id": None,
        "topic": "sla",
        "topics": ["sla", "security"],
        "keywords": ["security", "security incident", "credential exposure", "api key", "api key exposure", "p1 response target", "enterprise sla"],
        "topic_rules": [
            {
                "topic": "sla",
                "relationship": "general_rule",
                "targets": {
                    "Enterprise": {"P1": "30 minutes, 24x7", "P2": "2 hours", "P3": "1 business day"},
                    "Growth": {"P1": "2 business hours", "P2": "4 business hours", "P3": "2 business days"},
                    "Standard": {"P1": "4 business hours", "P2": "1 business day", "P3": "2 business days"}
                }
            },
            {
                "topic": "security",
                "relationship": "general_rule"
            }
        ],
        "content": (
            "Default first-response targets:\n"
            "- Enterprise: P1: 30 minutes, 24x7 | P2: 2 hours | P3: 1 business day\n"
            "- Growth: P1: 2 business hours | P2: 4 business hours | P3: 2 business days\n"
            "- Standard: P1: 4 business hours | P2: 1 business day | P3: 2 business days"
        ),
        "source_reference": "01_Support_Policy_v3_CURRENT.pdf, §3 (Default first-response targets)"
    },
    {
        "chunk_id": "DOC-01-SEC-04",
        "document_id": "01_Support_Policy_v3_CURRENT.pdf",
        "title": "Escalation",
        "source_type": "policy",
        "status": "current",
        "effective_date": "2026-05-01",
        "scope": "general",
        "account_id": None,
        "topic": "sla",
        "topics": ["sla", "security", "escalation"],
        "keywords": ["security", "security incident", "credential exposure", "api key", "api key exposure", "p1 escalation", "escalate immediately"],
        "topic_rules": [
            {
                "topic": "escalation",
                "relationship": "general_rule"
            },
            {
                "topic": "security",
                "relationship": "general_rule"
            }
        ],
        "content": (
            "P1 incidents should be escalated immediately. If a response target is already breached, the agent should clearly "
            "state the breach and recommend escalation rather than hiding uncertainty."
        ),
        "source_reference": "01_Support_Policy_v3_CURRENT.pdf, §4 (Escalation)"
    },

    # --- 02_Support_Policy_v2_DEPRECATED.pdf ---
    {
        "chunk_id": "DOC-02-SEC-01",
        "document_id": "02_Support_Policy_v2_DEPRECATED.pdf",
        "title": "Deprecated Support Policy v2",
        "source_type": "policy",
        "status": "deprecated",
        "effective_date": "2025-01-01",
        "scope": "general",
        "account_id": None,
        "topic": "sla",
        "topic_rules": [
            {
                "topic": "sla",
                "relationship": "superseded_by_v3"
            }
        ],
        "content": (
            "Status: DEPRECATED - DO NOT USE FOR CURRENT REQUESTS. Effective: 1 January 2025. Superseded by: Support Policy v3 effective 1 May 2026.\n"
            "Severity and response targets under v2:\n"
            "- Enterprise: P1: 1 hour | P2: 4 hours | P3: 2 business days\n"
            "- Growth: P1: 4 business hours | P2: 1 business day | P3: 3 business days\n"
            "- Standard: P1: 8 business hours | P2: 2 business days | P3: 3 business days\n"
            "Note: This file is intentionally retained for historical reference and must not be used as current policy."
        ),
        "source_reference": "02_Support_Policy_v2_DEPRECATED.pdf (Deprecated 1 Jan 2025 policy)"
    },

    # --- 03_Cancellation_and_Service_Credit_SOP_v4.pdf ---
    {
        "chunk_id": "DOC-03-SEC-01",
        "document_id": "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
        "title": "Order cancellation",
        "source_type": "sop",
        "status": "current",
        "effective_date": "2026-06-15",
        "scope": "general",
        "account_id": None,
        "topic": "cancellation",
        "topic_rules": [
            {
                "topic": "cancellation",
                "relationship": "general_rule",
                "draft": "May be cancelled with no fee.",
                "booked_under_30m": "No fee within 30 minutes of booking.",
                "booked_after_30m": "Charge INR 250 unless customer agreement explicitly waives.",
                "picked_up": "Do not cancel. Use return-to-origin workflow.",
                "delivered": "Cannot be cancelled."
            }
        ],
        "content": (
            "● DRAFT: May be cancelled with no fee.\n"
            "● BOOKED, not yet PICKED_UP: May be cancelled. No fee within 30 minutes of booking. After 30 minutes, charge INR 250 "
            "unless a customer agreement explicitly waives the cancellation fee.\n"
            "● PICKED_UP: Do not cancel. Use the return-to-origin workflow if the customer wants the parcel returned.\n"
            "● DELIVERED: Cannot be cancelled."
        ),
        "source_reference": "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1 (Order cancellation)"
    },
    {
        "chunk_id": "DOC-03-SEC-02",
        "document_id": "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
        "title": "Failed-pickup service credits",
        "source_type": "sop",
        "status": "current",
        "effective_date": "2026-06-15",
        "scope": "general",
        "account_id": None,
        "topic": "service_credit",
        "topic_rules": [
            {
                "topic": "service_credit",
                "relationship": "general_rule",
                "timing_threshold": "> 2 hours past pickup window end",
                "conditions": ["carrier_fault == true", "customer_fault == false"],
                "credit_amount": "lower of INR 500 or 10% of shipment fee",
                "override_note": "A signed customer agreement may replace the default delay threshold, credit amount, or cap."
            }
        ],
        "content": (
            "Under the default policy, a customer is eligible for a service credit when the pickup is more than 2 hours past "
            "the end of the scheduled pickup window, the carrier is at fault, and there is no customer-caused issue. "
            "The default credit is the lower of INR 500 or 10% of the shipment fee. A signed customer agreement may replace "
            "the default delay threshold, credit amount, or cap."
        ),
        "source_reference": "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §2 (Failed-pickup service credits)"
    },
    {
        "chunk_id": "DOC-03-SEC-03",
        "document_id": "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
        "title": "Approval and uncertainty",
        "source_type": "sop",
        "status": "current",
        "effective_date": "2026-06-15",
        "scope": "general",
        "account_id": None,
        "topic": "service_credit",
        "topic_rules": [
            {
                "topic": "approval_threshold",
                "relationship": "general_rule",
                "manager_threshold_inr": 1000,
                "rule": "Any individual credit above INR 1,000 requires manager approval."
            }
        ],
        "content": (
            "● Any individual credit above INR 1,000 requires manager approval.\n"
            "● Do not promise a credit when carrier fault, pickup timing, or customer fault is unknown.\n"
            "● When data conflicts, identify the conflict and request verification before a state-changing action."
        ),
        "source_reference": "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §3 (Approval and uncertainty)"
    },

    # --- 04_Product_Operations_Guide_and_Known_Issues.pdf ---
    {
        "chunk_id": "DOC-04-SEC-01",
        "document_id": "04_Product_Operations_Guide_and_Known_Issues.pdf",
        "title": "Plan capabilities",
        "source_type": "guide",
        "status": "current",
        "effective_date": "2026-08-14",
        "scope": "general",
        "account_id": None,
        "topic": "operations",
        "topic_rules": [
            {
                "topic": "capabilities",
                "bulk_upload_limit": 5000,
                "plans_with_bulk_upload": ["Growth", "Enterprise"]
            }
        ],
        "content": (
            "● Bulk Upload: Available on Growth and Enterprise. Supported file size is up to 5,000 rows per CSV.\n"
            "● Standard: Bulk Upload is not included.\n"
            "● Shipment status: BOOKED means the shipment is created but ParcelPilot has not yet received a pickup confirmation. "
            "PICKED_UP means carrier pickup has been confirmed."
        ),
        "source_reference": "04_Product_Operations_Guide_and_Known_Issues.pdf, §1 (Plan capabilities)"
    },
    {
        "chunk_id": "DOC-04-SEC-02-KI208",
        "document_id": "04_Product_Operations_Guide_and_Known_Issues.pdf",
        "title": "KI-208 - Bulk Upload failures on large CSVs",
        "source_type": "guide",
        "status": "current",
        "effective_date": "2026-08-10",
        "scope": "general",
        "account_id": None,
        "topic": "known_issue",
        "topic_rules": [
            {
                "topic": "known_issue",
                "issue_id": "KI-208",
                "issue_status": "Investigating",
                "workaround": "Split the upload into files below 3,000 rows. Individual shipment creation unaffected.",
                "supported_limit": 5000,
                "failure_threshold": "~3,000 rows"
            }
        ],
        "content": (
            "KI-208 - Bulk Upload failures on large CSVs\n"
            "Opened: 10 August 2026 | Status: Investigating\n"
            "Some Growth and Enterprise customers experience intermittent failures on CSV uploads above approximately 3,000 rows, "
            "even though the supported product limit remains 5,000 rows. Workaround: split the upload into files below 3,000 rows. "
            "Individual shipment creation is unaffected."
        ),
        "source_reference": "04_Product_Operations_Guide_and_Known_Issues.pdf, §2 (KI-208)"
    },
    {
        "chunk_id": "DOC-04-SEC-02-KI211",
        "document_id": "04_Product_Operations_Guide_and_Known_Issues.pdf",
        "title": "KI-211 - SwiftShip pickup webhook delay",
        "source_type": "guide",
        "status": "current",
        "effective_date": "2026-08-12",
        "scope": "general",
        "account_id": None,
        "topic": "known_issue",
        "topic_rules": [
            {
                "topic": "known_issue",
                "issue_id": "KI-211",
                "issue_status": "Monitoring",
                "carrier": "SwiftShip",
                "delay_minutes": 20
            }
        ],
        "content": (
            "KI-211 - SwiftShip pickup webhook delay\n"
            "Opened: 12 August 2026 | Status: Monitoring\n"
            "SwiftShip pickup confirmation webhooks can arrive up to 20 minutes late. A parcel may physically be collected "
            "while ParcelPilot still shows BOOKED. Before telling a customer that a pickup did not occur, verify the carrier "
            "status or wait through the known delay window."
        ),
        "source_reference": "04_Product_Operations_Guide_and_Known_Issues.pdf, §2 (KI-211)"
    },
    {
        "chunk_id": "DOC-04-SEC-03-KI176",
        "document_id": "04_Product_Operations_Guide_and_Known_Issues.pdf",
        "title": "KI-176 - Address validation (Resolved)",
        "source_type": "guide",
        "status": "resolved",
        "effective_date": "2026-07-18",
        "scope": "general",
        "account_id": None,
        "topic": "known_issue",
        "topic_rules": [
            {
                "topic": "known_issue",
                "issue_id": "KI-176",
                "issue_status": "Resolved",
                "resolved_date": "2026-07-18",
                "usage_constraint": "Do not use this resolved issue to explain new incidents unless evidence specifically matches it."
            }
        ],
        "content": (
            "KI-176 - Address validation: Resolved 18 July 2026. Do not use this resolved issue to explain new incidents "
            "unless evidence specifically matches it."
        ),
        "source_reference": "04_Product_Operations_Guide_and_Known_Issues.pdf, §3 (KI-176 Resolved)"
    },

    # --- 05_Northstar_Logistics_Enterprise_Agreement.pdf ---
    {
        "chunk_id": "DOC-05-SEC-01",
        "document_id": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
        "title": "Northstar Support terms",
        "source_type": "agreement",
        "status": "active",
        "effective_date": "2026-01-01",
        "scope": "account_specific",
        "account_id": "ACCT-001",
        "topic": "sla",
        "topic_rules": [
            {
                "topic": "sla",
                "relationship": "full_override",
                "overridden_fields": ["P1", "P2", "P3"],
                "targets": {
                    "P1": "15 minutes, 24x7",
                    "P2": "1 hour",
                    "P3": "8 business hours"
                }
            }
        ],
        "content": (
            "For Northstar Logistics, the following first-response targets replace ParcelPilot's standard support-policy targets:\n"
            "● P1: 15 minutes, 24x7\n"
            "● P2: 1 hour\n"
            "● P3: 8 business hours"
        ),
        "source_reference": "05_Northstar_Logistics_Enterprise_Agreement.pdf, §1 (Support terms)"
    },
    {
        "chunk_id": "DOC-05-SEC-02",
        "document_id": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
        "title": "Northstar Shipment cancellation",
        "source_type": "agreement",
        "status": "active",
        "effective_date": "2026-01-01",
        "scope": "account_specific",
        "account_id": "ACCT-001",
        "topic": "cancellation",
        "topic_rules": [
            {
                "topic": "cancellation",
                "relationship": "full_override",
                "scope_condition": "BOOKED before pickup only",
                "fee_inr": 0,
                "picked_up_rule": "Once a shipment is PICKED_UP, the standard return-to-origin process applies."
            }
        ],
        "content": (
            "Northstar may cancel any BOOKED shipment before pickup with no cancellation fee, regardless of how long ago "
            "the shipment was booked. Once a shipment is PICKED_UP, the standard return-to-origin process applies."
        ),
        "source_reference": "05_Northstar_Logistics_Enterprise_Agreement.pdf, §2 (Shipment cancellation)"
    },
    {
        "chunk_id": "DOC-05-SEC-03",
        "document_id": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
        "title": "Northstar Service credits",
        "source_type": "agreement",
        "status": "active",
        "effective_date": "2026-01-01",
        "scope": "account_specific",
        "account_id": "ACCT-001",
        "topic": "service_credit",
        "topic_rules": [
            {
                "topic": "service_credit",
                "relationship": "partial_override",
                "monthly_cap_inr": 5000,
                "cap_enforceability": "Unenforceable in current dataset due to lack of credit issuance history ledger; disclose limitation",
                "inherited_fields": ["timing_threshold", "credit_amount", "conditions", "manager_approval_threshold"]
            }
        ],
        "content": (
            "Monthly aggregate service credits are capped at INR 5,000. Unless this agreement states otherwise, the current "
            "ParcelPilot service-credit SOP applies."
        ),
        "source_reference": "05_Northstar_Logistics_Enterprise_Agreement.pdf, §3 (Service credits)"
    },
    {
        "chunk_id": "DOC-05-SEC-04",
        "document_id": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
        "title": "Northstar Account contact",
        "source_type": "agreement",
        "status": "active",
        "effective_date": "2026-01-01",
        "scope": "account_specific",
        "account_id": "ACCT-001",
        "topic": "general",
        "topic_rules": [
            {"topic": "contact", "csm": "Priya Mehta"}
        ],
        "content": "Dedicated CSM: Priya Mehta.",
        "source_reference": "05_Northstar_Logistics_Enterprise_Agreement.pdf, §4 (Account contact)"
    },

    # --- 06_LumenWorks_Service_Agreement.pdf ---
    {
        "chunk_id": "DOC-06-SEC-01",
        "document_id": "06_LumenWorks_Service_Agreement.pdf",
        "title": "LumenWorks Support terms",
        "source_type": "agreement",
        "status": "active",
        "effective_date": "2026-03-01",
        "scope": "account_specific",
        "account_id": "ACCT-002",
        "topic": "sla",
        "topic_rules": [
            {
                "topic": "sla",
                "relationship": "full_override",
                "targets": {
                    "P1": "2 business hours",
                    "P2": "4 business hours",
                    "P3": "2 business days"
                },
                "coverage": "No weekend or after-hours support coverage."
            }
        ],
        "content": (
            "Support terms:\n"
            "● P1: 2 business hours\n"
            "● P2: 4 business hours\n"
            "● P3: 2 business days\n"
            "● No weekend or after-hours support coverage."
        ),
        "source_reference": "06_LumenWorks_Service_Agreement.pdf, §1 (Support terms)"
    },
    {
        "chunk_id": "DOC-06-SEC-02",
        "document_id": "06_LumenWorks_Service_Agreement.pdf",
        "title": "LumenWorks Cancellation terms",
        "source_type": "agreement",
        "status": "active",
        "effective_date": "2026-03-01",
        "scope": "account_specific",
        "account_id": "ACCT-002",
        "topic": "cancellation",
        "topic_rules": [
            {
                "topic": "cancellation",
                "relationship": "defers_to_general",
                "governing_document": "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
                "rule": "No special cancellation-fee waiver applies. Use the current ParcelPilot Cancellation & Service Credit SOP."
            }
        ],
        "content": (
            "Cancellation terms: No special cancellation-fee waiver applies. Use the current ParcelPilot Cancellation & "
            "Service Credit SOP."
        ),
        "source_reference": "06_LumenWorks_Service_Agreement.pdf, §2 (Cancellation terms)"
    },
    {
        "chunk_id": "DOC-06-SEC-03",
        "document_id": "06_LumenWorks_Service_Agreement.pdf",
        "title": "LumenWorks Failed-pickup credits",
        "source_type": "agreement",
        "status": "active",
        "effective_date": "2026-03-01",
        "scope": "account_specific",
        "account_id": "ACCT-002",
        "topic": "service_credit",
        "topic_rules": [
            {
                "topic": "service_credit",
                "relationship": "full_override",
                "timing_threshold": "> 4 hours past pickup window end",
                "conditions": ["carrier_fault == true", "customer_fault == false"],
                "credit_amount_inr": 300,
                "replaces": "Replaces default failed-pickup credit amount (lower of 500 or 10%) and timing threshold (>2hrs) in SOP."
            }
        ],
        "content": (
            "If a pickup is more than 4 hours past the end of the scheduled pickup window, the carrier is at fault, and the "
            "customer is not at fault, LumenWorks receives a fixed INR 300 service credit. This clause replaces the default "
            "failed-pickup credit amount and timing threshold in the SOP."
        ),
        "source_reference": "06_LumenWorks_Service_Agreement.pdf, §3 (Failed-pickup credits)"
    }
]

def source_resolution(topic: str, account_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Implements the §4 precedence table deterministically.
    """
    if account_id == "ACCT-001":  # Northstar Logistics
        if topic == "sla":
            return {
                "authoritative_document": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
                "source_reference": "05_Northstar_Logistics_Enterprise_Agreement.pdf, §1",
                "relationship": "full_override",
                "explanation": "Northstar's custom enterprise agreement overrides standard SLA targets (P1 15min / P2 1hr / P3 8biz-hr, 24x7)."
            }
        elif topic == "cancellation":
            return {
                "authoritative_document": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
                "source_reference": "05_Northstar_Logistics_Enterprise_Agreement.pdf, §2",
                "relationship": "full_override_booked_prepickup_only",
                "explanation": "Northstar custom agreement waives cancellation fee (INR 0) for BOOKED pre-pickup shipments at any time. However, once PICKED_UP, standard return-to-origin applies with no cancellation."
            }
        elif topic == "service_credit":
            return {
                "authoritative_document": "05_Northstar_Logistics_Enterprise_Agreement.pdf + 03_Cancellation_and_Service_Credit_SOP_v4.pdf",
                "source_reference": "05_Northstar_Logistics_Enterprise_Agreement.pdf, §3 & 03_Cancellation_and_Service_Credit_SOP_v4.pdf, §2",
                "relationship": "partial_override",
                "explanation": "SOP mechanics and eligibility apply (>2hrs late, carrier fault, no customer fault -> lower of 500 or 10%). Agreement adds INR 5,000/month aggregate cap (disclosed limitation: unenforceable without historical credit ledger)."
            }

    elif account_id == "ACCT-002":  # LumenWorks
        if topic == "sla":
            return {
                "authoritative_document": "06_LumenWorks_Service_Agreement.pdf",
                "source_reference": "06_LumenWorks_Service_Agreement.pdf, §1",
                "relationship": "full_override",
                "explanation": "LumenWorks custom agreement governs (P1 2biz-hr / P2 4biz-hr / P3 2biz-days with no weekend/after-hours coverage). Always cite the agreement even though numeric targets match Growth plan defaults."
            }
        elif topic == "cancellation":
            return {
                "authoritative_document": "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
                "source_reference": "06_LumenWorks_Service_Agreement.pdf, §2 -> 03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1",
                "relationship": "defers_to_general",
                "explanation": "LumenWorks agreement §2 explicitly states no special cancellation waiver applies and defers to general SOP (INR 250 fee after 30 min of booking for BOOKED shipments)."
            }
        elif topic == "service_credit":
            return {
                "authoritative_document": "06_LumenWorks_Service_Agreement.pdf",
                "source_reference": "06_LumenWorks_Service_Agreement.pdf, §3",
                "relationship": "full_override",
                "explanation": "LumenWorks custom agreement overrides SOP: Fixed INR 300 credit if pickup is >4 hours late (instead of SOP's >2hrs and lower of 500 or 10%), with carrier fault and no customer fault."
            }

    elif account_id in ["ACCT-003", "ACCT-004"] or account_id is None:
        # Beacon Retail (ACCT-003: Standard) or Axis Labs (ACCT-004: Enterprise) or general inquiry
        if topic == "sla":
            return {
                "authoritative_document": "01_Support_Policy_v3_CURRENT.pdf",
                "source_reference": "01_Support_Policy_v3_CURRENT.pdf, §3",
                "relationship": "general_policy",
                "explanation": "No custom agreement exists; general Support Policy v3 applies based on account subscription tier."
            }
        elif topic in ["security", "incident", "credential"]:
            return {
                "authoritative_document": "01_Support_Policy_v3_CURRENT.pdf",
                "source_reference": "01_Support_Policy_v3_CURRENT.pdf, §2, §3 & §4",
                "relationship": "general_policy",
                "explanation": "No custom agreement exists; general Support Policy v3 applies (suspected credential exposure is classified as P1 Critical under §2, requiring 30-min 24x7 response for Enterprise under §3 and immediate escalation under §4)."
            }
        elif topic == "cancellation":
            return {
                "authoritative_document": "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
                "source_reference": "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §1",
                "relationship": "general_sop",
                "explanation": "No custom agreement exists; general Cancellation & Service Credit SOP v4 applies (INR 250 fee after 30 min of booking for BOOKED shipments)."
            }
        elif topic == "service_credit":
            return {
                "authoritative_document": "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
                "source_reference": "03_Cancellation_and_Service_Credit_SOP_v4.pdf, §2",
                "relationship": "general_sop",
                "explanation": "No custom agreement exists; general Cancellation & Service Credit SOP v4 applies (lower of INR 500 or 10% of shipment fee if >2 hours late, carrier fault, no customer fault)."
            }

    if topic in ["security", "incident", "credential"]:
        return {
            "authoritative_document": "01_Support_Policy_v3_CURRENT.pdf",
            "source_reference": "01_Support_Policy_v3_CURRENT.pdf, §2, §3 & §4",
            "relationship": "general_policy",
            "explanation": "General Support Policy v3 §2, §3, and §4 govern security incidents and suspected credential exposure."
        }

    return {
        "authoritative_document": "01_Support_Policy_v3_CURRENT.pdf / 03_Cancellation_and_Service_Credit_SOP_v4.pdf",
        "source_reference": "General Current Documentation",
        "relationship": "general_standard",
        "explanation": "General current documentation applies."
    }

def search_documents_index(
    query: str = "",
    topic: Optional[str] = None,
    account_id: Optional[str] = None,
    include_historical: bool = False
) -> Dict[str, Any]:
    """
    Deterministic document search filtering by query, topic, account_id, and status.
    Historical tickets are strictly excluded.
    Deprecated documents are excluded unless include_historical is explicitly True or 'v2' / 'deprecated' in query.
    """
    q_lower = query.lower().strip() if query else ""
    want_deprecated = include_historical or "v2" in q_lower or "deprecated" in q_lower or "old" in q_lower or "prior" in q_lower

    # Detect security intent in query or topic
    security_terms = [
        "api key exposure",
        "credential exposure",
        "security incident",
        "suspected credential exposure",
        "api key",
        "credential",
        "security"
    ]
    is_security_query = any(term in q_lower for term in security_terms)
    is_security_topic = bool(topic and topic.lower() in ("security", "incident", "credential", "credential_exposure"))

    effective_topic = topic.lower() if topic else None
    if is_security_topic:
        effective_topic = "security"

    results = []
    for chunk in DOCUMENT_CHUNKS:
        # Status filter
        if chunk["status"] == "deprecated" and not want_deprecated:
            continue
        if chunk["status"] != "deprecated" and want_deprecated and ("v2" in q_lower or "deprecated" in q_lower):
            # If user explicitly asked for deprecated, focus on deprecated
            pass

        # Topic filter
        if effective_topic and effective_topic != "all":
            chunk_topics = [t.lower() for t in chunk.get("topics", [chunk["topic"]])]
            matches_topic = (
                chunk["topic"].lower() == effective_topic or
                effective_topic in chunk_topics or
                effective_topic in chunk["title"].lower() or
                chunk["topic"] == "general"
            )
            # Route security-related queries to authoritative Support Policy chunks even if topic was 'known_issue' or 'operations'
            if not matches_topic and is_security_query and chunk["chunk_id"] in ("DOC-01-SEC-02", "DOC-01-SEC-03", "DOC-01-SEC-04"):
                matches_topic = True

            if not matches_topic:
                continue

        # Account ID filter
        if account_id:
            # If chunk is account-specific, it must match account_id
            if chunk["scope"] == "account_specific" and chunk["account_id"] != account_id:
                continue

        # Content/keyword relevance
        if q_lower:
            words = [w for w in q_lower.split() if len(w) > 2]
            match_score = 0
            chunk_keywords = " ".join(chunk.get("keywords", []))
            chunk_text = (chunk["title"] + " " + chunk["content"] + " " + chunk["document_id"] + " " + chunk_keywords).lower()
            for w in words:
                if w in chunk_text:
                    match_score += 1

            # Ensure security queries retrieve the authoritative security policy chunks §2, §3, §4
            if is_security_query and chunk["chunk_id"] in ("DOC-01-SEC-02", "DOC-01-SEC-03", "DOC-01-SEC-04"):
                match_score += 1

            if words and match_score == 0:
                continue

        results.append({
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "title": chunk["title"],
            "topic": chunk["topic"],
            "scope": chunk["scope"],
            "account_id": chunk["account_id"],
            "status": chunk["status"],
            "authority": "authoritative" if chunk["status"] != "deprecated" else "historical_reference_only",
            "source_reference": chunk["source_reference"],
            "content": chunk["content"]
        })

    # Add resolution
    resolution = None
    if effective_topic:
        resolution = source_resolution(effective_topic, account_id)
    elif is_security_query:
        resolution = source_resolution("security", account_id)

    return {
        "results": results,
        "count": len(results),
        "resolution": resolution
    }
