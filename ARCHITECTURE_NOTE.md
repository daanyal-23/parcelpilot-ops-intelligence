# Architecture Note — ParcelPilot Internal Support Agent

## 1. System Overview

The **ParcelPilot Internal Support Agent** is an enterprise operations AI system designed for authorized ParcelPilot support staff and operations managers. It investigates customer incidents, answers operational and contractual questions, deterministically calculates SLAs, fees, and credits, flags high-urgency tickets, and executes approved support actions through a strict two-phase confirmation protocol.

```mermaid
flowchart TB
    U["ParcelPilot Operations User<br/>Support Agent / Manager"]

    UI["React Frontend<br/>Chat • Operations Dashboard • Evaluation Suite"]

    API["FastAPI Backend<br/>REST API • Server-Side Sessions"]

    RESOLVE["Deterministic Account Resolution<br/>+ Session / Role Context"]

    AGENT["OpenAI Agent Loop<br/>GPT-5-mini + Native Function Calling"]

    DATA["Structured Data Tools"]
    DOCS["Document Search<br/>Metadata-Driven Precedence"]
    RULES["Deterministic Rules Engine<br/>SLA • Cancellation • Credits"]

    DB[("SQLite Database<br/>Accounts • Orders • Tickets<br/>Issued Credits • Sessions")]

    SOURCES["Authoritative Source Pack<br/>Signed Agreements • Current Policy/SOP<br/>Operations Guide"]

    GUARDS["Authorization & Ownership Guards<br/>Role Validation • Account Isolation"]

    PREP["prepare_action<br/>Validate + Persist Pending Action"]

    CONFIRM{"Explicit User Confirmation"}

    EXEC["execute_action<br/>Re-validate + Mutate"]

    RESPONSE["Grounded Response<br/>Decision + Evidence + Citations"]

    PROACTIVE["Proactive Issue Detection<br/>P1 • SLA Risk • Known Issues • Patterns"]

    DASH["Operations Dashboard"]

    U --> UI
    UI --> API
    API --> RESOLVE
    RESOLVE --> AGENT

    AGENT --> DATA
    AGENT --> DOCS
    AGENT --> RULES

    DATA --> DB
    RULES --> DB
    DOCS --> SOURCES

    DATA --> GUARDS
    RULES --> GUARDS
    GUARDS --> PREP

    PREP --> CONFIRM
    CONFIRM -->|Confirm| EXEC
    CONFIRM -->|Cancel| RESPONSE
    EXEC --> DB
    EXEC --> RESPONSE

    AGENT --> RESPONSE
    RESPONSE --> UI

    DB --> PROACTIVE
    SOURCES --> PROACTIVE
    PROACTIVE --> DASH
    DASH --> UI

    classDef user fill:#eef2ff,stroke:#6366f1,stroke-width:2px
    classDef frontend fill:#ecfeff,stroke:#0891b2,stroke-width:2px
    classDef backend fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
    classDef agent fill:#fefce8,stroke:#ca8a04,stroke-width:2px
    classDef data fill:#f8fafc,stroke:#475569,stroke-width:2px
    classDef safety fill:#fff7ed,stroke:#ea580c,stroke-width:2px
    classDef action fill:#fdf2f8,stroke:#db2777,stroke-width:2px
    classDef output fill:#f0fdfa,stroke:#0f766e,stroke-width:2px

    class U user
    class UI frontend
    class API,RESOLVE backend
    class AGENT agent
    class DATA,DOCS,RULES,DB,SOURCES data
    class GUARDS safety
    class PREP,CONFIRM,EXEC action
    class RESPONSE,PROACTIVE,DASH output
    ```

---

## 2. Core Architectural Principles & Decisions

### Principle 1: The LLM Does Not Own Business Truth
- **Decision**: The LLM functions strictly as an orchestrator and explainer. It never calculates elapsed time, assesses SLA breach status, determines cancellation fee amounts, or computes credit eligibility in memory.
- **Implementation**: Every calculation is executed in Python (`backend/rules_engine.py`) using deterministic code and verified against source document line items.
- **Provider & Model**: Powered by **OpenAI (`gpt-5-mini`)** (with `gpt-4o-mini` fallback compatibility) using the official `openai` Python SDK. The agent loop utilizes native OpenAI function calling with strict JSON schemas (`tools` parameter with `type: "function"`).

