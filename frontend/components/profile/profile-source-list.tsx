import { Badge } from "@/components/ui/badge";
import type { ProfileFieldSource } from "@/lib/types";

export function ProfileSourceList({ sources }: { sources: ProfileFieldSource[] }) {
  return (
    <section className="space-y-3 rounded-lg border p-4">
      <h2 className="text-sm font-medium">字段来源</h2>
      {sources.length ? (
        <div className="space-y-2">
          {sources.map((source, index) => (
            <div
              key={`${source.field}-${index}`}
              className="rounded-md border p-3 text-sm"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{source.field}</span>
                <Badge variant="outline">{source.source_kind}</Badge>
                <Badge variant="secondary">{source.confidence}</Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{source.source_text}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">尚无字段来源。</p>
      )}
    </section>
  );
}
