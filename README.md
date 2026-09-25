# ParcelPilot Operations Intelligence

> AI-powered internal operations platform for grounded incident investigation, contract-aware support decisions, proactive SLA monitoring, and safe operational actions.

![Validation Passing](https://img.shields.io/badge/Validation%20Scenarios-21%2F21%20Passed%20(100%25)-22c55e?style=for-the-badge)
![Citation Accuracy](https://img.shields.io/badge/Citation%20Verification-21%2F21%20Verified%20(100%25)-06b6d4?style=for-the-badge)
![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20OpenAI-6366f1?style=for-the-badge)

**Hosted Application:** https://web-production-e9158.up.railway.app/

---

## Overview

**ParcelPilot Operations Intelligence** is a personal full-stack AI operations platform built around a simulated logistics environment.

In complex logistics operations, support decisions carry direct financial and contractual consequences. The platform combines:

- An **LLM-powered support assistant** for natural-language inquiry and tool orchestration
- A **deterministic business rules engine** for SLA timers, cancellation fees, and service credits
- **Contract-aware policy retrieval** enforcing signed agreement overrides over standard SOPs
- **Account and ownership isolation** preventing cross-customer data leakage
- **Role-based authorization** enforcing managerial approval thresholds
- **Human-confirmed operational actions** through a two-phase prepare/confirm lifecycle
- **Proactive incident and SLA monitoring** surfacing high-severity outages, breach risks, and platform bug correlations

### Core Architectural Principle

> **"The model handles reasoning and orchestration; business truth remains deterministic and verifiable."**

The platform deliberately avoids delegating mathematical computations, policy precedence decisions, or database mutations to probabilistic language model outputs.

---

## Why I Built This

I built this project to explore how AI assistants can operate reliably in operational domains where hallucinated or unverified responses lead to incorrect business actions.

In logistics and freight operations, a support agent must navigate customer-specific contracts, shipment milestones, carrier fault attributions, and spending authorization limits before answering questions or mutating records. General-purpose conversational agents often fail in this context: they hallucinate refund rules, calculate timestamps erroneously, confuse account boundaries, or trigger unauthorized actions.

This project investigates an alternative pattern: **keeping business truth, mathematical calculations, role authorization, account boundaries, and state mutations under deterministic backend control**, while using the LLM for what it does best—interpreting messy natural-language requests, selecting appropriate tools, and synthesizing clear explanations for human operators.

---

## Key Capabilities

1. **AI Support Assistant**:
   - Interactive operations assistant powered by OpenAI (`gpt-5-mini` with `gpt-4o-mini` fallback compatibility) via multi-turn function calling.
   - Transparent step activity badges displaying the exact sequence of tools executed (`Document Search`, `Data Lookup`, `Calculation`, `Action`).
   - Grounded citations citing the exact governing document and section (e.g., `05_Northstar_Logistics_Enterprise_Agreement.pdf, §2`).

2. **Contract-Aware Policy Resolution**:
   - Structured metadata retrieval hierarchy where signed customer agreements automatically supersede general support policies and standard operating procedures.
   - Explicit exclusion of deprecated policy versions unless historical context is explicitly requested.

3. **Deterministic SLA, Fee & Credit Calculations**:
   - Pure Python calculations for cancellation fees, pickup delay credits, and SLA response targets.
   - Milestone-aware evaluation (e.g., distinguishing pre-pickup `BOOKED` shipments from in-transit `PICKED_UP` shipments requiring Return-to-Origin handling).

4. **Account & Ownership Isolation**:
   - Customer account identities are deterministically pre-resolved from user messages before the LLM turn begins.
   - Cross-account queries or conflicting entity references are intercepted by server-side guards and rejected with `ACCOUNT_MISMATCH`.

5. **Role-Based Authorization**:
   - Authenticated server-side user sessions (`support_agent` vs. `manager`).
   - Managerial thresholds enforced in code: individual service credits exceeding ₹1,000 strictly require manager approval, rejecting unauthorized attempts with `INSUFFICIENT_AUTHORITY`.

6. **Two-Phase Action Confirmation**:
   - Any state-altering action (`cancel_order`, `issue_credit`, `escalate_ticket`) is staged into a `pending_confirmation` state via `prepare_action`.
   - Operators review action details on an interactive card before explicit confirmation triggers `execute_action`.
   - At confirmation time, live order milestones are re-verified from the database to prevent executing stale actions.

7. **Proactive Issue Detection**:
   - Automated operational scanning pipeline surfacing P1 critical outages and security incidents.
   - Deterministic 24x7 SLA countdown tracking against an operational snapshot timestamp.
   - Transparent `Calendar Undefined` classification for business-hour SLAs where working calendars are not defined in source contracts.
   - Automated correlation with active platform bugs (e.g., carrier webhook delays, bulk upload row limits) and suppression of false matches on resolved issues.

8. **Operations Data & Policy Explorer**:
   - Interactive database browser for simulated `accounts`, `orders`, `tickets`, and `issued_credits`.
   - Visual Precedence Matrix detailing custom contract overrides vs. general SOP terms across all accounts.

---

## Architecture

For a comprehensive breakdown of the system architecture, component interactions, and data models, see [ARCHITECTURE.md](ARCHITECTURE.md).

For an overview of product workflows and engineering trade-offs, see [PRODUCT_OVERVIEW.md](PRODUCT_OVERVIEW.md).

```
User Request
   │
   ▼
React Frontend (Vite + Tailwind CSS)
   │
   ▼ (REST API + Server-Side Session)
FastAPI Backend
   │
   ├─► Deterministic Account Pre-Resolution
   │
   ▼
Agent Orchestration Loop (OpenAI Function Calling)
   │
   ├─► lookup_data ──────────► SQLite Database (Accounts, Orders, Tickets)
   ├─► search_documents ─────► Structured Metadata Document Index
   ├─► calculate ────────────► Deterministic Rules Engine (SLAs, Fees, Credits)
   └─► prepare_action ───────► Authorization & Ownership Guards
                                      │
                                      ▼
                        Two-Phase Confirmation Card
                                      │
                                      ▼
                               execute_action (Re-Validation + DB Mutation)
```

---

## Validation

The repository includes a deterministic end-to-end validation suite containing 21 scenarios covering contract overrides, operational calculations, authorization boundaries, account isolation, historical information, known-issue correlation, and action safety.

### Results
- **Decision Correctness:** **100% (21/21 passed)**
- **Authoritative Citation Verification:** **100% (21/21 verified)**

These scenarios serve as regression tests to ensure that prompt updates or code changes do not violate business rules, cross account boundaries, or produce ungrounded policy citations.

### Running Validation

Run the validation suite locally using:

```bash
python backend/eval_suite.py
```

This executes all 21 operational scenarios against the live agent loop, verifying tool execution sequences, calculation outputs, and source citations.

---

## Quickstart & Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend assets)
- OpenAI API Key (`OPENAI_API_KEY`)

### Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/daanyal-23/parcelpilot-ops-intelligence.git
   cd parcelpilot-ops-intelligence
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and configure your API key:
   ```bash
   cp .env.example .env
   # Set OPENAI_API_KEY and OPENAI_MODEL=gpt-5-mini in .env
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Seed the SQLite Database**:
   ```bash
   python -c "from backend.db import seed_db; seed_db()"
   ```

5. **Build the Frontend**:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

6. **Start the FastAPI Application**:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
   Open your browser at [http://localhost:8000](http://localhost:8000).

---

## Deployment

The application is deployed on Railway as a unified full-stack service:
- **Web Process (`Procfile`)**: Starts Uvicorn serving the FastAPI backend (`uvicorn backend.main:app --host 0.0.0.0 --port $PORT`).
- **Build Configuration (`railway.json` / `nixpacks.toml`)**: Builds Python and Node environments and runs the application.
- **Static Hosting**: FastAPI statically serves the compiled React assets from `frontend/dist`.

---

## Repository Structure

```
parcelpilot-ops-intelligence/
├── backend/
│   ├── db.py               # SQLite schema, session management, Excel data seeding
│   ├── docs_index.py       # Metadata indexing & policy precedence resolution
│   ├── rules_engine.py     # Deterministic severity, SLA, fee, and credit logic
│   ├── tools.py            # Agent tools, role authorization & two-phase action execution
│   ├── agent.py            # OpenAI orchestration loop & deterministic account guards
│   ├── proactive.py        # Proactive incident detection & known-issue correlation
│   ├── eval_suite.py       # Deterministic 21-scenario validation suite
│   └── main.py             # FastAPI REST endpoints & static frontend host
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # React UI (Assistant, Proactive Monitor, Validation Console, Explorer)
│   │   ├── index.css       # Custom styling and design tokens
│   │   └── main.jsx        # Frontend entry point
│   ├── package.json
│   └── vite.config.js
├── data/                   # Simulated logistics dataset (6 policy PDFs + 1 XLSX data workbook)
│   ├── 01_Support_Policy_v3_CURRENT.pdf
│   ├── 02_Support_Policy_v2_DEPRECATED.pdf
│   ├── 03_Cancellation_and_Service_Credit_SOP_v4.pdf
│   ├── 04_Product_Operations_Guide_and_Known_Issues.pdf
│   ├── 05_Northstar_Logistics_Enterprise_Agreement.pdf
│   ├── 06_LumenWorks_Service_Agreement.pdf
│   └── ParcelPilot_Operations_Data.xlsx
├── ARCHITECTURE.md         # Detailed architectural design and component specifications
├── PRODUCT_OVERVIEW.md     # Operational workflows, scope boundaries, and roadmap
├── Procfile                # Railway deployment entrypoint
├── railway.json            # Deployment configuration
├── nixpacks.toml           # Nixpacks build definition
└── requirements.txt        # Backend dependencies
```

---

## Development Workflow

AI-assisted development tools including Google Antigravity and Claude/Claude Code were used for code exploration, implementation assistance, debugging, refactoring, documentation, evaluation analysis, and deployment troubleshooting. Architectural decisions, application behavior, testing, and final validation were manually reviewed.