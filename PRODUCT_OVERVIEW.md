# Product Overview — ParcelPilot Operations Intelligence

## Problem

In high-volume logistics and freight operations, support and operations teams operate in an environment where decisions carry immediate legal and financial consequences. Before an operational decision or action can be taken, operators must synthesize information across multiple disparate sources:

- **Customer & Account Context**: Plan tiers (Standard, Growth, Enterprise), dedicated CSM assignments, premium support entitlements, and bespoke commercial agreements.
- **Live Shipment State**: Granular milestone statuses (`BOOKED`, `PICKED_UP`, `IN_TRANSIT`, `DELIVERED`, `EXCEPTION`), carrier assignments, and timestamped event sequences.
- **Contractual Overrides & Support Policies**: Standard service level agreements (SLAs), general standard operating procedures (SOPs), and signed enterprise agreements with bespoke terms that supersede baseline policies.
- **Known Technical Issues**: Ongoing platform bugs, carrier webhook ingestion delays, and batch processing limits that explain anomalous operational symptoms without being isolated carrier failures.
- **SLA Commitments**: Severity tiers (P1 through P3), first-response targets, and resolution requirements.
- **Authorization & Approval Boundaries**: Financial spending limits and role-specific permissions (e.g., support agent vs. manager approval thresholds).

When support teams rely on manual documentation searches, tribal knowledge, or unstructured AI chatbots, they risk issuing unauthorized refunds, calculating incorrect cancellation fees, misinterpreting contractual terms, or missing high-severity operational outages.

## Solution

**ParcelPilot Operations Intelligence** is a full-stack internal operations platform designed around a simulated logistics environment. The platform bridges natural language interactions with deterministic operational backend controls.

Rather than delegating business truth to a probabilistic language model, the system establishes a strict separation of concerns:
- **LLM Reasoning & Orchestration**: An LLM agent parses natural language questions, extracts intents and entities, selects appropriate operational tools, and explains outcomes with natural language clarity.
- **Deterministic Backend Authority**: Data queries, contract precedence resolution, SLA timers, fee calculations, credit eligibility, role-based authorization, and state mutations are executed in deterministic Python and SQLite code.
- **Human-in-the-Loop Safeguards**: State-altering operations follow a two-phase prepare/confirm lifecycle, preventing automated mutations while streamlining operator execution.

## Core Workflows

### Incident Investigation
When an inquiry or ticket arises, the platform correlates customer identity, order details, and historical ticket notes. It audits historical ticket resolutions against current governing contracts—identifying non-authoritative claims or historical inaccuracies—and checks for correlations with active known platform issues (e.g., carrier webhook lags or bulk upload limits) while rejecting false correlations with resolved incidents.

### Contract & Policy Resolution
The platform resolves governing rules using a structured precedence hierarchy:
1. **Signed Customer Agreements**: Specific terms negotiated by enterprise accounts (e.g., Northstar Logistics, LumenWorks) override baseline policies.
2. **Current Policies & SOPs**: Governing Support Policy v3 and Cancellation & Service Credit SOP v4 establish defaults for accounts without custom clauses.
3. **Product Operations Guides**: Technical guides provide operational limits and platform incident context.
4. **Historical & Deprecated Documents**: Deprecated policies (e.g., Support Policy v2) and past ticket resolutions are explicitly segregated and never treated as current authority.