### Principle 2: Metadata-Driven Precedence Over Similarity
- **Decision**: Document retrieval is structured via explicit metadata tags rather than unconstrained semantic vector closeness.
- **Hierarchy Enforced**: `Signed Customer Agreement` > `Current Support Policy (v3) / Current SOP (v4)` > `Product Operations Guide`.
- **Precedence Mapping**:
  - **Northstar (ACCT-001)**: Full SLA override (P1 15m/P2 1h/P3 8h, 24x7); Full Cancellation override (₹0 for BOOKED pre-pickup only); Partial Service Credit override (SOP mechanics inherited; ₹5,000 monthly aggregate cap).
  - **LumenWorks (ACCT-002)**: Full SLA override (P1 2h/P2 4h/P3 2d, no weekend/after-hours); Defers to general SOP for cancellation; Full Service Credit override (flat ₹300 for >4h delay).
  - **Beacon Retail (ACCT-003)**: General Standard policy & general SOP.
  - **Axis Labs (ACCT-004)**: General Enterprise policy & general SOP.
- **Deprecated Isolation**: Deprecated Support Policy v2 is strictly filtered out of general retrieval and only surfaced when the user explicitly requests historical/deprecated terms.

### Principle 3: Non-Authoritative Historical Context
- **Decision**: Historical ticket resolutions (`historical_resolution`) are flagged `authoritative: false` at the schema level and completely excluded from document search index.
- **Implementation**: When an agent investigates historical tickets (e.g. TKT-450, TKT-451), the agent explains the historical note as investigational context, identifies errors against current agreements, and cites the true authoritative source.

### Principle 4: Server-Side Role-Based Authorization & Session Management
- **Decision**: The client cannot self-declare permissions. Role (`support_agent` vs `manager`) is stored server-side in user sessions (`user_sessions` table) created via `POST /api/login`.
- **Enforcement**: In accordance with `03_Cancellation_and_Service_Credit_SOP_v4.pdf` §3, individual service credits > ₹1,000 strictly require `manager` role. If a `support_agent` attempts to prepare or execute a credit > ₹1,000, the tool layer rejects the operation with structured error `INSUFFICIENT_AUTHORITY`.

### Principle 5: Two-Phase State-Changing Actions & Mutation Defense-in-Depth
- **Decision**: State-changing actions (`cancel_order`, `issue_credit`, `escalate_ticket`) follow a mandatory two-phase lifecycle:
  1. `prepare_action`: Validates inputs and role, persists action in `pending_confirmation` state, and returns action summary.
  2. `execute_action`: Requires explicit user confirmation via `POST /api/actions/{id}/confirm`. Re-checks role authorization, action expiry window (24h), and independent business eligibility before mutating database records:
     - **Credit Issuance**: Persists credit records to `issued_credits` table and logs on order notes.
     - **Cancellation Re-validation**: Re-checks live order status from database; strictly rejects cancellation if order has progressed to `PICKED_UP` or `DELIVERED`.
- **Urgency Independence**: P1 critical incidents increase recommendation urgency but never bypass explicit user confirmation.

---

## 3. Account-Resolution Reliability & Cross-Account Isolation Hardening

During multi-round manual smoke testing and empirical raw-trace evaluation, account resolution and cross-account isolation were systematically analyzed and hardened:

1. **Vulnerability Discovery & Root Cause**:
   - Initial implementations relied on model prompt compliance to infer customer account IDs from company names (e.g. "Axis Labs", "LumenWorks").
   - Repeated trace analysis revealed two failure modes:
     - The model could emit a conflicting `account_id` argument (e.g., supplying `ACCT-002` for Axis Labs queries).
     - When ambiguous or unmentioned entities were queried, the model occasionally hallucinated IDs from parametric memory (e.g., selecting `ORD-1001` when asked about LumenWorks).
2. **Deterministic Pre-Resolution Layer**:
   - Account resolution was shifted entirely out of model discretion into a deterministic pre-resolution step (`resolve_account_from_message` in `backend/agent.py`).
   - Before the LLM turn begins, the raw user query is matched against known account aliases using word-boundary regular expressions and verified directly against SQLite.
   - The verified account (`resolved_account_id`) is injected into the server-side turn context as trusted system metadata.
