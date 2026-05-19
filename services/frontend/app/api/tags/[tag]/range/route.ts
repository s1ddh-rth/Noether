import { NextRequest, NextResponse } from "next/server";

import { pool } from "@/lib/db";
import type { RangePoint } from "@/lib/types";

export const dynamic = "force-dynamic";

// Tag ids are simple identifiers (XMEAS_1, XMV_11, ...). Reject anything
// else defensively even though the query is parameterised.
const TAG_RE = /^[A-Za-z0-9_]{1,64}$/;

// Last 5 minutes of one tag, oldest→newest, for a sparkline.
export async function GET(_req: NextRequest, { params }: { params: { tag: string } }) {
  const tag = params.tag;
  if (!TAG_RE.test(tag)) {
    return NextResponse.json({ error: "invalid tag" }, { status: 400 });
  }
  try {
    const { rows } = await pool.query<{ ts: Date; value: number }>(
      `SELECT ts, value
         FROM tag_samples
        WHERE tag = $1 AND ts > now() - interval '5 minutes'
        ORDER BY ts ASC`,
      [tag]
    );
    const body: RangePoint[] = rows.map((r) => ({
      ts: r.ts.toISOString(),
      value: Number(r.value),
    }));
    return NextResponse.json(body, { headers: { "Cache-Control": "no-store" } });
  } catch (err) {
    console.error("api/tags/[tag]/range failed", err);
    return NextResponse.json({ error: "range query failed" }, { status: 502 });
  }
}
