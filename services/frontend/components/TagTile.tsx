"use client";

import { Line, LineChart } from "recharts";

import { useTagRange } from "@/lib/hooks";
import type { LatestTag } from "@/lib/types";

// A sample older than this is "stale" (spec: >30 s → data-stale).
const STALE_MS = 30_000;

export function TagTile({ latest, now }: { latest: LatestTag; now?: number }) {
  const { data: range } = useTagRange(latest.tag);
  const ref = now ?? Date.now();
  const ageMs = ref - new Date(latest.ts).getTime();
  const stale = ageMs > STALE_MS;
  const points = range ?? [];

  return (
    <div
      data-stale={stale ? "true" : "false"}
      className={`rounded-lg border p-3 ${
        stale
          ? "border-[var(--danger)] bg-[color-mix(in_srgb,var(--danger)_8%,var(--panel))]"
          : "border-[var(--border)] bg-[var(--panel)]"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs text-[var(--muted)]">{latest.tag}</span>
        {stale && (
          <span className="rounded bg-[var(--danger)] px-1.5 py-0.5 text-[10px] font-semibold text-black">
            stale
          </span>
        )}
      </div>
      <div className="mt-1 font-mono text-lg tabular-nums">
        {Number.isFinite(latest.value) ? latest.value.toFixed(3) : "—"}
      </div>
      <div className="mt-1 h-9" data-testid="sparkline">
        {points.length > 1 ? (
          <LineChart width={140} height={36} data={points}>
            <Line
              type="monotone"
              dataKey="value"
              stroke="var(--accent)"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        ) : (
          <span className="text-[10px] text-[var(--muted)]">no recent history</span>
        )}
      </div>
    </div>
  );
}
