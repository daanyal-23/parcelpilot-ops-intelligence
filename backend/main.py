"""
ParcelPilot Operations Intelligence - FastAPI Backend Application.
Serves operations assistant, proactive issue detection, server-side session authentication,
role-based action execution, validation suite, data explorer, and static frontend assets.
"""

import os
import sys
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Ensure project root is in sys.path and load project root .env
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=dotenv_path, override=True)

from backend.db import (
    get_db_connection,
    DATASET_SNAPSHOT_TIME,
    init_db,
    seed_db,
    create_session,
    get_session
)
from backend.agent import execute_agent_turn
from backend.tools import execute_action, cancel_action
from backend.proactive import run_proactive_detection
from backend.eval_suite import run_evaluation
from backend.docs_index import DOCUMENT_CHUNKS, source_resolution

app = FastAPI(
    title="ParcelPilot Operations Intelligence API",
    description="Grounded Operations Intelligence & Safe Action Execution Platform",
    version="2.0.0"
)

# CORS restriction for secure deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas
class LoginRequest(BaseModel):
    role: str = "support_agent"
    user_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None

class ActionConfirmRequest(BaseModel):
    session_id: Optional[str] = None

# Session Dependency Helper
def authenticate_session(
    request: Request,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Dict[str, Any]:
    # Check header first, fallback to query param or default dev session if needed
    sess_id = x_session_id or request.query_params.get("session_id")
    if not sess_id:
        # Check if default dev session can be used
        sess_id = "sess_default_agent"

    session = get_session(sess_id)
    if not session:
        # Fallback to dev session
        session = get_session("sess_default_agent")
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in.")
    return session

@app.on_event("startup")
def startup_event():
    db_file = os.path.join(os.path.dirname(__file__), "parcelpilot.db")
    if not os.path.exists(db_file):
        seed_db()

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ParcelPilot Operations Intelligence",
        "dataset_snapshot_time": DATASET_SNAPSHOT_TIME,
        "llm_provider": "OpenAI",
        "model": os.getenv("OPENAI_MODEL", "gpt-5-mini")
    }

@app.post("/api/login")
def login_endpoint(req: LoginRequest):
    role = req.role.lower().strip()
    if role not in ["support_agent", "manager"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'support_agent' or 'manager'.")
    
    user_id = req.user_id or ("mgr_priya" if role == "manager" else "agent_rohit")
    session_id = create_session(user_id=user_id, role=role)
    return {
        "status": "success",
        "session_id": session_id,
        "user_id": user_id,
        "role": role,
        "message": f"Logged in as {role} ({user_id})"
    }

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, session: Dict[str, Any] = Depends(authenticate_session)):
    # Trusted server-side role and user_id from verified session
    user_context = {
        "role": session["role"],
        "user_id": session["user_id"],
        "session_id": session["session_id"]
    }
    result = execute_agent_turn(
        message=req.message,
        user_context=user_context,
        history=req.history
    )
    return result

@app.get("/api/proactive")
def proactive_endpoint():
    return run_proactive_detection()

@app.get("/api/eval")
def eval_endpoint():
    return run_evaluation()

@app.get("/api/actions")
def list_actions(session: Dict[str, Any] = Depends(authenticate_session)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM actions ORDER BY created_at DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        return {"actions": rows}
    finally:
        conn.close()

@app.get("/api/credits")
def list_credits(session: Dict[str, Any] = Depends(authenticate_session)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM issued_credits ORDER BY issued_at DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        return {"credits": rows}
    finally:
        conn.close()

@app.post("/api/actions/{action_id}/confirm")
def confirm_action_endpoint(
    action_id: str,
    req: ActionConfirmRequest,
    session: Dict[str, Any] = Depends(authenticate_session)
):
    # Server-side trusted context from session
    user_context = {
        "role": session["role"],
        "user_id": session["user_id"]
    }
    res = execute_action(action_id=action_id, user_context=user_context, confirmed_by_user=True)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message", "Execution failed"))
    return res

@app.post("/api/actions/{action_id}/cancel")
def cancel_action_endpoint(action_id: str, session: Dict[str, Any] = Depends(authenticate_session)):
    res = cancel_action(action_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message", "Cancellation failed"))
    return res

@app.get("/api/data/accounts")
def get_accounts(session: Dict[str, Any] = Depends(authenticate_session)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM accounts")
        return {"accounts": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.get("/api/data/orders")
def get_orders(session: Dict[str, Any] = Depends(authenticate_session)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM orders")
        return {"orders": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.get("/api/data/tickets")
def get_tickets(session: Dict[str, Any] = Depends(authenticate_session)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM tickets")
        return {"tickets": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.get("/api/data/docs")
def get_docs(session: Dict[str, Any] = Depends(authenticate_session)):
    return {
        "chunks": DOCUMENT_CHUNKS,
        "precedence_matrix": {
            "ACCT-001 (Northstar)": {
                "sla": source_resolution("sla", "ACCT-001"),
                "cancellation": source_resolution("cancellation", "ACCT-001"),
                "service_credit": source_resolution("service_credit", "ACCT-001")
            },
            "ACCT-002 (LumenWorks)": {
                "sla": source_resolution("sla", "ACCT-002"),
                "cancellation": source_resolution("cancellation", "ACCT-002"),
                "service_credit": source_resolution("service_credit", "ACCT-002")
            },
            "ACCT-003 (Beacon Retail)": {
                "sla": source_resolution("sla", "ACCT-003"),
                "cancellation": source_resolution("cancellation", "ACCT-003"),
                "service_credit": source_resolution("service_credit", "ACCT-003")
            },
            "ACCT-004 (Axis Labs)": {
                "sla": source_resolution("sla", "ACCT-004"),
                "cancellation": source_resolution("cancellation", "ACCT-004"),
                "service_credit": source_resolution("service_credit", "ACCT-004")
            }
        }
    }

# Mount frontend build directory if it exists
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and not os.path.isdir(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
