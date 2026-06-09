import { NODE_TYPES, DEFAULT_NODE_COLOR } from "@/components/graph/node-style";

// 图例:只列出当前图里实际出现的节点类型,避免 21 种全列占屏。
export function GraphLegend({
  types,
  highlight,
  className,
}: {
  types: string[];
  highlight?: string | null;
  className?: string;
}) {
  const present = new Set(types);
  const known = NODE_TYPES.filter((t) => present.has(t.type));
  const hasUnknown = types.some(
    (t) => !NODE_TYPES.some((known) => known.type === t),
  );

  if (known.length === 0 && !hasUnknown) return null;

  return (
    <div
      className={`max-h-[70%] overflow-auto rounded-lg border bg-background/90 p-2 text-xs shadow-sm backdrop-blur ${className ?? ""}`}
    >
      <div className="mb-1 font-medium text-muted-foreground">{"图例"}</div>
      <ul className="space-y-1">
        {known.map((t) => {
          const active = t.type === highlight;
          return (
            <li
              key={t.type}
              className={`flex items-center gap-2 rounded px-1 transition-colors ${
                active ? "bg-accent font-medium" : ""
              }`}
            >
              <span
                className={`inline-block h-3 w-3 shrink-0 rounded-full ${
                  active ? "ring-2 ring-foreground ring-offset-1" : ""
                }`}
                style={{ backgroundColor: t.color }}
              />
              <span>{t.label}</span>
            </li>
          );
        })}
        {hasUnknown ? (
          <li className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-3 shrink-0 rounded-full"
              style={{ backgroundColor: DEFAULT_NODE_COLOR }}
            />
            <span>{"其他"}</span>
          </li>
        ) : null}
      </ul>
    </div>
  );
}
