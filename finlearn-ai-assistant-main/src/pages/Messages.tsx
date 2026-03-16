import { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { API_URL } from "@/lib/api";
import {
  ArrowLeft,
  MessageCircle,
  Send,
  Loader2,
  Users,
  Inbox,
} from "lucide-react";

interface ChatMessage {
  id: string;
  sender_id: string;
  receiver_id: string;
  body: string;
  created_at: string;
}

function msgSenderId(m: ChatMessage): string {
  return String((m as Record<string, unknown>).sender_id ?? (m as Record<string, unknown>).senderId ?? "").trim();
}
function msgReceiverId(m: ChatMessage): string {
  return String((m as Record<string, unknown>).receiver_id ?? (m as Record<string, unknown>).receiverId ?? "").trim();
}
/** Normalize for comparison so UUID case / format doesn't break "me" vs "other". */
function normId(id: string): string {
  return String(id ?? "").trim().toLowerCase();
}

interface Conversation {
  other_user_id: string;
  display_name: string;
  last_message: string;
  last_at: string;
}

export default function Messages() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const withParam = searchParams.get("with");

  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(withParam);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messageInput, setMessageInput] = useState("");
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [selectedDisplayName, setSelectedDisplayName] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        navigate("/");
        return;
      }
      setCurrentUserId(session.user.id);
    });
  }, [navigate]);

  useEffect(() => {
    if (withParam) setSelectedId(withParam);
  }, [withParam]);

  // Fetch conversation list
  useEffect(() => {
    if (!currentUserId) return;
    setLoadingConversations(true);
    fetch(`${API_URL}/api/conversations?user_id=${encodeURIComponent(currentUserId)}`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        setConversations(Array.isArray(data) ? data : []);
        setLoadingConversations(false);
      })
      .catch(() => {
        setConversations([]);
        setLoadingConversations(false);
      });
  }, [currentUserId]);

  // Fetch messages when selection changes
  useEffect(() => {
    if (!currentUserId || !selectedId) {
      setMessages([]);
      return;
    }
    setLoadingMessages(true);
    fetch(
      `${API_URL}/api/messages?user_id=${encodeURIComponent(currentUserId)}&with_user=${encodeURIComponent(selectedId)}`
    )
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        setMessages(Array.isArray(data) ? data : []);
        setLoadingMessages(false);
      })
      .catch(() => {
        setMessages([]);
        setLoadingMessages(false);
      });
  }, [currentUserId, selectedId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    const body = messageInput.trim();
    if (!body || !currentUserId || !selectedId || sending) return;
    setSending(true);
    try {
      const res = await fetch(`${API_URL}/api/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sender_id: currentUserId,
          receiver_id: selectedId,
          body,
        }),
      });
      if (res.ok) {
        setMessageInput("");
        const data = await res.json();
        const newMsg = data?.data?.[0];
        if (newMsg) setMessages((prev) => [...prev, newMsg]);
        else {
          const listRes = await fetch(
            `${API_URL}/api/messages?user_id=${encodeURIComponent(currentUserId)}&with_user=${encodeURIComponent(selectedId)}`
          );
          if (listRes.ok) {
            const list = await listRes.json();
            setMessages(Array.isArray(list) ? list : []);
          }
        }
        // Refresh conversation list so this thread moves to top
        const convRes = await fetch(`${API_URL}/api/conversations?user_id=${encodeURIComponent(currentUserId)}`);
        if (convRes.ok) {
          const conv = await convRes.json();
          setConversations(Array.isArray(conv) ? conv : []);
        }
      }
    } finally {
      setSending(false);
    }
  };

  const selectedConversation = conversations.find((c) => c.other_user_id === selectedId);
  // Always show the OTHER person's name (selectedId is the other user). Fetch from API so we never show current user's name.
  const displayName = selectedDisplayName ?? selectedConversation?.display_name ?? (selectedId ? `User ${selectedId.slice(0, 8)}` : "");

  // Infer "me" from thread participants (normalized IDs) so left/right works with two accounts in two tabs
  const otherNorm = normId(selectedId ?? "");
  const participantsSet = (() => {
    const set = new Set<string>();
    messages.forEach((m) => {
      set.add(normId(msgSenderId(m)));
      set.add(normId(msgReceiverId(m)));
    });
    set.delete(otherNorm);
    return set;
  })();
  const meInferredNorm = participantsSet.size === 1 ? Array.from(participantsSet)[0] : normId(currentUserId ?? "");

  // Resolve display name for the other user (selectedId) from API so chat header always shows the other person
  useEffect(() => {
    if (!selectedId) {
      setSelectedDisplayName(null);
      return;
    }
    fetch(`${API_URL}/api/users/${encodeURIComponent(selectedId)}/display-name`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data: { display_name?: string } | null) => {
        setSelectedDisplayName(data?.display_name ?? null);
      })
      .catch(() => setSelectedDisplayName(null));
  }, [selectedId]);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate("/dashboard")}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2">
              <MessageCircle className="w-5 h-5 text-primary" />
              <span className="font-display text-sm font-semibold">Messages</span>
            </div>
          </div>
          <button
            onClick={() => navigate("/social")}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted text-muted-foreground hover:text-foreground text-sm"
          >
            <Users className="w-4 h-4" />
            Community
          </button>
        </div>
      </header>

      <div className="flex-1 flex max-w-5xl w-full mx-auto">
        {/* Conversation list */}
        <aside className="w-72 border-r border-border flex flex-col bg-muted/20">
          <div className="p-3 border-b border-border">
            <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Inbox className="w-4 h-4" />
              Conversations
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loadingConversations ? (
              <div className="p-4 flex justify-center">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : conversations.length === 0 ? (
              <div className="p-4 text-sm text-muted-foreground text-center">
                No conversations yet. Go to Community and message someone to start.
              </div>
            ) : (
              conversations.map((c) => (
                <button
                  key={c.other_user_id}
                  onClick={() => setSelectedId(c.other_user_id)}
                  className={`w-full text-left px-4 py-3 border-b border-border/50 hover:bg-muted/50 transition-colors ${
                    selectedId === c.other_user_id ? "bg-primary/10 border-l-2 border-l-primary" : ""
                  }`}
                >
                  <div className="font-medium truncate">{c.display_name}</div>
                  <div className="text-xs text-muted-foreground truncate mt-0.5">
                    {c.last_message || "No messages"}
                  </div>
                  {c.last_at && (
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {new Date(c.last_at).toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                    </div>
                  )}
                </button>
              ))
            )}
          </div>
        </aside>

        {/* Thread */}
        <main className="flex-1 flex flex-col min-w-0">
          {!selectedId ? (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <MessageCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Select a conversation or message someone from Community.</p>
                <button
                  onClick={() => navigate("/social")}
                  className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm hover:opacity-90"
                >
                  Go to Community
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="border-b border-border px-4 py-3">
                <h3 className="font-semibold">{displayName}</h3>
                <p className="text-xs text-muted-foreground">Direct message</p>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
                {loadingMessages ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                  </div>
                ) : messages.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">No messages yet. Say hi!</p>
                ) : (
                  messages.map((m) => {
                    const sid = msgSenderId(m);
                    const rid = msgReceiverId(m);
                    const isMe = normId(sid) === meInferredNorm && normId(rid) === otherNorm;
                    return (
                      <div key={m.id} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
                        <div
                          className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                            isMe ? "bg-primary text-primary-foreground" : "bg-muted"
                          }`}
                        >
                          <p className="whitespace-pre-wrap break-words">{m.body}</p>
                          <p className={`text-xs mt-1 ${isMe ? "text-primary-foreground/80" : "text-muted-foreground"}`}>
                            {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </p>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>
              <div className="border-t border-border p-3 flex gap-2">
                <input
                  type="text"
                  placeholder="Type a message..."
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                  className="flex-1 px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <button
                  onClick={sendMessage}
                  disabled={!messageInput.trim() || sending}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5 text-sm"
                >
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  Send
                </button>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
