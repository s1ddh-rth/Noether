"use client";

import useSWR from "swr";

import type { AnomalyAlert, LatestTag, RangePoint } from "@/lib/types";

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} → ${res.status}`);
  return res.json();
};

// Live tag values — 1 s cadence (spec: dashboard tiles refresh every 1 s).
export function useLatestTags() {
  return useSWR<LatestTag[]>("/api/tags/latest", fetcher, {
    refreshInterval: 1000,
    revalidateOnFocus: false,
  });
}

// Anomaly feed — 5 s cadence (spec).
export function useRecentAnomalies() {
  return useSWR<AnomalyAlert[]>("/api/anomalies/recent", fetcher, {
    refreshInterval: 5000,
    revalidateOnFocus: false,
  });
}

// Per-tag 5-minute history for the sparkline. The value badge updates
// at 1 s via useLatestTags; the sparkline shape only needs a gentler
// cadence, so 15 s keeps 52 tiles from hammering the BFF.
export function useTagRange(tag: string) {
  return useSWR<RangePoint[]>(`/api/tags/${tag}/range`, fetcher, {
    refreshInterval: 15000,
    revalidateOnFocus: false,
  });
}
