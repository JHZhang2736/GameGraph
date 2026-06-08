import type { MissingProfileField } from "@/lib/types";

export function ProfileMissingFields({ fields }: { fields: MissingProfileField[] }) {
  if (!fields.length) {
    return (
      <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
        没有阻断性缺失信息。
      </section>
    );
  }

  return (
    <section className="space-y-3 rounded-lg border p-4">
      <h2 className="text-sm font-medium">缺失信息</h2>
      <div className="space-y-2">
        {fields.map((field) => (
          <div
            key={field.field}
            data-missing-field={field.field}
            data-blocking={field.blocking}
            className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
          >
            <div className="font-medium">
              <span className="mr-1">{field.blocking ? "阻断" : "提示"}：</span>
              <span>{field.field}</span>
            </div>
            <div className="mt-1 text-xs">{field.reason}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
