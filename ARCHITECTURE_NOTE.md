# Architecture Note — ParcelPilot Internal Support Agent

## 1. System Overview

The **ParcelPilot Internal Support Agent** is an enterprise operations AI system designed for authorized ParcelPilot support staff and operations managers. It investigates customer incidents, answers operational and contractual questions, deterministically calculates SLAs, fees, and credits, flags high-urgency tickets, and executes approved support actions through a strict two-phase confirmation protocol.

---

## 2. Core Architectural Principles & Decisions

### Principle 1: The LLM Does Not Own Business Truth
- **Decision**: The LLM functions strictly as an orchestrator and explainer. It never calculates elapsed time, assesses SLA breach status, determines cancellation fee amounts, or computes credit eligibility in memory.
- **Implementation**: Every calculation is executed in Python (`backend/rules_engine.py`) using deterministic code and verified against source document line items.
- **Provider & Model**: Powered by **OpenAI (`gpt-5-mini` / `gpt-4o-mini`)** using the official `openai` Python SDK. The agent loop utilizes native OpenAI function calling with tool schemas (`tools` parameter with `type: "function"`).

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

## 3. Disclosed Limitations & Trade-Offs

1. **Northstar Aggregate Credit Cap (₹5,000/month)**:
   - *Limitation*: The supplied dataset lacks a historical ledger of previously issued credits for ACCT-001.
   - *Handling*: The system evaluates individual credit eligibility under SOP mechanics and explicitly discloses the monthly cap limitation in the calculation output.
2. **Undefined Business-Hour Calendar**:
   - *Limitation*: None of the source documents define a holiday or business-hour calendar (e.g. 9-5 vs weekend exclusions).
   - *Handling*: For business-hour denominated SLAs (e.g. P3 8 business hours), the system reports raw wall-clock elapsed time alongside the target string rather than fabricating an arbitrary calendar.
3. **No Vector Embeddings / External Vector DB**:
   - *Trade-off*: Deterministic JSON metadata filtering with topic/account/scope tags was chosen over vector embeddings.
   - *Rationale*: For small, legally precise data packs (6 PDFs), metadata tagging eliminates embedding hallucination, guarantees 100% citation accuracy, and remains explainable.

---

## 4. Evaluation & Success Metrics

- **Evaluation Suite**: Built directly into the codebase (`backend/eval_suite.py` and UI tab) covering all 17 locked golden scenarios (E01–E17).
- **Reported Metric: Decision Accuracy**: **100.0% (17 / 17 passed)**
- **Reported Metric: Authoritative Citation Accuracy**: **100.0% (17 / 17 verified)**

---

## 5. AI Coding Tools Attribution
- Developed with Google Antigravity IDE pairing agentically to construct data schemas, deterministic calculation engines, OpenAI function-calling agent loop, evaluation harness, and modern React UI.
