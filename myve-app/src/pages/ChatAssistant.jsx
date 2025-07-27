import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Card, CardContent, CardHeader } from '../components/ui/card';
import { Button } from '../components/ui/button';
import GraphViewer from '../components/GraphViewer';
import { Send, Plus, Bot, User, AlertTriangle, ClipboardList, BookUser } from 'lucide-react';

// Helper component for a cleaner, more modern chat message bubble
const ChatMessage = ({ msg }) => {
  const isBot = msg.sender === 'bot';
  // Safe displayText extraction for various response structures
  const displayText =
    typeof msg.text === 'string'
      ? msg.text
      : typeof msg.text === 'object' && msg.text?.text
      ? msg.text.text
      : '[Unsupported response format]';

  return (
    <div className={`flex items-start gap-3 ${isBot ? 'justify-start' : 'justify-end'}`}>
      {isBot && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
          <Bot className="w-5 h-5 text-gray-600" />
        </div>
      )}
      <div className={`max-w-[75%] rounded-lg px-4 py-3 shadow-sm ${isBot ? 'bg-white' : 'bg-blue-500 text-white'}`}>
        <ReactMarkdown
          components={{
            p: ({ node, ...props }) => <p {...props} />,
          }}
        >
          {displayText}
        </ReactMarkdown>
        {/* Metadata display */}
        {msg.metadata && msg.metadata.summary && (
          <div className="mt-2 text-sm text-green-700 bg-green-50 border border-green-200 p-2 rounded">
            <strong>Summary:</strong> {msg.metadata.summary}
          </div>
        )}
        {msg.metadata && msg.metadata.suggestions && Array.isArray(msg.metadata.suggestions) && (
          <div className="mt-2 text-sm text-gray-700 bg-gray-50 border border-gray-200 p-2 rounded">
            <strong>Suggestions:</strong>
            <ul className="list-disc list-inside mt-1">
              {msg.metadata.suggestions.map((item, idx) => (
                <li key={idx}>
                  {item.bank} - {item.rate}% for {item.tenure_months} months
                </li>
              ))}
            </ul>
          </div>
        )}
        {/* Enhanced metadata visibility for agents and intents */}
        {console.debug("Active Agents Received:", msg.metadata?.agents)}
        {msg.metadata?.agents && msg.metadata.agents.length > 0 && (
          <div className="mt-2 text-xs text-purple-700 bg-purple-50 border border-purple-200 p-2 rounded flex flex-wrap gap-2">
            <strong className="w-full">Agents:</strong>
            {msg.metadata.agents.map((agent, idx) => {
              let icon = <Bot className="w-4 h-4" />;
              const normalized = agent.toLowerCase().replace("_agent", "");
              if (normalized === 'planning') icon = <ClipboardList className="w-4 h-4 text-blue-600" />;
              else if (normalized === 'buying') icon = <Send className="w-4 h-4 text-green-600" />;
              else if (normalized === 'repaying') icon = <BookUser className="w-4 h-4 text-indigo-600" />;
              else if (normalized === 'warning' || normalized === 'warn') icon = <AlertTriangle className="w-4 h-4 text-yellow-600" />;

              return (
                <div key={idx} className="flex items-center gap-2 px-2 py-1 bg-purple-100 text-purple-800 rounded-full">
                  {icon}
                  <span>{agent}</span>
                </div>
              );
            })}
          </div>
        )}
        {msg.metadata?.intents && (
          <div className="mt-2 text-xs text-indigo-700 bg-indigo-50 border border-indigo-200 p-2 rounded">
            <strong>Intents:</strong> {msg.metadata.intents.join(', ')}
          </div>
        )}
        <div className={`text-xs mt-2 ${isBot ? 'text-gray-400 text-left' : 'text-blue-200 text-right'}`}>
          {msg.timestamp
            ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : ''}
        </div>
      </div>
      {!isBot && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
          <User className="w-5 h-5 text-white" />
        </div>
      )}
    </div>
  );
};

