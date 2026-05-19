"use client";

import { AnomalyPanel } from "@/components/AnomalyPanel";
import { TagTile } from "@/components/TagTile";
import { useLatestTags } from "@/lib/hooks";

export default function DashboardPage() {
  const { data, error, isLoading } = useLatestTags();
  const tags = [...(data ?? [])].sort((a, b) => a.tag.localeCompare(b.tag));

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h1 className="text-xl font-semibold">Dashboard</h1>
          <span className="text-xs text-[var(--muted)]">{tags.length} tags · 1 s refresh</span>
        </div>
        {error && <p className="text-sm text-[var(--danger)]">tag feed unavailable</p>}
        {isLoading && <p className="text-sm text-[var(--muted)]">loading…</p>}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
          {tags.map((t) => (
            <TagTile key={t.tag} latest={t} />
          ))}
        </div>
      </section>
      <AnomalyPanel />
    </div>
  );
}