3. **Structural Server-Side Enforcement**:
   - **Tool-Layer Binding**: `search_documents` automatically overrides model-supplied `account_id` arguments with `resolved_account_id`.
   - **Explicit Cross-Account Mismatch Protection (`ACCOUNT_MISMATCH`)**: When an explicit order ID is supplied alongside a customer context (e.g., "LumenWorks wants to cancel ORD-1001"), `lookup_data` checks `order.account_id == resolved_account_id`. If a mismatch is detected (e.g., `ORD-1001` belongs to `ACCT-001`), `lookup_data` returns a structured `ACCOUNT_MISMATCH` error. The orchestration loop immediately halts, suppressing further document searches or calculations, and instructs the user to provide the correct order ID.
   - **Action & Calculation Ownership Guard (`INVALID_ACCOUNT_OWNERSHIP`)**: `calculate` and `prepare_action` validate target records against `resolved_account_id` in SQLite, preventing any cross-customer state mutation or computation.

---

## 4. Proactive Issue Detection Architecture

The proactive engine (`backend/proactive.py`) provides automated operational intelligence:

1. **Deterministic 24x7 SLA Monitoring**: Evaluates active incidents against the dataset reference time (`2026-08-16T11:00:00+05:30`). Outages (e.g. TKT-501) and security incidents (e.g. TKT-505) are classified as P1 with contract-specific response targets (15m 24x7 for Northstar, 30m 24x7 for Axis Labs).
2. **Grounded Handling of Working-Hour Schedules**:
   - Source policy documents do not specify working hours, timezones, or weekend/holiday calendars for non-24x7 SLAs (e.g. "4 business hours", "2 business days").
   - To avoid hallucinating an ungrounded 9–5 calendar, the engine reports raw elapsed wall-clock minutes and displays SLA status for open business-hour tickets as **`Calendar Undefined`**.
3. **Historical Ticket Isolation**: Historical closed tickets (e.g. TKT-450, TKT-451) are explicitly classified as **`Historical / Closed`** rather than evaluated as active open incidents.
4. **Known Issue Correlation**: Matches incoming ticket descriptions against known bugs (KI-208, KI-211) and suppresses false matches against resolved issues (KI-176).

---

## 5. Disclosed Limitations & Trade-Offs

1. **Northstar Aggregate Credit Cap (₹5,000/month)**:
   - *Limitation*: The supplied dataset lacks a historical ledger of previously issued credits for ACCT-001 across the billing period.
   - *Handling*: The system deterministically computes individual credit eligibility under SOP mechanics and explicitly discloses the monthly aggregate limit in the calculation explanation.
2. **Undefined Business-Hour Calendar**:
   - *Limitation*: Source PDFs specify business-hour targets (e.g., "8 business hours", "2 business days") without defining operational calendar hours, shift schedules, or holiday calendars.
   - *Handling*: The engine calculates raw elapsed time and clearly flags business-hour targets as `Calendar Undefined` to avoid fabricating unverified calendar rules.
3. **Deterministic Metadata Tagging vs. Vector Embeddings**:
   - *Trade-off*: Structured JSON metadata tagging was selected over vector semantic search.
   - *Rationale*: Across a bounded, legally authoritative document set (6 PDFs), metadata tagging eliminates embedding hallucination, guarantees exact section citations, and ensures deterministic compliance.

---

## 6. Evaluation & Verified Metrics

The codebase includes an automated 21-test Golden Evaluation Suite (`backend/eval_suite.py`):

- **Benchmark Scope**: 21 locked scenarios (E01–E21) covering contract overrides, calculation mandates, return-to-origin rules, authorization checks, known issues, and account resolution guards.
- **Production Verified Performance**:
  - **Decision Accuracy: 100.0% (21/21 passed in production)**
  - **Authoritative Citation Accuracy: 100.0% (21/21 verified in production)**

---

## 7. Deployment Configuration

The repository is configured for deployment on Railway via:
- `Procfile`: Web process entrypoint running Uvicorn.
- `railway.json`: Nixpacks build definition.
- `requirements.txt`: Python runtime dependencies.
- FastAPI static mount: Hosts compiled React frontend assets (`frontend/dist`) alongside the REST API.

*Production Deployment: The application is deployed on Railway and the deployed instance has been verified using the full E01–E21 Golden Evaluation Suite.*

---

## 8. AI Coding Tools Attribution
Google Antigravity and Claude/Claude Code were used during development for code exploration, implementation assistance, debugging, refactoring, documentation, evaluation analysis, and deployment troubleshooting. Application behavior, architectural decisions, and evaluation results were manually reviewed and validated.
