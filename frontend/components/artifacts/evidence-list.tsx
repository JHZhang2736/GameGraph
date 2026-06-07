import type { EvidenceRef } from "@/lib/types";

export function EvidenceList({ evidence }: { evidence: EvidenceRef[] }) {
  if (evidence.length === 0) {
    return <p className="text-xs text-muted-foreground">无证据记录</p>;
  }
  return (
    <ul className="space-y-1 text-xs text-muted-foreground">
      {evidence.map((ref, i) => (
        <li key={`${ref.title}-${i}`}>
          <span className="font-medium text-foreground/80">{ref.title}</span>
          {ref.url ? (
            <>
              {" — "}
              <a href={ref.url} className="underline" target="_blank" rel="noreferrer">
                {ref.url}
              </a>
            </>
          ) : ref.quote_or_summary ? (
            <>{" — “"}{ref.quote_or_summary}{"”"}</>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
