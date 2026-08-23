import React, { useState, useEffect, useRef } from 'react';
import {
  Shield,
  ShieldAlert,
  Send,
  RefreshCw,
  Search,
  Database,
  Calculator,
  Zap,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Clock,
  UserCheck,
  UserCog,
  Layers,
  ArrowRight,
  TrendingUp,
  HelpCircle,
  Check,
  X,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Info
} from 'lucide-react';

const SNAPSHOT_TIME = "2026-08-16 11:00 IST";

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'proactive' | 'eval' | 'data'
  const [role, setRole] = useState('support_agent'); // 'support_agent' | 'manager'
  const [sessionId, setSessionId] = useState('sess_default_agent');
  
  // Chat state
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hello! I am the **ParcelPilot Support Agent**. I can help you investigate issues, check policy rules & customer contracts, calculate deterministic cancellation fees and service credits, and safely prepare support actions.\n\nHow can I assist you today?",
      tool_trace: [],
      evidence: []
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [expandedTraceId, setExpandedTraceId] = useState(null);
  const [actionNotice, setActionNotice] = useState(null);
  const chatEndRef = useRef(null);

  // Proactive state
  const [proactiveData, setProactiveData] = useState(null);
  const [loadingProactive, setLoadingProactive] = useState(false);

  // Eval state
  const [evalData, setEvalData] = useState(null);
  const [loadingEval, setLoadingEval] = useState(false);

  // Data state
  const [dataTab, setDataTab] = useState('tickets');
  const [accountsData, setAccountsData] = useState([]);
  const [ordersData, setOrdersData] = useState([]);
  const [ticketsData, setTicketsData] = useState([]);
  const [docsData, setDocsData] = useState(null);
  const [loadingData, setLoadingData] = useState(false);

  // Session Login function
  const loginRole = async (targetRole) => {
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: targetRole })
      });
      const data = await res.json();
      if (res.ok && data.session_id) {
        setSessionId(data.session_id);
        setRole(targetRole);
      }
    } catch (err) {
      console.error("Login failed:", err);
    }
  };

  useEffect(() => {
    loginRole(role);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load Proactive Data
  const loadProactive = async () => {
    setLoadingProactive(true);
    try {
      const res = await fetch('/api/proactive', {
        headers: { 'X-Session-ID': sessionId }
      });
      const data = await res.json();
      setProactiveData(data);
    } catch (err) {
      console.error("Failed to load proactive data:", err);
    } finally {
      setLoadingProactive(false);
    }
  };

  // Load Data Explorer
  const loadDataExplorer = async () => {
    setLoadingData(true);
    try {
      const headers = { 'X-Session-ID': sessionId };
      const [accRes, ordRes, tktRes, docRes] = await Promise.all([
        fetch('/api/data/accounts', { headers }),
        fetch('/api/data/orders', { headers }),
        fetch('/api/data/tickets', { headers }),
        fetch('/api/data/docs', { headers })
      ]);
      const [acc, ord, tkt, docs] = await Promise.all([
        accRes.json(),
        ordRes.json(),
        tktRes.json(),
        docRes.json()
      ]);
      setAccountsData(acc.accounts || []);
      setOrdersData(ord.orders || []);
      setTicketsData(tkt.tickets || []);
      setDocsData(docs || null);
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoadingData(false);
    }
  };

  // Run Eval
  const runEvalSuite = async () => {
    setLoadingEval(true);
    try {
      const res = await fetch('/api/eval', {
        headers: { 'X-Session-ID': sessionId }
      });
      const data = await res.json();
      setEvalData(data);
    } catch (err) {
      console.error("Failed to run eval:", err);
    } finally {
      setLoadingEval(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'proactive') loadProactive();
    if (activeTab === 'data') loadDataExplorer();
    if (activeTab === 'eval' && !evalData) runEvalSuite();
  }, [activeTab]);

  // Handle Send Chat
  const handleSendMessage = async (msgText) => {
    const textToSend = msgText || inputMessage;
    if (!textToSend.trim() || isSending) return;

    const userMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: textToSend.trim()
    };

    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    setIsSending(true);

    try {
      const history = messages.slice(1).map(m => ({
        role: m.role,
        content: m.content
      }));

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({
          message: textToSend.trim(),
          session_id: sessionId,
          history: history
        })
      });

      const data = await res.json();

      const assistantMsg = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response || "No response received.",
        tool_trace: data.tool_trace || [],
        evidence: data.evidence || [],
        pending_action: data.pending_action || null
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "⚠️ An error occurred while communicating with the agent server. Please verify the backend is running.",
        tool_trace: [],
        evidence: []
      }]);
    } finally {
      setIsSending(false);
    }
  };

  // Handle Action Confirmation (Phase 2)
  const handleConfirmAction = async (actionId) => {
    try {
      const res = await fetch(`/api/actions/${actionId}/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({ session_id: sessionId })
      });
      const data = await res.json();
      if (!res.ok) {
        setActionNotice({ type: 'error', text: data.detail || "Action execution rejected." });
      } else {
        setActionNotice({ type: 'success', text: data.message || `Action ${actionId} executed successfully!` });
        setMessages(prev => prev.map(m => {
          if (m.pending_action && m.pending_action.action_id === actionId) {
            return {
              ...m,
              pending_action: { ...m.pending_action, state: 'executed' }
            };
          }
          return m;
        }));
      }
    } catch (err) {
      setActionNotice({ type: 'error', text: "Failed to connect to action confirmation endpoint." });
    }
  };

  // Handle Action Cancellation
  const handleCancelAction = async (actionId) => {
    try {
      const res = await fetch(`/api/actions/${actionId}/cancel`, {
        method: 'POST',
        headers: { 'X-Session-ID': sessionId }
      });
      const data = await res.json();
      setActionNotice({ type: 'info', text: `Action ${actionId} cancelled.` });
      setMessages(prev => prev.map(m => {
        if (m.pending_action && m.pending_action.action_id === actionId) {
          return {
            ...m,
            pending_action: { ...m.pending_action, state: 'cancelled' }
          };
        }
        return m;
      }));
    } catch (err) {
      setActionNotice({ type: 'error', text: "Failed to cancel action." });
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#090d16] text-slate-100">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-[#0d1322]/90 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-950/40">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-emerald-400 bg-clip-text text-transparent">
                  ParcelPilot
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
                  Operations AI
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">Grounded Support & Resolution Suite</p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Snapshot Timestamp Badge */}
            <div className="hidden md:flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-slate-800/80 border border-slate-700 text-xs text-slate-300">
              <Clock className="w-3.5 h-3.5 text-emerald-400" />
              <span>Snapshot:</span>
              <span className="font-mono font-medium text-emerald-300">{SNAPSHOT_TIME}</span>
            </div>

            {/* Server-Side Session Role Switcher */}
            <div className="flex items-center bg-slate-900 border border-slate-700/80 rounded-xl p-1 shadow-inner">
              <button
                onClick={() => loginRole('support_agent')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  role === 'support_agent'
                    ? 'bg-emerald-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <UserCheck className="w-3.5 h-3.5" />
                <span>Support Agent</span>
              </button>
              <button
                onClick={() => loginRole('manager')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  role === 'manager'
                    ? 'bg-amber-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <UserCog className="w-3.5 h-3.5" />
                <span>Manager</span>
                <span className="text-[10px] bg-amber-800/60 px-1.5 py-0.2 rounded font-mono"> &gt;₹1k</span>
              </button>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-1 overflow-x-auto border-t border-slate-800/60">
          <button
            onClick={() => setActiveTab('chat')}
            className={`py-3 px-4 text-xs font-medium border-b-2 flex items-center space-x-2 transition-colors whitespace-nowrap ${
              activeTab === 'chat'
                ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>AI Support Assistant</span>
          </button>
          <button
            onClick={() => setActiveTab('proactive')}
            className={`py-3 px-4 text-xs font-medium border-b-2 flex items-center space-x-2 transition-colors whitespace-nowrap ${
              activeTab === 'proactive'
                ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            <span>Proactive Issue Detection</span>
            <span className="bg-emerald-500/20 text-emerald-300 text-[10px] px-1.5 py-0.5 rounded-full font-bold">
              Bonus Track
            </span>
          </button>
          <button
            onClick={() => setActiveTab('eval')}
            className={`py-3 px-4 text-xs font-medium border-b-2 flex items-center space-x-2 transition-colors whitespace-nowrap ${
              activeTab === 'eval'
                ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Golden Evaluation (E01–E21)</span>
            <span className="bg-slate-800 text-slate-300 text-[10px] px-1.5 py-0.5 rounded-full font-bold">
              {evalData?.total_tests ? `${evalData.total_tests} Tests` : '21 Tests'}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('data')}
            className={`py-3 px-4 text-xs font-medium border-b-2 flex items-center space-x-2 transition-colors whitespace-nowrap ${
              activeTab === 'data'
                ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Database className="w-4 h-4" />
            <span>Data & Policy Explorer</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col">
        {/* Action Notice Alert */}
        {actionNotice && (
          <div className={`mb-4 p-3 rounded-xl flex items-center justify-between text-xs font-medium transition-all ${
            actionNotice.type === 'success' ? 'bg-emerald-950/80 border border-emerald-500 text-emerald-300' :
            actionNotice.type === 'error' ? 'bg-rose-950/80 border border-rose-500 text-rose-300' :
            'bg-slate-800 border border-slate-600 text-slate-300'
          }`}>
            <div className="flex items-center space-x-2">
              {actionNotice.type === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
              {actionNotice.type === 'error' && <AlertTriangle className="w-4 h-4 text-rose-400" />}
              <span>{actionNotice.text}</span>
            </div>
            <button onClick={() => setActionNotice(null)} className="text-slate-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* TAB 1: AI SUPPORT ASSISTANT (CHAT) */}
        {activeTab === 'chat' && (
          <div className="flex-1 flex flex-col glass-panel rounded-2xl overflow-hidden border border-slate-800 shadow-2xl">
            {/* Quick Test Prompt Chips */}
            <div className="p-3 bg-slate-900/90 border-b border-slate-800 flex items-center space-x-2 overflow-x-auto text-xs">
              <span className="text-slate-400 font-medium shrink-0 flex items-center space-x-1">
                <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                <span>Quick Inquiries:</span>
              </span>
              {[
                { label: 'E01: Northstar Cancel ORD-1001', query: 'Can Northstar cancel ORD-1001?' },
                { label: 'E02: LumenWorks Cancel ORD-2001', query: 'Can LumenWorks cancel ORD-2001?' },
                { label: 'E03: LumenWorks Credit ORD-2002', query: 'Does ORD-2002 qualify for a credit?' },
                { label: 'E04: TKT-504 SwiftShip Status', query: 'Why is TKT-504 still BOOKED?' },
                { label: 'E07: TKT-505 Security Leak', query: 'What should happen with TKT-505?' },
                { label: 'E08: TKT-501 Outage', query: 'What should happen with TKT-501?' },
                { label: 'E17: Northstar ORD-1002 (Picked Up)', query: 'Can Northstar cancel ORD-1002?' },
                { label: 'E18: Axis Labs P2 SLA', query: "What's Axis Labs' P2 SLA?" },
                { label: 'E19: Beacon Retail P1 SLA', query: "What's Beacon Retail's P1 SLA?" },
                { label: 'E20: LumenWorks P3 SLA', query: "What's LumenWorks' P3 SLA?" },
                { label: 'E21: LumenWorks Ambiguous Cancel', query: 'LumenWorks wants to cancel an order booked exactly 30 minutes ago' },
                { label: 'E12: Unauthorized Credit', query: 'Issue a service credit of INR 1500 for ORD-2002 as Support Agent' }
              ].map((chip, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(chip.query)}
                  className="px-2.5 py-1 rounded-lg bg-slate-800/90 hover:bg-slate-700 border border-slate-700 hover:border-emerald-500/50 text-slate-300 hover:text-emerald-300 transition-all shrink-0 font-mono text-[11px]"
                >
                  {chip.label}
                </button>
              ))}
            </div>

            {/* Messages Container */}
            <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-6">
              {messages.map((msg, index) => (
                <div
                  key={msg.id || index}
                  className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div className={`flex items-start space-x-2 max-w-3xl ${msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                    {/* Avatar */}
                    <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 shadow-md ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-tr from-blue-600 to-indigo-500 text-white'
                        : 'bg-gradient-to-tr from-emerald-600 to-teal-500 text-white'
                    }`}>
                      {msg.role === 'user' ? <UserCheck className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
                    </div>

                    {/* Message Card */}
                    <div className={`rounded-2xl p-4 sm:p-5 text-sm leading-relaxed shadow-lg ${
                      msg.role === 'user'
                        ? 'bg-blue-600/20 border border-blue-500/30 text-blue-50 rounded-tr-none'
                        : 'bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-none'
                    }`}>
                      {/* Formatted Markdown Content */}
                      <div className="prose prose-invert max-w-none text-sm space-y-2">
                        {msg.content.split('\n\n').map((paragraph, pIdx) => {
                          if (paragraph.startsWith('**') || paragraph.startsWith('- ') || paragraph.startsWith('1. ')) {
                            return (
                              <div key={pIdx} className="space-y-1.5">
                                {paragraph.split('\n').map((line, lIdx) => {
                                  const formatted = line
                                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                    .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 bg-slate-800 rounded font-mono text-emerald-300 text-xs">$1</code>');
                                  return (
                                    <div
                                      key={lIdx}
                                      dangerouslySetInnerHTML={{ __html: formatted }}
                                      className={line.startsWith('- ') ? 'pl-3 border-l-2 border-slate-700 text-xs sm:text-sm text-slate-300' : ''}
                                    />
                                  );
                                })}
                              </div>
                            );
                          }
                          return <p key={pIdx} dangerouslySetInnerHTML={{ __html: paragraph.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />;
                        })}
                      </div>

                      {/* Tool Trace Badges */}
                      {msg.tool_trace && msg.tool_trace.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-slate-800/80">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center space-x-1">
                              <Layers className="w-3 h-3 text-emerald-400" />
                              <span>Executed Tools Trace ({msg.tool_trace.length}):</span>
                            </span>
                            <button
                              onClick={() => setExpandedTraceId(expandedTraceId === msg.id ? null : msg.id)}
                              className="text-[11px] text-emerald-400 hover:text-emerald-300 flex items-center space-x-1"
                            >
                              <span>{expandedTraceId === msg.id ? 'Collapse Details' : 'View Inputs & Outputs'}</span>
                              {expandedTraceId === msg.id ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                            </button>
                          </div>

                          {/* Step Badges */}
                          <div className="flex flex-wrap gap-2">
                            {msg.tool_trace.map((t, tIdx) => {
                              const toolName = t.tool;
                              const badgeStyle =
                                toolName === 'search_documents' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' :
                                toolName === 'lookup_data' ? 'bg-blue-500/10 text-blue-400 border-blue-500/30' :
                                toolName === 'calculate' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
                                'bg-amber-500/10 text-amber-400 border-amber-500/30';
                              
                              const icon =
                                toolName === 'search_documents' ? <Search className="w-3 h-3" /> :
                                toolName === 'lookup_data' ? <Database className="w-3 h-3" /> :
                                toolName === 'calculate' ? <Calculator className="w-3 h-3" /> :
                                <Zap className="w-3 h-3" />;

                              return (
                                <span
                                  key={tIdx}
                                  className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-mono border ${badgeStyle}`}
                                >
                                  {icon}
                                  <span>{toolName}</span>
                                </span>
                              );
                            })}
                          </div>

                          {/* Expanded Step Trace JSON View */}
                          {expandedTraceId === msg.id && (
                            <div className="mt-3 p-3 bg-slate-950/90 rounded-xl border border-slate-800 font-mono text-xs space-y-2 overflow-x-auto max-h-64">
                              {msg.tool_trace.map((step, sIdx) => (
                                <div key={sIdx} className="border-b border-slate-800/80 pb-2 last:border-b-0">
                                  <div className="text-emerald-400 font-semibold mb-1">
                                    Step {sIdx + 1}: {step.tool}
                                  </div>
                                  <div className="text-slate-400 text-[11px]">Inputs:</div>
                                  <pre className="text-slate-300 text-[10px] bg-slate-900/80 p-1.5 rounded">{JSON.stringify(step.input, null, 2)}</pre>
                                  <div className="text-slate-400 text-[11px] mt-1">Output:</div>
                                  <pre className="text-emerald-300 text-[10px] bg-slate-900/80 p-1.5 rounded">{JSON.stringify(step.output, null, 2)}</pre>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Evidence Citations Panel */}
                      {msg.evidence && msg.evidence.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-slate-800/60">
                          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center space-x-1">
                            <FileText className="w-3 h-3 text-cyan-400" />
                            <span>Authoritative Citations:</span>
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.evidence.map((ev, evIdx) => (
                              <span
                                key={evIdx}
                                className="px-2 py-0.5 bg-slate-800/80 border border-slate-700 text-slate-300 rounded text-[11px] font-mono flex items-center space-x-1"
                              >
                                <span>{ev.reference || ev.document}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Two-Phase Pending Action Confirmation Card */}
                      {msg.pending_action && (
                        <div className="mt-4 p-4 rounded-xl bg-amber-950/40 border border-amber-500/50 text-amber-200">
                          <div className="flex items-center space-x-2 mb-2">
                            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                            <span className="font-semibold text-xs uppercase tracking-wider text-amber-300">
                              State-Changing Action Prepared (Confirmation Required)
                            </span>
                          </div>
                          <p className="text-xs text-amber-100 mb-3">
                            <strong>{msg.pending_action.summary}</strong>
                            <br />
                            <span className="text-[11px] text-amber-300/80 font-mono">Action ID: {msg.pending_action.action_id} | Target: {msg.pending_action.target_id}</span>
                          </p>

                          {msg.pending_action.state === 'pending_confirmation' ? (
                            <div className="flex items-center space-x-3">
                              <button
                                onClick={() => handleConfirmAction(msg.pending_action.action_id)}
                                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow-lg shadow-emerald-950/40 transition-all"
                              >
                                <Check className="w-3.5 h-3.5" />
                                <span>Explicitly Confirm & Execute</span>
                              </button>
                              <button
                                onClick={() => handleCancelAction(msg.pending_action.action_id)}
                                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all"
                              >
                                <X className="w-3.5 h-3.5" />
                                <span>Cancel Action</span>
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center space-x-2 text-xs font-semibold">
                              {msg.pending_action.state === 'executed' && (
                                <span className="text-emerald-400 flex items-center space-x-1">
                                  <CheckCircle2 className="w-4 h-4" />
                                  <span>Action executed successfully.</span>
                                </span>
                              )}
                              {msg.pending_action.state === 'cancelled' && (
                                <span className="text-slate-400 flex items-center space-x-1">
                                  <XCircle className="w-4 h-4" />
                                  <span>Action cancelled.</span>
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Input Bar */}
            <div className="p-4 bg-slate-900/95 border-t border-slate-800">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="flex items-center space-x-3"
              >
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Ask a policy question, investigate an order/ticket, or request a calculation..."
                  disabled={isSending}
                  className="flex-1 bg-slate-950 border border-slate-700 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none transition-all"
                />
                <button
                  type="submit"
                  disabled={!inputMessage.trim() || isSending}
                  className="px-5 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-xl text-sm font-semibold flex items-center space-x-2 shadow-lg shadow-emerald-950/40 transition-all shrink-0"
                >
                  {isSending ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <span>Send</span>
                      <Send className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* TAB 2: PROACTIVE ISSUE DETECTION DASHBOARD */}
        {activeTab === 'proactive' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
                  <TrendingUp className="w-5 h-5 text-emerald-400" />
                  <span>Proactive Issue Detection Dashboard</span>
                </h2>
                <p className="text-xs text-slate-400">Deterministic pipeline surfacing P1 incidents, SLA risks, and known-issue correlations</p>
              </div>
              <button
                onClick={loadProactive}
                disabled={loadingProactive}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold flex items-center space-x-1.5 border border-slate-700 transition-all"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingProactive ? 'animate-spin' : ''}`} />
                <span>Refresh Pipeline</span>
              </button>
            </div>

            {loadingProactive || !proactiveData ? (
              <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
                <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin" />
                <p className="text-sm">Running deterministic ticket and order scan...</p>
              </div>
            ) : (
              <>
                {/* Metric Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-blue-500">
                    <div className="text-xs font-semibold text-slate-400 uppercase">Total Active Tickets</div>
                    <div className="text-2xl font-bold text-white mt-1">{proactiveData.total_tickets}</div>
                    <div className="text-[11px] text-slate-400 mt-1 font-mono">Dataset Snapshot Time</div>
                  </div>
                  <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-rose-500 glow-red">
                    <div className="text-xs font-semibold text-rose-400 uppercase">P1 Critical Incidents</div>
                    <div className="text-2xl font-bold text-rose-400 mt-1">{proactiveData.p1_critical_count}</div>
                    <div className="text-[11px] text-rose-300/80 mt-1">Outage & Security Leaks</div>
                  </div>
                  <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-amber-500 glow-amber">
                    <div className="text-xs font-semibold text-amber-400 uppercase">SLA Breached / At Risk</div>
                    <div className="text-2xl font-bold text-amber-400 mt-1">{proactiveData.sla_breached_count}</div>
                    <div className="text-[11px] text-amber-300/80 mt-1">Target exceeded at snapshot</div>
                  </div>
                  <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-emerald-500">
                    <div className="text-xs font-semibold text-emerald-400 uppercase">Correlated Known Issues</div>
                    <div className="text-2xl font-bold text-emerald-400 mt-1">{proactiveData.known_issue_correlations.length}</div>
                    <div className="text-[11px] text-emerald-300/80 mt-1">KI-208 & KI-211 Matches</div>
                  </div>
                </div>

                {/* Cross Customer Pattern Detection Alerts */}
                {proactiveData.cross_customer_patterns && proactiveData.cross_customer_patterns.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                      <Layers className="w-4 h-4 text-emerald-400" />
                      <span>Cross-Customer Pattern Detection ({proactiveData.cross_customer_patterns.length})</span>
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {proactiveData.cross_customer_patterns.map((pat, idx) => (
                        <div key={idx} className="glass-panel p-4 rounded-xl border border-slate-700/80 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-sm text-slate-100">{pat.title}</span>
                            <span className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                              pat.severity === 'Critical' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                              pat.severity === 'Medium' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                              'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                            }`}>
                              {pat.severity}
                            </span>
                          </div>
                          <p className="text-xs text-slate-300">{pat.description}</p>
                          <div className="text-[11px] text-emerald-400 font-mono">
                            Recommended: {pat.recommended_action}
                          </div>
                          <div className="text-[10px] text-slate-400">
                            Affected Accounts: {pat.affected_accounts.join(', ')} | Tickets: {pat.affected_tickets.join(', ')}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Critical P1 Incidents Panel */}
                <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
                  <h3 className="text-sm font-bold text-rose-400 uppercase tracking-wider flex items-center space-x-1.5">
                    <ShieldAlert className="w-4 h-4 text-rose-400" />
                    <span>Critical Incidents Requiring Immediate Escalation (P1)</span>
                  </h3>
                  <div className="space-y-3">
                    {proactiveData.p1_tickets.map((tkt, idx) => (
                      <div key={idx} className="p-4 rounded-xl bg-slate-900/90 border border-rose-500/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className="px-2 py-0.5 bg-rose-500/20 text-rose-400 rounded font-mono text-xs font-bold border border-rose-500/30">
                              {tkt.ticket_id}
                            </span>
                            <span className="font-semibold text-sm text-slate-100">{tkt.subject}</span>
                            <span className="text-xs text-slate-400">({tkt.account_name})</span>
                          </div>
                          <p className="text-xs text-slate-300">{tkt.description}</p>
                          <div className="text-xs text-amber-300 font-mono">
                            Governing SLA: {tkt.sla_target} | Elapsed: {tkt.elapsed_minutes} mins (SLA BREACHED)
                          </div>
                        </div>
                        <button
                          onClick={() => {
                            setActiveTab('chat');
                            handleSendMessage(`What should happen with ${tkt.ticket_id}?`);
                          }}
                          className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shrink-0 flex items-center space-x-1 shadow-lg shadow-rose-950/40"
                        >
                          <span>Investigate & Prepare</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* All Analyzed Tickets Table */}
                <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
                  <div className="p-4 bg-slate-900 border-b border-slate-800 font-bold text-sm text-slate-200">
                    Comprehensive Ticket SLA & Severity Classification Matrix
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
                        <tr>
                          <th className="p-3">Ticket ID</th>
                          <th className="p-3">Account</th>
                          <th className="p-3">Severity</th>
                          <th className="p-3">Subject</th>
                          <th className="p-3">SLA Target</th>
                          <th className="p-3">Elapsed (mins)</th>
                          <th className="p-3">Status</th>
                          <th className="p-3">Known Issue</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {proactiveData.all_analyzed_tickets.map((tkt, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/40">
                            <td className="p-3 text-emerald-400 font-bold">{tkt.ticket_id}</td>
                            <td className="p-3 text-slate-200">{tkt.account_name}</td>
                            <td className="p-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                tkt.severity === 'P1' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                                tkt.severity === 'P2' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                                'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                              }`}>
                                {tkt.severity}
                              </span>
                            </td>
                            <td className="p-3 font-sans text-slate-200">{tkt.subject}</td>
                            <td className="p-3 text-slate-300">{tkt.sla_target}</td>
                            <td className="p-3 text-slate-300">{tkt.elapsed_minutes}</td>
                            <td className="p-3">
                              {tkt.status === 'closed' ? (
                                <span className="text-slate-500 font-medium">Historical / Closed</span>
                              ) : tkt.is_breached ? (
                                <span className="text-rose-400 font-semibold">BREACHED</span>
                              ) : (tkt.is_24x7 || tkt.sla_target?.toLowerCase().includes('24x7')) ? (
                                <span className="text-emerald-400">Within Target</span>
                              ) : (
                                <span className="text-amber-400/90 font-medium">Calendar Undefined</span>
                              )}
                            </td>
                            <td className="p-3">
                              {tkt.known_issue ? (
                                <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 text-[10px]">
                                  {tkt.known_issue.issue_id}
                                </span>
                              ) : (
                                <span className="text-slate-600">-</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* TAB 3: GOLDEN EVALUATION SUITE (E01–E21) */}
        {activeTab === 'eval' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <span>Golden Evaluation Suite (E01–E{evalData?.total_tests || 21} Benchmark)</span>
                </h2>
                <p className="text-xs text-slate-400">
                  Measures <strong>Decision Accuracy</strong> & <strong>Authoritative Source Citations</strong> across all locked test scenarios
                </p>
              </div>
              <button
                onClick={runEvalSuite}
                disabled={loadingEval}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5 shadow-lg shadow-emerald-950/40 transition-all"
              >
                <RefreshCw className={`w-4 h-4 ${loadingEval ? 'animate-spin' : ''}`} />
                <span>Re-run Evaluation</span>
              </button>
            </div>

            {loadingEval || !evalData ? (
              <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
                <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin" />
                <p className="text-sm">Running all {evalData?.total_tests || 21} Golden Test Cases...</p>
              </div>
            ) : (
              <>
                {/* Score Meters */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-emerald-500 glow-emerald">
                    <div className="text-xs font-semibold text-emerald-400 uppercase">Decision Accuracy</div>
                    <div className="text-3xl font-extrabold text-emerald-400 mt-1 font-mono">
                      {evalData.decision_accuracy_pct}%
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      {evalData.passed_tests} of {evalData.total_tests} tests verified
                    </div>
                  </div>
                  <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-cyan-500">
                    <div className="text-xs font-semibold text-cyan-400 uppercase">Citation Accuracy</div>
                    <div className="text-3xl font-extrabold text-cyan-400 mt-1 font-mono">
                      {evalData.citation_accuracy_pct}%
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Authoritative document lines cited
                    </div>
                  </div>
                  <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-blue-500">
                    <div className="text-xs font-semibold text-blue-400 uppercase">Evaluation Coverage</div>
                    <div className="text-3xl font-extrabold text-white mt-1 font-mono">
                      {evalData.passed_tests} / {evalData.total_tests}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      SLAs, Fees, Webhooks, P1s, Deprecations, Roles
                    </div>
                  </div>
                </div>

                {/* Test Results Table */}
                <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
                  <div className="p-4 bg-slate-900 border-b border-slate-800 font-bold text-sm text-slate-200">
                    Detailed Test Results (E01–E{evalData.total_tests})
                  </div>
                  <div className="divide-y divide-slate-800/60">
                    {evalData.test_results.map((test, idx) => (
                      <div key={idx} className="p-4 hover:bg-slate-800/30 transition-colors space-y-2">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center space-x-2.5">
                            <span className="px-2 py-0.5 bg-slate-800 text-emerald-300 rounded font-mono font-bold text-xs border border-slate-700">
                              {test.id}
                            </span>
                            <span className="font-semibold text-sm text-slate-100">{test.query}</span>
                          </div>
                          <div className="flex items-center space-x-2 shrink-0">
                            {test.passed ? (
                              <span className="px-2.5 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-bold flex items-center space-x-1">
                                <Check className="w-3.5 h-3.5" />
                                <span>PASS</span>
                              </span>
                            ) : (
                              <span className="px-2.5 py-1 bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-lg text-xs font-bold flex items-center space-x-1">
                                <X className="w-3.5 h-3.5" />
                                <span>FAIL</span>
                              </span>
                            )}
                            <button
                              onClick={() => {
                                setActiveTab('chat');
                                handleSendMessage(test.query);
                              }}
                              className="text-xs px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-all"
                            >
                              Run in Chat
                            </button>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
                            <div className="text-slate-400 font-medium">Expected Decision:</div>
                            <div className="text-slate-200 mt-0.5">{test.expected_decision}</div>
                          </div>
                          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80 font-mono">
                            <div className="text-slate-400 font-medium">Authoritative Source:</div>
                            <div className="text-cyan-300 mt-0.5">{test.authoritative_source}</div>
                          </div>
                        </div>

                        <div className="text-xs text-slate-300 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/50">
                          <div className="text-slate-400 font-semibold mb-1">Agent Response Summary:</div>
                          <p className="line-clamp-2">{test.agent_response}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* TAB 4: DATA & POLICY EXPLORER */}
        {activeTab === 'data' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
                  <Database className="w-5 h-5 text-emerald-400" />
                  <span>Data & Policy Explorer</span>
                </h2>
                <p className="text-xs text-slate-400">Structured tables seeded from xlsx & metadata-tagged document index</p>
              </div>
              <button
                onClick={loadDataExplorer}
                disabled={loadingData}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold flex items-center space-x-1.5 border border-slate-700 transition-all"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingData ? 'animate-spin' : ''}`} />
                <span>Reload Data</span>
              </button>
            </div>

            {/* Sub-tabs */}
            <div className="flex space-x-2 border-b border-slate-800 pb-2">
              {[
                { id: 'tickets', label: 'Tickets Table' },
                { id: 'orders', label: 'Orders Table' },
                { id: 'accounts', label: 'Accounts Table' },
                { id: 'precedence', label: 'Precedence Matrix' }
              ].map(st => (
                <button
                  key={st.id}
                  onClick={() => setDataTab(st.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    dataTab === st.id
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {st.label}
                </button>
              ))}
            </div>

            {loadingData ? (
              <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
                <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin" />
                <p className="text-sm">Loading database tables...</p>
              </div>
            ) : (
              <>
                {/* Tickets Table */}
                {dataTab === 'tickets' && (
                  <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
                        <tr>
                          <th className="p-3">Ticket ID</th>
                          <th className="p-3">Account ID</th>
                          <th className="p-3">Created At</th>
                          <th className="p-3">Status</th>
                          <th className="p-3">Subject</th>
                          <th className="p-3">Historical Resolution (Non-Authoritative)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 font-mono">
                        {ticketsData.map((tkt, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/40">
                            <td className="p-3 text-emerald-400 font-bold">{tkt.ticket_id}</td>
                            <td className="p-3 text-slate-300">{tkt.account_id}</td>
                            <td className="p-3 text-slate-400">{tkt.created_at}</td>
                            <td className="p-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] ${
                                tkt.status === 'open' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'
                              }`}>
                                {tkt.status}
                              </span>
                            </td>
                            <td className="p-3 font-sans text-slate-200">{tkt.subject}</td>
                            <td className="p-3 font-sans text-xs text-amber-300/80">
                              {tkt.historical_resolution || <span className="text-slate-600">-</span>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Orders Table */}
                {dataTab === 'orders' && (
                  <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
                        <tr>
                          <th className="p-3">Order ID</th>
                          <th className="p-3">Account ID</th>
                          <th className="p-3">Carrier</th>
                          <th className="p-3">Status</th>
                          <th className="p-3">Booked At</th>
                          <th className="p-3">Pickup Actual</th>
                          <th className="p-3">Fee (INR)</th>
                          <th className="p-3">Carrier Fault</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 font-mono">
                        {ordersData.map((ord, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/40">
                            <td className="p-3 text-emerald-400 font-bold">{ord.order_id}</td>
                            <td className="p-3 text-slate-300">{ord.account_id}</td>
                            <td className="p-3 text-slate-200">{ord.carrier}</td>
                            <td className="p-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                ord.status === 'BOOKED' ? 'bg-blue-500/20 text-blue-300' :
                                ord.status === 'PICKED_UP' ? 'bg-amber-500/20 text-amber-300' :
                                'bg-emerald-500/20 text-emerald-300'
                              }`}>
                                {ord.status}
                              </span>
                            </td>
                            <td className="p-3 text-slate-400">{ord.booked_at}</td>
                            <td className="p-3 text-slate-400">{ord.pickup_actual_at || 'None'}</td>
                            <td className="p-3 text-emerald-300">₹{ord.shipment_fee_inr}</td>
                            <td className="p-3 text-slate-300">{ord.carrier_fault ? 'True' : 'False'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Accounts Table */}
                {dataTab === 'accounts' && (
                  <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
                        <tr>
                          <th className="p-3">Account ID</th>
                          <th className="p-3">Account Name</th>
                          <th className="p-3">Plan</th>
                          <th className="p-3">CSM</th>
                          <th className="p-3">Contract File</th>
                          <th className="p-3">Premium Support</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 font-mono">
                        {accountsData.map((acc, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/40">
                            <td className="p-3 text-emerald-400 font-bold">{acc.account_id}</td>
                            <td className="p-3 font-sans text-slate-200 font-medium">{acc.account_name}</td>
                            <td className="p-3 text-cyan-300">{acc.plan}</td>
                            <td className="p-3 font-sans text-slate-300">{acc.csm}</td>
                            <td className="p-3 text-slate-400">{acc.contract_file || 'None (General Policies)'}</td>
                            <td className="p-3 text-slate-400">{acc.premium_support ? 'True (Info only)' : 'False'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Precedence Matrix */}
                {dataTab === 'precedence' && docsData && docsData.precedence_matrix && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(docsData.precedence_matrix).map(([accKey, rules], idx) => (
                      <div key={idx} className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3">
                        <div className="font-bold text-sm text-emerald-400 border-b border-slate-800 pb-2">
                          {accKey}
                        </div>
                        <div className="space-y-2 text-xs">
                          <div>
                            <span className="font-semibold text-slate-400">SLA Precedence:</span>
                            <p className="text-slate-200 mt-0.5">{rules.sla.explanation}</p>
                            <span className="text-[11px] font-mono text-cyan-300">{rules.sla.source_reference}</span>
                          </div>
                          <div>
                            <span className="font-semibold text-slate-400">Cancellation Precedence:</span>
                            <p className="text-slate-200 mt-0.5">{rules.cancellation.explanation}</p>
                            <span className="text-[11px] font-mono text-cyan-300">{rules.cancellation.source_reference}</span>
                          </div>
                          <div>
                            <span className="font-semibold text-slate-400">Service Credit Precedence:</span>
                            <p className="text-slate-200 mt-0.5">{rules.service_credit.explanation}</p>
                            <span className="text-[11px] font-mono text-cyan-300">{rules.service_credit.source_reference}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
