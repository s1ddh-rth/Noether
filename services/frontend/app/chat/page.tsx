"use client";

import { useEffect, useRef, useState } from "react";

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { VegaChart } from "@/components/VegaChart";
import type { ChatAnswer, ChatTurn } from "@/lib/types";

const SESSION_KEY = "noether.chat.session";

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string>("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // Per-tab session id (sessionStorage — survives reloads, not new tabs).
  useEffect(() => {
    let sid = sessionStorage.getItem(SESSION_KEY);
    if (!sid) {
      sid = crypto.randomUUID();
      sessionStorage.setItem(SESSION_KEY, sid);
    }
    setSessionId(sid);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, busy]);

  async function send() {
    const question = input.trim();
    if (!question || busy || !sessionId) return;
    setInput("");
    setError(null);
    setTurns((t) => [...t, { role: "user", text: question }]);
    setBusy(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, question }),
      });
      const data = (await res.json()) as ChatAnswer | { error: string };
      if (!res.ok || "error" in data) {
        const msg = "error" in data ? data.error : `request failed (${res.status})`;
        setError(msg);
        return;
      }
      setTurns((t) => [
        ...t,
        {
          role: "assistant",
          text: data.answer,
          citations: data.citations,
          vegaSpec: data.vega_spec,
        },
      ]);
    } catch {
      setError("network error talking to the chat API");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto flex max-w-3xl flex-col gap-4">
      <h1 className="text-xl font-semibold">Chat</h1>

      <div className="flex min-h-[50vh] flex-col gap-3">
        {turns.length === 0 && (
          <p className="text-sm text-[var(--muted)]">
            Ask about the live plant — e.g. “what is XMEAS_7 doing right now?”
          </p>
        )}
        {turns.map((turn, i) => (
          <div key={i} className={turn.role === "user" ? "self-end" : "self-start w-full"}>
            <div
              className={`rounded-lg px-3 py-2 text-sm ${
                turn.role === "user"
                  ? "bg-[var(--accent)] text-black"
                  : "border border-[var(--border)] bg-[var(--panel)]"
              }`}
            >
              <p className="whitespace-pre-wrap">{turn.text}</p>
              {turn.vegaSpec && (
                <div className="mt-2">
                  <ErrorBoundary
                    fallback={
                      <p className="text-xs text-[var(--muted)]">Could not render chart.</p>
                    }
                  >
                    <VegaChart spec={turn.vegaSpec} />
                  </ErrorBoundary>
                </div>
              )}
              {turn.citations && turn.citations.length > 0 && (
                <footer className="mt-2 border-t border-[var(--border)] pt-1 text-xs text-[var(--muted)]">
                  <span className="font-semibold">Sources:</span>
                  <ul className="list-inside list-disc">
                    {turn.citations.map((c, j) => (
                      <li key={j} className="truncate">
                        {c}
                      </li>
                    ))}
                  </ul>
                </footer>
              )}
            </div>
          </div>
        ))}
        {busy && <p className="self-start text-sm text-[var(--muted)]">thinking…</p>}
        {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
        className="flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the operator agent…"
          aria-label="chat input"
          className="flex-1 rounded border border-[var(--border)] bg-[var(--panel)] px-3 py-2 text-sm outline-none focus:border-[var(--accent)]"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </section>
  );
}
