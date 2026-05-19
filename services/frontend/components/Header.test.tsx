import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Header } from "@/components/Header";

const usePathname = vi.fn();
vi.mock("next/navigation", () => ({ usePathname: () => usePathname() }));

describe("Header", () => {
  it("renders the brand and both nav links", () => {
    usePathname.mockReturnValue("/dashboard");
    render(<Header />);
    expect(screen.getByText("Noether")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/dashboard");
    expect(screen.getByRole("link", { name: "Chat" })).toHaveAttribute("href", "/chat");
  });

  it("marks the active route with aria-current", () => {
    usePathname.mockReturnValue("/chat");
    render(<Header />);
    expect(screen.getByRole("link", { name: "Chat" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Dashboard" })).not.toHaveAttribute("aria-current");
  });
});
