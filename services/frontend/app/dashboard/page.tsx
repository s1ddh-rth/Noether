// Phase 2 fills this with live tag tiles + the anomaly panel. Phase 1
// ships the route + the BFF endpoints it will consume.
export default function DashboardPage() {
  return (
    <section>
      <h1 className="text-xl font-semibold">Dashboard</h1>
      <p className="mt-2 text-sm text-[var(--muted)]">
        Live tag tiles and the anomaly feed land in phase 2. The BFF endpoints (
        <code>/api/tags/latest</code>, <code>/api/tags/[tag]/range</code>,{" "}
        <code>/api/anomalies/recent</code>) are live now.
      </p>
    </section>
  );
}
