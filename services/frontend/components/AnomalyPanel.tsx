"use client";

import { useRecentAnomalies } from "@/lib/hooks";

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function AnomalyPanel() {
  const { data, error } = useRecentAnomalies();
  const alerts = data ?? [];

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-4">
      <h2 className="text-sm font-semibold">Anomalies</h2>
      {error && <p className="mt-2 text-xs text-[var(--danger)]">feed unavailable</p>}
      {!error && alerts.length === 0 && (
        <p className="mt-2 text-xs text-[var(--muted)]">no alerts yet</p>
      )}
      <ul className="mt-2 flex flex-col gap-1">
        {alerts.map((a) => (
          <li
            key={a.alertId}
            className="flex items-center justify-between gap-3 rounded border border-[var(--border)] px-2 py-1.5 text-xs"
          >
            <span className="font-mono text-[var(--muted)]">{fmtTime(a.ts)}</span>
            <span
              className={`font-mono tabular-nums ${
                a.alert ? "text-[var(--danger)]" : "text-[var(--foreground)]"
              }`}
            >
              {a.score.toFixed(3)}
            </span>
            <span className="flex-1 truncate text-right text-[var(--muted)]">
              {a.tags.length ? a.tags.join(", ") : "—"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
