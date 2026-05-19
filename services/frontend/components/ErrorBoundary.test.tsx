import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ErrorBoundary } from "@/components/ErrorBoundary";

function Boom(): never {
  throw new Error("render exploded");
}

describe("ErrorBoundary", () => {
  it("renders children when they don't throw", () => {
    render(
      <ErrorBoundary fallback={<span>fallback</span>}>
        <span>ok content</span>
      </ErrorBoundary>
    );
    expect(screen.getByText("ok content")).toBeInTheDocument();
    expect(screen.queryByText("fallback")).toBeNull();
  });

  it("renders the fallback when a child throws", () => {
    // React logs the caught error; silence it for a clean test run.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary fallback={<span>fallback shown</span>}>
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByText("fallback shown")).toBeInTheDocument();
    spy.mockRestore();
  });
});