const ChatAssistant = () => {
  // State hooks remain unchanged
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [suggestionClass, setSuggestionClass] = useState('fade-in');
  const [sessionId, setSessionId] = useState(() => sessionStorage.getItem("active_session_id") || null);
  const [sessions, setSessions] = useState([]);
  const [sessionTitle, setSessionTitle] = useState('');
  const [probingQuestions, setProbingQuestions] = useState([]);
  const [probingAnswers, setProbingAnswers] = useState({});
  const [isProbing, setIsProbing] = useState(false);
  const [actionPlan, setActionPlan] = useState(null);
  const [warnings, setWarnings] = useState([]);

  const messagesEndRef = useRef(null);

  // All logic hooks and functions remain unchanged
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await fetch('/api/ai/sessions');
        if (res.ok) {
          const data = await res.json();
          setSessions(data.sessions || []);
        }
      } catch (e) { console.error("Failed to fetch sessions", e); }
    };
    fetchSessions();
  }, []);

  useEffect(() => {
    const loadSession = async () => {
        if (!sessionId) {
            setMessages([]);
            setSessionTitle('');
            setActionPlan(null);
            setWarnings([]);
            return;
        };
        try {
            const res = await fetch(`/api/ai/history/${sessionId}`);
            if(res.ok) {
                const data = await res.json();
                setMessages(data.messages || []);
                const currentSession = sessions.find((s) => s.session_id === sessionId);
                // The title might not be in the sessions list if it was just created
                setSessionTitle(data.title || currentSession?.title || '');
            }
        } catch(e) { console.error("Failed to load session history", e); }
    };
    loadSession();
  }, [sessionId, sessions]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, isProbing, actionPlan, warnings]);

  const handleNewSession = () => {
    setSessionId(null);
    sessionStorage.removeItem("active_session_id");
    setMessages([]);
    setInput('');
    setActionPlan(null);
    setWarnings([]);
    setProbingQuestions([]);
    setIsProbing(false);
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    setProbingQuestions([]);
    setProbingAnswers({});
    setIsProbing(false);
    setActionPlan(null);
    setWarnings([]);
    setIsLoading(true);
    const timestamp = new Date().toISOString();
    setMessages(prev => [...prev, { sender: 'user', text: input, timestamp }]);
    const userInput = input;
    setInput('');
    // Step 1: Interpret user intent and update UI early
    try {
      const interpretRes = await fetch('/api/ai/interpret', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userInput })
      });
      const interpretData = await interpretRes.json();
      setActionPlan(prev => ({
        ...(prev || {}),
        agents: interpretData.agents || [],
        intents: interpretData.intents || [],
      }));
    } catch (err) {
      console.warn("Interpret call failed", err);
    }
    try {
      const res = await fetch('/api/ai/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: userInput,
          session_id: sessionId,
          probingAnswers: Object.values(probingAnswers)
        })
      });
      const data = await res.json();
      setMessages(prev => [
        ...prev,
        {
          sender: 'bot',
          text: data.response,
          timestamp: new Date().toISOString(),
          metadata: data.metadata || {}
        }
      ]);
      if (data.plan || data.intents || data.agents) {
        setActionPlan(prev => ({
          ...(prev || {}),
          ...(data.plan || {}),
          intents: data.intents,
          agents: data.agents,
        }));
      }
      if (data.graphs) setActionPlan(prev => ({ ...prev, graphs: data.graphs }));
      if (data.graph_points) setActionPlan(prev => ({ ...prev, graph_points: data.graph_points }));
      if (data.warnings) setWarnings(data.warnings);
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id);
        sessionStorage.setItem("active_session_id", data.session_id);
        // Refresh session list to include the new one
        const res = await fetch('/api/ai/sessions');
        const sessionData = await res.json();
        setSessions(sessionData.sessions || []);
      }
      setIsLoading(false);
      setSuggestionClass('fade-out');
      setTimeout(async () => {
        setSuggestions([]);
        const suggestRes = await fetch('/api/ai/suggest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: userInput, response: data.response })
        });
        const suggestionData = await suggestRes.json();
        setSuggestions(suggestionData.suggestions || []);
        setSuggestionClass('fade-in');
      }, 300);
      if (data.probing_questions && data.probing_questions.length > 0) {
        setProbingQuestions(data.probing_questions);
        setIsProbing(true);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { sender: 'bot', text: 'Sorry, there was an error processing your request.', timestamp: new Date().toISOString() }
      ]);
      setIsLoading(false);
    }
  };

  const handleSessionChange = (e) => {
    const newSessionId = e.target.value;
    setSessionId(newSessionId);
    if(newSessionId) {
        sessionStorage.setItem("active_session_id", newSessionId);
    } else {
        handleNewSession();
    }
  };

  const handleProbingInput = (index, value) => {
    setProbingAnswers(prev => ({ ...prev, [index]: value }));
  };

  const submitProbingAnswers = async () => {
    setIsLoading(true);
    setSuggestionClass('fade-out');
    setIsProbing(false);
    try {
      const res = await fetch('/api/ai/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: messages.filter(m => m.sender === 'user').slice(-1)[0]?.text || '',
          session_id: sessionId,
          probingAnswers: Object.values(probingAnswers)
        })
      });
      const data = await res.json();
      setMessages(prev => [
        ...prev,
        {
          sender: 'bot',
          text: data.response,
          timestamp: new Date().toISOString(),
          metadata: data.metadata || {}
        }
      ]);
      if (data.plan || data.intents || data.agents) {
        setActionPlan(prev => ({
          ...(prev || {}),
          ...(data.plan || {}),
          intents: data.intents,
          agents: data.agents,
        }));
      }
      if (data.warnings) setWarnings(data.warnings);
      setTimeout(() => {
        setSuggestions(data.suggestions || []);
        setSuggestionClass('fade-in');
      }, 300);
      setProbingQuestions([]);
      setProbingAnswers({});
      setIsLoading(false);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { sender: 'bot', text: 'Sorry, there was an error submitting your answers.', timestamp: new Date().toISOString() }
      ]);
      setIsLoading(false);
      setSuggestionClass('fade-in');
    }
  };

  const handleRenameSession = async () => {
    if (sessionId && sessionTitle.trim()) {
        await fetch(`/api/ai/session/${sessionId}/rename`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: sessionTitle.trim() }),
        });
        setSessions((prev) =>
            prev.map((s) =>
                s.session_id === sessionId ? { ...s, title: sessionTitle.trim() } : s
            )
        );
    }
  }

  return (
    <div className="flex flex-col md:flex-row h-full min-h-screen">
      {/* --- Left Sidebar: Session Card and Suggestion Card --- */}
      <div className="w-full md:w-1/4 max-h-screen overflow-y-auto p-4 space-y-4 flex flex-col">
        {/* Session Card */}
        <Card className="flex flex-col">
          <CardHeader className="pb-2 border-b">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <BookUser className="w-5 h-5" /> Sessions
              </h2>
              <Button variant="ghost" size="icon" onClick={handleNewSession}>
                <Plus className="w-5 h-5" title="New Chat" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 pt-4">
            <select
              value={sessionId || ""}
              onChange={handleSessionChange}
              className="w-full border-gray-300 rounded-md shadow-sm text-sm p-2"
            >
              <option value="" disabled>Select a chat</option>
              {sessions.map((s) => (
                <option key={s.session_id} value={s.session_id}>
                  {s.title || `Chat from ${new Date(s.created_at).toLocaleDateString()}`}
                </option>
              ))}
            </select>
            {sessionId && (
              <input
                type="text"
                className="w-full border-gray-300 rounded-md shadow-sm text-sm p-2"
                placeholder="Rename this session..."
                value={sessionTitle}
                onChange={(e) => setSessionTitle(e.target.value)}
                onBlur={handleRenameSession}
              />
            )}
          </CardContent>
        </Card>
        {/* Suggestion Card */}
        <Card>
          <CardHeader className="pb-2 border-b">
            <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
              <Bot className="w-5 h-5" /> Suggestions
            </h3>
          </CardHeader>
          <CardContent className="pt-4">
            {suggestions.length > 0 ? (
              <div className={`flex flex-wrap gap-2 transition-all duration-300 ${suggestionClass}`}>
                {suggestions.map((text, i) => (
                  <button
                    key={i}
                    className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm transition-colors duration-200 hover:bg-blue-100 hover:text-blue-700"
                    onClick={() => setInput(text)}
                  >
                    {text}
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-gray-400 text-sm">No suggestions yet.</div>
            )}
          </CardContent>
        </Card>
        {/* Active Agents Card */}
        <Card>
          <CardHeader className="pb-2 border-b">
            <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
              <Bot className="w-5 h-5" /> Active Agents
            </h3>
          </CardHeader>
          <CardContent className="pt-4">
            {actionPlan?.agents && actionPlan.agents.length > 0 ? (
              <div className="flex flex-col gap-2">
                {actionPlan.agents.map((agent, idx) => {
                  let icon = <Bot className="w-4 h-4" />;
                  if (agent.toLowerCase().includes('plan')) icon = <ClipboardList className="w-4 h-4 text-blue-600" />;
                  else if (agent.toLowerCase().includes('buy')) icon = <Send className="w-4 h-4 text-green-600" />;
                  else if (agent.toLowerCase().includes('repay')) icon = <BookUser className="w-4 h-4 text-indigo-600" />;
                  else if (agent.toLowerCase().includes('warn')) icon = <AlertTriangle className="w-4 h-4 text-yellow-600" />;

                  return (
                    <div key={idx} className="flex items-center gap-2 px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm">
                      {icon}
                      <span>{agent}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-gray-400 text-sm">No agents active</div>
            )}
            {actionPlan?.intents && actionPlan.intents.length > 0 && (
              <div className="mt-3">
                <h4 className="text-sm font-medium text-gray-700 mb-1">Detected Intents:</h4>
                <ul className="list-disc list-inside text-sm text-gray-600">
                  {actionPlan.intents.map((intent, idx) => (
                    <li key={idx}>{intent}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      {/* --- Main Chat Panel --- */}
      <div className="flex-1  p-4 md:p-6 space-y-6 min-h-0 max-h-[calc(100vh-160px)]">
        <Card className="flex-1 flex flex-col border-0 md:border shadow-none md:shadow-sm m-0 md:m-4 rounded-none md:rounded-lg max-h-full">
          <CardHeader className="border-b">
            <h3 className="text-lg font-semibold text-gray-900">
              {sessionTitle || "Financial Assistant"}
            </h3>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
            <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-6 space-y-6 min-h-0">
              {messages.map((msg, idx) => (
                <ChatMessage key={idx} msg={msg} />
              ))}

              {isLoading && (
                <div className="flex items-start gap-3 justify-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-gray-600" />
                  </div>
                  <div className="max-w-[75%] rounded-lg px-4 py-3 shadow-sm bg-white flex items-center gap-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse [animation-delay:-0.3s]"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse [animation-delay:-0.15s]"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
                  </div>
                </div>
              )}

              {isProbing && (
                <div className="flex items-start gap-3 justify-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-gray-600" />
                  </div>
                  <div className="w-full md:min-w-[280px] max-h-screen  p-4 space-y-4 flex flex-col">
                    <h4 className="text-sm font-semibold text-gray-800 mb-3">Please provide more details:</h4>
                    <div className="space-y-3">
                      {probingQuestions.map((q, idx) => (
                        <input
                          key={idx}
                          type="text"
                          placeholder={q}
                          value={probingAnswers[idx] || ''}
                          onChange={(e) => handleProbingInput(idx, e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm focus:ring-blue-500 focus:border-blue-500"
                        />
                      ))}
                      <Button onClick={submitProbingAnswers} disabled={isLoading} className="mt-2">
                        {isLoading ? 'Processing...' : 'Submit Answers'}
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {warnings.length > 0 && (
                <div className="bg-red-50 border-l-4 border-red-500 text-red-800 p-4 rounded-r-lg shadow-md my-4">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="h-6 w-6 text-red-500" />
                    <div>
                      <h3 className="text-md font-semibold">Important Alerts</h3>
                      <ul className="list-disc list-inside mt-1 text-sm">
                        {warnings.map((warn, i) => (
                          <li key={i}>{warn}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              
              <div ref={messagesEndRef} />
            </div>
            <div className="border-t bg-white p-4 shrink-0">
              <div className="relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about your finances..."
                  className="w-full pl-4 pr-12 py-3 border border-gray-300 rounded-full shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-100 transition-shadow"
                  onKeyDown={(e) => e.key === 'Enter' && !isLoading && sendMessage()}
                  disabled={isLoading}
                />
                <Button
                  onClick={sendMessage}
                  disabled={isLoading}
                  size="icon"
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full h-9 w-9"
                >
                  <Send className="w-5 h-5" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ChatAssistant;