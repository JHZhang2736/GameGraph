"use client";

// Placeholder for long-task progress. A real SSE/polling source replaces the
// static value later; the component contract stays the same.
export function TaskProgress() {
  return (
    <span className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-green-200 bg-green-50 px-2.5 py-1 text-xs text-green-700">
      <span aria-hidden>●</span>
      图谱构建 完成
    </span>
  );
}
