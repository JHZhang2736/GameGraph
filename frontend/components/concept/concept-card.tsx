import type { ConceptCard } from "@/lib/types";

function Chips({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
        {label}
      </div>
      <div className="mt-1 text-sm">{children}</div>
    </div>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="list-disc pl-5 text-sm">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function ConceptCardView({ card }: { card: ConceptCard }) {
  return (
    <article className="flex flex-col gap-3 rounded-lg border p-4">
      <h2 className="font-semibold">{card.title}</h2>
      <p className="text-sm text-muted-foreground">{card.one_sentence_concept}</p>

      <Field label="核心幻想">{card.core_fantasy}</Field>
      <Field label="核心循环">{card.core_loop}</Field>
      <Field label="主要玩家决策">
        <Bullets items={card.main_player_decisions} />
      </Field>
      <Field label="主要机制">
        <Chips items={card.main_mechanics} />
      </Field>
      <Field label="参考来源">
        <Chips items={card.reference_sources} />
      </Field>
      <Field label="与参考差异">{card.difference_from_references}</Field>
      <Field label="适配理由">{card.fit_reason}</Field>
      <Field label="新颖理由">{card.novelty_reason}</Field>
      <Field label="制作风险">
        <Bullets items={card.production_risks} />
      </Field>
      <Field label="设计风险">
        <Bullets items={card.design_risks} />
      </Field>
      <Field label="建议原型范围">{card.suggested_prototype_scope}</Field>
    </article>
  );
}
