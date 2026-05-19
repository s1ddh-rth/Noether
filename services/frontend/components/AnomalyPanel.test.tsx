import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AnomalyPanel } from "@/components/AnomalyPanel";
import type { AnomalyAlert } from "@/lib/types";

const useRecentAnomalies = vi.fn();
vi.mock("@/lib/hooks", () => ({
  useRecentAnomalies: () => useRecentAnomalies(),
}));

function alert(o: Partial<AnomalyAlert> = {}): AnomalyAlert {
  return {
    alertId: "a1",
    ts: "2026-05-19T12:00:00.000Z",
    score: 0.873,
    alert: true,
    tags: ["XMEAS_1", "XMV_2"],
    ...o,
  };
}

describe("AnomalyPanel", () => {
  it("renders alerts with score and contributing tags", () => {
    useRecentAnomalies.mockReturnValue({ data: [alert()], error: undefined });
    render(<AnomalyPanel />);
    expect(screen.getByText("Anomalies")).toBeInTheDocument();
    expect(screen.getByText("0.873")).toBeInTheDocument();
    expect(screen.getByText("XMEAS_1, XMV_2")).toBeInTheDocument();
  });

  it("shows an empty state when there are no alerts", () => {
    useRecentAnomalies.mockReturnValue({ data: [], error: undefined });
    render(<AnomalyPanel />);
    expect(screen.getByText("no alerts yet")).toBeInTheDocument();
  });

  it("shows an error state when the feed fails", () => {
    useRecentAnomalies.mockReturnValue({ data: undefined, error: new Error("boom") });
    render(<AnomalyPanel />);
    expect(screen.getByText("feed unavailable")).toBeInTheDocument();
  });

  it("keeps the BFF newest-first order (no client re-sort)", () => {
    const rows = [
      alert({ alertId: "new", ts: "2026-05-19T12:05:00.000Z", score: 0.9 }),
      alert({ alertId: "old", ts: "2026-05-19T12:00:00.000Z", score: 0.1 }),
    ];
    useRecentAnomalies.mockReturnValue({ data: rows, error: undefined });
    render(<AnomalyPanel />);
    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("0.900");
    expect(items[1]).toHaveTextContent("0.100");
  });
});
