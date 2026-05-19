"use client";

import { Component, type ReactNode } from "react";

// Defense-in-depth around <VegaChart>: VegaChart already catches embed
// failures, but a render-time throw from a pathological spec must not
// take down the chat page (spec §"Malformed spec is contained").
export class ErrorBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.error("ErrorBoundary caught", error);
  }

  render() {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}
