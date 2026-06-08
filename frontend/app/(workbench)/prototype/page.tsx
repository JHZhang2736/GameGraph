"use client";

import { usePrototypeBrief } from "@/lib/queries";
import {
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";

function SignalList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "success" | "failure";
}) {
  const toneClass =
    tone === "success"
      ? "border-green-200 bg-green-50 text-green-800"
      : "border-red-200 bg-red-50 text-red-800";
  return (
    <div className={`rounded-lg border p-3 ${toneClass}`}>
      <h2 className="mb-2 text-sm font-semibold">{title}</h2>
      <ul className="list-disc pl-5 text-sm">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function PrototypePage() {
  const { data, isLoading, isError, refetch } = usePrototypeBrief();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      <PageHeader title="原型验证简报" description="把最大不确定性转化为最小可执行测试" />

      <section className="rounded-lg border p-4">
        <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
          最大风险假设
        </h2>
        <p className="text-sm">{data.largest_risk_hypothesis}</p>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border p-3">
          <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
            最小原型范围
          </h2>
          <p className="text-sm">{data.minimum_prototype_scope}</p>
        </div>
        <div className="rounded-lg border p-3">
          <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
            目标试玩时长
          </h2>
          <p className="text-sm">{data.target_playtest_duration}</p>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <SignalList title="成功信号" items={data.success_signals} tone="success" />
        <SignalList title="失败信号" items={data.failure_signals} tone="failure" />
      </section>

      <section className="rounded-lg border border-dashed p-3">
        <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
          暂时不要做
        </h2>
        <p className="text-sm text-muted-foreground">
          {data.do_not_build_yet.join("、")}
        </p>
      </section>
    </div>
  );
}
