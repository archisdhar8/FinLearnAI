import { useState, useRef, useEffect, useMemo } from "react";
import { Send, Bot, User, Sparkles, X, MessageSquare } from "lucide-react";

// Simple markdown parser for chat messages
function parseMarkdown(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Bold: **text**
    const boldMatch = remaining.match(/^\*\*(.+?)\*\*/);
    if (boldMatch) {
      parts.push(<strong key={key++} className="font-semibold">{boldMatch[1]}</strong>);
      remaining = remaining.slice(boldMatch[0].length);
      continue;
    }

    // Italic: *text*
    const italicMatch = remaining.match(/^\*(.+?)\*/);
    if (italicMatch) {
      parts.push(<em key={key++}>{italicMatch[1]}</em>);
      remaining = remaining.slice(italicMatch[0].length);
      continue;
    }

    // Headers: ## text (on its own line)
    const headerMatch = remaining.match(/^##\s+(.+?)(?:\n|$)/);
    if (headerMatch) {
      parts.push(<span key={key++} className="font-bold text-primary block mt-3 mb-1">{headerMatch[1]}</span>);
      remaining = remaining.slice(headerMatch[0].length);
      continue;
    }

    // Bullet points: - text (on its own line)
    const bulletMatch = remaining.match(/^[-•]\s+(.+?)(?:\n|$)/);
    if (bulletMatch) {
      parts.push(<span key={key++} className="block pl-3 before:content-['•'] before:mr-2 before:text-primary">{bulletMatch[1]}</span>);
      remaining = remaining.slice(bulletMatch[0].length);
      continue;
    }

    // Line breaks
    if (remaining.startsWith('\n\n')) {
      parts.push(<span key={key++} className="block h-2" />);
      remaining = remaining.slice(2);
      continue;
    }
    if (remaining.startsWith('\n')) {
      parts.push(<br key={key++} />);
      remaining = remaining.slice(1);
      continue;
    }

    // Regular text - take until next special character
    const nextSpecial = remaining.search(/[\*\n#-]/);
    if (nextSpecial === -1) {
      parts.push(remaining);
      break;
    } else if (nextSpecial === 0) {
      // Special char but didn't match patterns above, treat as regular text
      parts.push(remaining[0]);
      remaining = remaining.slice(1);
    } else {
      parts.push(remaining.slice(0, nextSpecial));
      remaining = remaining.slice(nextSpecial);
    }
  }

  return parts;
}

type Source = {
  title: string;
  snippet: string;
  score: number;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
};

const SUGGESTED_QUESTIONS = [
  "What is dollar-cost averaging?",
  "How do ETFs work?",
  "Explain compound interest",
  "What's the difference between stocks and bonds?",
];

interface ChatPanelProps {
  defaultOpen?: boolean;
}

export function ChatPanel({ defaultOpen = false }: ChatPanelProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "👋 Hi! I'm your FinLearn AI assistant. Ask me anything about investing — from basic concepts to advanced strategies. I'm here to help you learn!",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText || isLoading) return;

    const userMsg: Message = { role: "user", content: messageText };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const { API_URL } = await import("@/lib/api");
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: messageText }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessages((prev) => [
          ...prev,
          { 
            role: "assistant", 
            content: data.response,
            sources: data.sources || []
          },
        ]);
      } else {
        throw new Error("API request failed");
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I'm having trouble connecting to the server. Make sure the backend is running on port 8000.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 p-4 rounded-full bg-primary text-primary-foreground glow-gold hover:scale-105 transition-transform"
      >
        <MessageSquare className="w-6 h-6" />
      </button>
    );
  }

  return (
    <div className="w-full h-full flex flex-col border-l border-border bg-card">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10">
            <Sparkles className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h3 className="font-body text-sm font-semibold">FinLearn AI</h3>
            <p className="text-xs text-muted-foreground">Your investing tutor</p>
          </div>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && (
              <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot className="w-4 h-4 text-primary" />
              </div>
            )}
            <div
              className={`max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "glass-card"
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.role === "assistant" ? parseMarkdown(msg.content) : msg.content}</div>
              {/* Display sources for assistant messages */}
              {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border/50">
                  <p className="text-xs text-muted-foreground mb-2 font-medium">Sources:</p>
                  <div className="space-y-1.5">
                    {msg.sources.slice(0, 3).map((source, idx) => (
                      <div 
                        key={idx} 
                        className="text-xs bg-muted/50 rounded-lg px-2.5 py-1.5"
                      >
                        <span className="font-medium text-primary">[{idx + 1}]</span>{" "}
                        <span className="text-foreground/80">{source.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {msg.role === "user" && (
              <div className="w-7 h-7 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0 mt-0.5">
                <User className="w-4 h-4 text-muted-foreground" />
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-primary" />
            </div>
            <div className="glass-card rounded-xl px-4 py-3">
              <div className="flex gap-1.5">
                <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2 flex flex-wrap gap-2">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              className="text-xs px-3 py-1.5 rounded-full border border-border text-muted-foreground hover:border-primary hover:text-primary transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-border">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about investing..."
            className="flex-1 bg-muted rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            className="p-2.5 rounded-xl bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
