"use client";

import { useConcepts } from "@/lib/queries";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import type { EvaluationCategory } from "@/lib/types";
import { cn } from "@/lib/utils";

const CATEGORY_LABEL: Record<EvaluationCategory, string> = {
  safe: "稳妥型",
  balanced: "平衡型",
  challenging: "挑战型",
};

const CATEGORY_STYLE: Record<EvaluationCategory, string> = {
  safe: "border-zinc-200 bg-zinc-50 text-zinc-600",
  balanced: "border-blue-200 bg-blue-50 text-blue-700",
  challenging: "border-amber-200 bg-amber-50 text-amber-700",
};

export default function ConceptsPage() {
  const { data, isLoading, isError, refetch } = useConcepts();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;
  if (data.cards.length === 0) return <EmptyState message="暂无概念卡" />;

  return (
    <div>
      <PageHeader title="概念卡对比" description="由机会框架推导出的具体概念,附评估分类" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.cards.map((card) => {
          const evaluation = data.evaluations.find(
            (e) => e.concept_card_id === card.id,
          );
          return (
            <article key={card.id} className="flex flex-col rounded-lg border p-4">
              <div className="mb-2 flex items-start gap-2">
                <h2 className="font-semibold">{card.title}</h2>
                {evaluation ? (
                  <span
                    className={cn(
                      "ml-auto rounded-full border px-2 py-0.5 text-xs",
                      CATEGORY_STYLE[evaluation.category],
                    )}
                  >
                    {CATEGORY_LABEL[evaluation.category]}
                  </span>
                ) : null}
              </div>
              <p className="mb-3 text-sm text-muted-foreground">
                {card.one_sentence_concept}
              </p>

              <div className="mb-2">
                <div className="text-xs font-medium text-muted-foreground">
                  与参考作品的差异
                </div>
                <p className="text-sm">{card.difference_from_references}</p>
              </div>

              <div className="mb-2">
                <div className="text-xs font-medium text-muted-foreground">制作风险</div>
                <ul className="list-disc pl-5 text-sm">
                  {card.production_risks.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>

              <div>
                <div className="text-xs font-medium text-muted-foreground">设计风险</div>
                <ul className="list-disc pl-5 text-sm">
                  {card.design_risks.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>

              {evaluation ? (
                <dl className="mt-3 grid grid-cols-2 gap-2 border-t pt-3 text-xs">
                  <div>适配 {evaluation.fit_score}/5</div>
                  <div>可行 {evaluation.feasibility_score}/5</div>
                  <div>新颖 {evaluation.novelty_score}/5</div>
                  <div>风险 {evaluation.risk_score}/5</div>
                  <div className="col-span-2">
                    证据质量 {evaluation.evidence_quality_score}/5
                  </div>
                </dl>
              ) : null}
            </article>
          );
        })}
      </div>
    </div>
  );
}
