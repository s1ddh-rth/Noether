import { expect, test } from "@playwright/test";

// Runs against `docker compose --profile core` (frontend on :3001).
// The agent isn't in `core`, so the chat assertion accepts either an
// assistant reply (agent up) or the graceful error (agent down) — the
// invariant is "the page handles the round-trip without crashing"
// (spec §"Round-trip chat turn", which presupposes the backend; CI
// core has no LLM).

test("dashboard renders live tag tiles + the anomaly panel", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Anomalies" })).toBeVisible();
  // ≥1 tile with a stale attribute appears once the BFF responds.
  await expect(page.locator("[data-stale]").first()).toBeVisible({ timeout: 15_000 });
  const tiles = await page.locator("[data-stale]").count();
  expect(tiles).toBeGreaterThan(0);
});

test("nav switches to the chat route and a turn does not crash the page", async ({ page }) => {
  await page.goto("/dashboard");
  await page.getByRole("link", { name: "Chat" }).click();
  await expect(page).toHaveURL(/\/chat$/);
  await expect(page.getByRole("heading", { name: "Chat" })).toBeVisible();

  await page.getByLabel("chat input").fill("what is XMEAS_7 doing right now?");
  await page.getByRole("button", { name: "Send" }).click();

  // The user message must always echo into the pane.
  await expect(page.getByText("what is XMEAS_7 doing right now?")).toBeVisible();
  // Then either an assistant bubble (agent up) or the inline error
  // (agent down in core) — both are non-crash outcomes.
  await expect
    .poll(
      async () => {
        const err = await page.getByText(/agent unreachable|network error/).count();
        const sources = await page.getByText("Sources:").count();
        const bubbles = await page.locator(".self-start").count();
        return err + sources + bubbles;
      },
      { timeout: 20_000 }
    )
    .toBeGreaterThan(0);
});
