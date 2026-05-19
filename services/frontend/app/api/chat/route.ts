import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const AGENT_URL = process.env.AGENT_URL ?? "http://agent:8100";

// Proxy to services/agent POST /chat. The agent API key is injected
// server-side here so it never reaches the browser. The agent is
// JSON-only today (its router notes SSE is a future follow-up); when it
// gains SSE this handler can stream by forwarding the response body and
// flipping the content-type — the client already tolerates either.
export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }
  const { session_id, question } = (body ?? {}) as {
    session_id?: unknown;
    question?: unknown;
  };
  if (typeof session_id !== "string" || typeof question !== "string" || !question.trim()) {
    return NextResponse.json(
      { error: "session_id and question (non-empty) are required" },
      { status: 400 }
    );
  }

  try {
    const upstream = await fetch(`${AGENT_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.AGENT_API_KEY ?? "",
      },
      body: JSON.stringify({ session_id, question }),
    });
    const text = await upstream.text();
    if (!upstream.ok) {
      console.error("agent /chat non-ok", upstream.status, text.slice(0, 300));
      return NextResponse.json({ error: `agent responded ${upstream.status}` }, { status: 502 });
    }
    return new NextResponse(text, {
      status: 200,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
    });
  } catch (err) {
    console.error("agent /chat proxy failed", err);
    return NextResponse.json(
      { error: "agent unreachable — is the `agent` profile up?" },
      { status: 502 }
    );
  }
}
