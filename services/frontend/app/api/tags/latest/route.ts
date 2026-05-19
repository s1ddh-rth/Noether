import { NextResponse } from "next/server";

import { pool } from "@/lib/db";
import type { LatestTag } from "@/lib/types";

// Live data — never cache.
export const dynamic = "force-dynamic";

// Newest sample per tag. DISTINCT ON (tag) with the (tag, ts DESC) index
// is a cheap single-scan; ~52 rows back.
export async function GET() {
  try {
    const { rows } = await pool.query<{ tag: string; value: number; ts: Date }>(
      `SELECT DISTINCT ON (tag) tag, value, ts
         FROM tag_samples
        ORDER BY tag, ts DESC`
    );
    const body: LatestTag[] = rows.map((r) => ({
      tag: r.tag,
      value: Number(r.value),
      ts: r.ts.toISOString(),
    }));
    return NextResponse.json(body, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (err) {
    console.error("api/tags/latest failed", err);
    return NextResponse.json({ error: "tag query failed" }, { status: 502 });
  }
}
