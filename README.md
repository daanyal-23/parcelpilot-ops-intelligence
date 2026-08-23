# ParcelPilot Internal Support Agent & Operations Suite

> Grounded, locked-design internal AI support assistant and proactive issue detection platform for authorized ParcelPilot operations staff. Powered by OpenAI function-calling architecture for the CalQuity Technical Assessment.

![ParcelPilot Suite](https://img.shields.io/badge/Decision%20Accuracy-100%25%20(21%2F21%20 Production)-22c55e?style=for-the-badge)
![Authoritative Citations](https://img.shields.io/badge/Authoritative%20Citations-100%25%20(21%2F21 Production)-06b6d4?style=for-the-badge)
![FastAPI + React](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20OpenAI-6366f1?style=for-the-badge)

**Hosted Application:** https://web-production-e9158.up.railway.app/
---

## 🌟 Key Features

1. **AI Support Assistant (Chat)**:
   - Powered by **OpenAI (`gpt-5-mini`)** (with `gpt-4o-mini` compatibility fallback) via native multi-turn function calling.
   - **Step Activity Badges**: Renders ordered tool execution badges (`🔍 Document Search`, `📊 Data Lookup`, `🧮 Calculation`, `⚡ Action`).
   - **Authoritative Source Citations**: Every policy response explicitly cites the governing document section (e.g. `05_Northstar_Logistics_Enterprise_Agreement.pdf, §2`).
   - **Two-Phase Action Protocol**: State-changing actions (`cancel_order`, `issue_credit`, `escalate_ticket`) prepare a pending confirmation card requiring explicit human confirmation before mutating records.

2. **Proactive Issue Detection (Bonus Feature Track)**:
   - Deterministic scanning pipeline surfacing P1 Critical incidents (outages, security key exposures).
   - **Deterministic 24x7 SLA Monitoring**: Evaluates open 24x7 SLA targets against dataset snapshot timestamp `2026-08-16T11:00:00+05:30` (Asia/Kolkata).
   - **Grounded Status Classification**: Displays closed tickets as `Historical / Closed` and open business-hour tickets as `Calendar Undefined` (reflecting that authoritative source documents do not define working-hour schedules).
   - **Known Issue Correlation**: Accurately correlates active tickets with known platform bugs (KI-208 bulk upload limit, KI-211 SwiftShip 20-min webhook lag) while strictly guarding against false matches on resolved issues (KI-176).
   - **Cross-Customer Pattern Detection**: Systemic failure clustering across customer accounts.

3. **Golden Evaluation Suite (E01–E21)**:
   - Built-in interactive test runner validating all 21 locked benchmark cases using the live agent loop.
   - **Production Verified Performance**: **100.0% Decision Accuracy (21/21 passed in production)** and **100.0% Authoritative Citation Accuracy(21/21 verified in production)**.

4. **Data & Policy Explorer**:
   - Live browser for SQLite `accounts`, `orders`, `tickets`, and `issued_credits` tables.
   - Interactive Precedence Matrix visualizer detailing custom contract overrides vs general SOP rules.

---

## 📐 Architecture & Non-Negotiable Principles

- **The LLM Does Not Own Business Truth**: The model orchestrates tools and explains results; all calculations (SLAs, cancellation fees, service credits) are executed in deterministic Python code (`backend/rules_engine.py`).
- **Deterministic Account Resolution & Ownership Guards**: Customer account identity is resolved deterministically from raw user messages before the LLM call. Conflicting tool arguments or cross-account order accesses are strictly intercepted and rejected via server-side guards (`INVALID_ACCOUNT_OWNERSHIP` / `ACCOUNT_MISMATCH`).
- **Server-Side Session Authentication**: Users log in via `POST /api/login`, establishing trusted server-side sessions. Client cannot self-declare roles. Individual credits > ₹1,000 strictly require Manager approval per SOP v4 §3.
- **Metadata-Driven Precedence**: Retrieval operates on structured metadata hierarchy (`Signed Agreement > Policy v3 / SOP v4 > Operations Guide`).
- **Historical Resolutions are Non-Authoritative**: Stored in `tickets` with `authoritative: false`, excluded from document search index, and treated as investigational context only.
- **Two-Phase Action Protocol with Defense-in-Depth**:
  - *Credit Issuance*: Executed credits are permanently recorded in `issued_credits` table.
  - *Cancellation Re-validation*: Live order status is re-checked from SQLite upon execution; cancellations on `PICKED_UP` orders are strictly rejected and Return-to-Origin is mandated.

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend build)
- OpenAI API Key (`OPENAI_API_KEY`)

### Installation & Run

1. **Clone the repository**:
   ```bash
   git clone https://github.com/daanyal-23/CalQuity.git
   cd CalQuity
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

5. **Build the React Frontend**:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

6. **Start the FastAPI Server**:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
   Open your browser at [http://localhost:8000](http://localhost:8000).

---

## 🧪 Running the Evaluation Suite

Run the automated E01–E21 test suite locally from the command line:

```bash
python backend/eval_suite.py
```

All 21 test cases evaluate the live agent loop and verify decision outcomes and authoritative citation coverage.

---

## ☁️ Deployment Configuration

The application is deployed on Railway:
- `Procfile`: Web process execution command (`uvicorn backend.main:app --host 0.0.0.0 --port $PORT`).
- `railway.json`: Nixpacks deployment build configuration.
- `requirements.txt`: Python package dependencies.
- FastAPI static mount: Serves pre-built React frontend assets from `frontend/dist`.

*(Note: The application is deployed on Railway and has been verified against the full E01–E21 Golden Evaluation Suite in production.)*

---

## 📁 Repository Structure

```
CalQuity/
├── backend/
│   ├── db.py               # SQLite schema, session storage, timezone seeding
│   ├── docs_index.py       # Metadata chunking & precedence resolution engine
│   ├── rules_engine.py     # Deterministic severity, SLA, fee, credit calculations
│   ├── tools.py            # Agent-facing tools & role authorization layer
│   ├── agent.py            # OpenAI function-calling orchestration loop & account guards
│   ├── proactive.py        # Proactive issue detection & pattern analysis
│   ├── eval_suite.py       # Automated E01-E21 evaluation suite
│   └── main.py             # FastAPI REST endpoints & static frontend host
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Full React UI with chat, proactive dash, eval runner (E01-E21)
│   │   ├── index.css       # Tailwind & custom dark glassmorphic styles
│   │   └── main.jsx        # Entry point
│   ├── package.json
│   └── vite.config.js
├── data/                   # 6 PDFs + 1 XLSX source data pack
├── ARCHITECTURE_NOTE.md    # In-depth architectural & technical decisions
├── PRODUCT_NOTE.md         # Product strategy, roadmap, and tradeoffs
├── Procfile                # Railway deployment process command
├── railway.json            # Railway deployment configuration
└── requirements.txt        # Backend dependencies
```

---

## 🛠️ AI Tools Used

Google Antigravity and Claude/Claude Code were used during development for code exploration, implementation assistance, debugging, refactoring, documentation, evaluation analysis, and deployment troubleshooting. Application behavior, architectural decisions, and evaluation results were manually reviewed and validated.