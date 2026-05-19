"use client";

import { useEffect, useRef, useState } from "react";

// Renders an agent-emitted Vega-Lite spec. Malformed specs must never
// crash the page (spec §"Vega-Lite renderer"): we validate, isolate the
// embed in try/catch, and fall back to a message + the raw spec under a
// <details>. vega-embed is heavy and DOM-only → dynamically imported.
export function VegaChart({ spec }: { spec: Record<string, unknown> | null | undefined }) {
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let finalize: (() => void) | undefined;
    let cancelled = false;

    const isPlainObject = spec != null && typeof spec === "object" && !Array.isArray(spec);
    if (!isPlainObject || !ref.current) {
      setFailed(!isPlainObject);
      return;
    }
    setFailed(false);

    import("vega-embed")
      .then(({ default: embed }) => {
        if (cancelled || !ref.current) return;
        return embed(ref.current, spec as object, {
          actions: false,
          renderer: "svg",
        });
      })
      .then((result) => {
        if (result) finalize = result.finalize;
      })
      .catch((err) => {
        console.error("vega-embed failed", err);
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
      try {
        finalize?.();
      } catch {
        /* finalize best-effort */
      }
    };
  }, [spec]);

  if (failed) {
    return (
      <div className="rounded border border-[var(--border)] bg-[var(--panel)] p-3 text-xs">
        <p className="text-[var(--muted)]">Could not render chart.</p>
        <details className="mt-1">
          <summary className="cursor-pointer text-[var(--muted)]">raw spec</summary>
          <pre className="mt-1 overflow-auto text-[10px]">
            {JSON.stringify(spec ?? null, null, 2)}
          </pre>
        </details>
      </div>
    );
  }

  return <div ref={ref} data-testid="vega-container" className="overflow-auto" />;
}