### Operational Calculations
All financial and SLA calculations are executed deterministically by a dedicated backend rules engine:
- **Cancellation Fees**: Evaluates milestone status (e.g., `BOOKED` vs. `PICKED_UP`), elapsed time from booking, and custom contract overrides (such as Northstar's ₹0 cancellation fee for pre-pickup orders vs. standard tiered fees).
- **Service Credit Eligibility**: Evaluates pickup delays, carrier fault determinations, scheduled windows, and contractual minimum delay thresholds (e.g., LumenWorks flat ₹300 credit for carrier delays >4 hours).
- **SLA Target Verification**: Evaluates 24x7 response windows against an operational snapshot timestamp.

### Safe Operational Actions
Any action that mutates operational state (`cancel_order`, `issue_credit`, `escalate_ticket`) is governed by defense-in-depth safety checks:
- **Two-Phase Action Lifecycle**: The agent invokes `prepare_action` to validate inputs and role authority, staging the action in a `pending_confirmation` state. An operator must review and confirm the action before `execute_action` runs.
- **Role Authorization**: Individual service credits exceeding ₹1,000 strictly require a `manager` role; attempts by support agents are rejected by the backend.
- **Execution Re-Validation**: Live shipment status is re-verified at the exact moment of execution (e.g., blocking cancellation if an order transitioned to `PICKED_UP` and requiring Return-to-Origin handling instead).
- **Audit Persistence**: Executed credits and actions are persisted in dedicated audit tables (`issued_credits`, `actions`).

### Proactive Operations Monitoring
A proactive intelligence engine continuously evaluates operational data without requiring user prompts:
- **P1 Critical Incident Detection**: Automatically surfaces critical outages (HTTP 500 shipment creation failures) and security vulnerabilities (API key exposure) with exact contract-specific SLA timers.
- **Deterministic 24x7 SLA Tracking**: Flags breached or at-risk 24x7 tickets against the reference snapshot.
- **Known-Issue Clustering**: Aggregates tickets impacted by active system issues to give operations teams real-time visibility into widespread incidents.
- **Cross-Customer Pattern Detection**: Identifies systemic failure patterns across multiple accounts before individual customer escalations occur.

## Current Scope & Design Trade-offs

| Area | Approach Taken | Engineering Rationale |
|---|---|---|
| **Authentication** | Server-side session tokens with role selection (`support_agent`, `manager`) | Prioritized robust backend role authorization guards and account isolation over integrating enterprise OAuth/SSO providers. |
| **Document Retrieval** | Structured metadata indexing | In a bounded set of legally binding policy documents, metadata-driven precedence eliminates vector search hallucinations, prevents cross-contract leakage, and guarantees exact section citations. |
| **Interaction Model** | Synchronous multi-turn agent turns | Synchronous execution enables structured JSON payloads containing verified tool traces, harvested citations, and interactive action confirmation cards. |
| **Action Execution** | Two-phase human confirmation | Prevents the model from autonomously mutating operational database records, maintaining strict human-in-the-loop oversight for cancellations, credits, and escalations. |
| **SLA Working Hours** | Strict `Calendar Undefined` status | Because the provided operational documents define business-hour SLAs (e.g., "4 business hours") without specifying shift schedules, weekend policies, or holiday calendars, the engine transparently marks them as `Calendar Undefined` rather than inventing an ungrounded 9-to-5 schedule. |

## Future Roadmap

1. **Live Carrier Webhook Ingestion**: Stream real-time carrier tracking webhooks to automatically resolve transient synchronization lags (such as KI-211) and update shipment milestones automatically.
2. **Historical Credit Ledger & Aggregate Caps**: Expand the credit ledger into a multi-period accounting system to enforce monthly aggregate customer credit limits (such as Northstar's ₹5,000 monthly cap).
3. **Automated Incident Escalation Alerts**: Dispatch automated webhook notifications to dedicated Customer Success Managers (CSMs) and on-call engineering channels when P1 incidents are detected.
4. **Configurable Business-Hour Calendar Engine**: Provide tenant-specific calendar configurations (operating hours, shift schedules, regional holidays, timezones) to calculate business-hour SLA compliance deterministically.

## Success Metrics

The platform's reliability and compliance were evaluated against an end-to-end suite of 21 deterministic validation scenarios covering contract overrides, operational calculations, role permissions, account isolation, and edge cases:

- **Decision Correctness**: **100.0% (21/21 scenarios passed)**
- **Authoritative Citation Verification**: **100.0% (21/21 scenarios verified)**

*Note: These metrics represent internal engineering validation and regression test results measuring system adherence to defined specifications, not claims of third-party adoption or production customer usage.*
