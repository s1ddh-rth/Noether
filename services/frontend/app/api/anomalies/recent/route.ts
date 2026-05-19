import { NextResponse } from "next/server";

import { pool } from "@/lib/db";
import type { AnomalyAlert } from "@/lib/types";

export const dynamic = "force-dynamic";

// Latest 20 anomaly rows, newest first.
export async function GET() {
  try {
    const { rows } = await pool.query<{
      alert_id: string;
      ts: Date;
      score: number;
      alert: boolean;
      tags: string[];
    }>(
      `SELECT alert_id, ts, score, alert, tags
         FROM tag_anomalies
        ORDER BY ts DESC
        LIMIT 20`
    );
    const body: AnomalyAlert[] = rows.map((r) => ({
      alertId: r.alert_id,
      ts: r.ts.toISOString(),
      score: Number(r.score),
      alert: r.alert,
      tags: r.tags ?? [],
    }));
    return NextResponse.json(body, { headers: { "Cache-Control": "no-store" } });
  } catch (err) {
    console.error("api/anomalies/recent failed", err);
    return NextResponse.json({ error: "anomaly query failed" }, { status: 502 });
  }
}
