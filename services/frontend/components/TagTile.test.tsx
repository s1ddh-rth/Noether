import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TagTile } from "@/components/TagTile";
import type { LatestTag } from "@/lib/types";

// TagTile pulls its sparkline series from useTagRange — stub it so the
// component test needs no network.
vi.mock("@/lib/hooks", () => ({
  useTagRange: () => ({
    data: [
      { ts: "2026-05-19T11:00:00.000Z", value: 1 },
      { ts: "2026-05-19T11:00:01.000Z", value: 2 },
      { ts: "2026-05-19T11:00:02.000Z", value: 1.5 },
    ],
  }),
}));

const NOW = new Date("2026-05-19T12:00:30.000Z").getTime();

function tag(overrides: Partial<LatestTag> = {}): LatestTag {
  return {
    tag: "XMEAS_7",
    value: 42.123456,
    ts: "2026-05-19T12:00:20.000Z", // 10 s before NOW → fresh
    ...overrides,
  };
}

describe("TagTile", () => {
  it("renders the tag id and value to 3 dp", () => {
    render(<TagTile latest={tag()} now={NOW} />);
    expect(screen.getByText("XMEAS_7")).toBeInTheDocument();
    expect(screen.getByText("42.123")).toBeInTheDocument();
  });

  it("renders a sparkline svg when history is present", () => {
    render(<TagTile latest={tag()} now={NOW} />);
    const spark = screen.getByTestId("sparkline");
    expect(spark.querySelector("svg")).not.toBeNull();
  });

  it("is not stale when the latest sample is recent", () => {
    const { container } = render(<TagTile latest={tag()} now={NOW} />);
    expect(container.querySelector("[data-stale='false']")).not.toBeNull();
    expect(screen.queryByText("stale")).toBeNull();
  });

  it("marks the tile stale when the sample is older than 30 s", () => {
    const { container } = render(
      <TagTile latest={tag({ ts: "2026-05-19T11:59:00.000Z" })} now={NOW} />
    );
    expect(container.querySelector("[data-stale='true']")).not.toBeNull();
    expect(screen.getByText("stale")).toBeInTheDocument();
  });
});
