// Shapes returned by the BFF routes and consumed by the dashboard.
// Kept tiny and explicit — the browser only ever sees these.

export interface LatestTag {
  tag: string;
  value: number;
  ts: string; // ISO8601
}

export interface RangePoint {
  ts: string;
  value: number;
}

export interface AnomalyAlert {
  alertId: string;
  ts: string;
  score: number;
  alert: boolean;
  tags: string[];
}
