import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { VegaChart } from "@/components/VegaChart";

// vega-embed is DOM/canvas-heavy and dynamically imported by the
// component; stub it so we control resolve/reject.
const embedMock = vi.fn();
vi.mock("vega-embed", () => ({ default: (...args: unknown[]) => embedMock(...args) }));

const VALID_SPEC = {
  $schema: "https://vega.github.io/schema/vega-lite/v5.json",
  data: { values: [{ a: 1, b: 2 }] },
  mark: "line",
  encoding: { x: { field: "a" }, y: { field: "b" } },
};

describe("VegaChart", () => {
  beforeEach(() => {
    embedMock.mockReset();
  });

  it("renders the chart container for a valid spec (no fallback)", async () => {
    embedMock.mockResolvedValue({ finalize: vi.fn() });
    render(<VegaChart spec={VALID_SPEC} />);
    expect(await screen.findByTestId("vega-container")).toBeInTheDocument();
    await waitFor(() => expect(embedMock).toHaveBeenCalledTimes(1));
    expect(screen.queryByText("Could not render chart.")).toBeNull();
  });

  it("falls back (message + <details> raw spec) when embed rejects", async () => {
    embedMock.mockRejectedValue(new Error("invalid spec"));
    const { container } = render(<VegaChart spec={{ not: "valid" }} />);
    expect(await screen.findByText("Could not render chart.")).toBeInTheDocument();
    expect(container.querySelector("details")).not.toBeNull();
    expect(container.querySelector("pre")?.textContent).toContain('"not": "valid"');
  });

  it("falls back without calling embed when spec is not a plain object", async () => {
    render(<VegaChart spec={null} />);
    expect(await screen.findByText("Could not render chart.")).toBeInTheDocument();
    expect(embedMock).not.toHaveBeenCalled();
  });
});
