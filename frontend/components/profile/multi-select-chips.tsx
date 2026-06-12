"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface MultiSelectChipsProps {
  id?: string;
  value: string[];
  onChange: (value: string[]) => void;
  // 可选受控建议项（如「可靶向体验」）。不传则只能自由输入。
  options?: string[];
  placeholder?: string;
  invalid?: boolean;
}

// 多选 chips：已选项渲染为可移除标签，配一个「添加…」下拉（有 options 时）
// 与一个自由输入框（回车 / 逗号添加）。值始终是去重的字符串数组。
export function MultiSelectChips({
  id,
  value,
  onChange,
  options,
  placeholder,
  invalid,
}: MultiSelectChipsProps) {
  const [draft, setDraft] = useState("");

  function add(item: string) {
    const next = item.trim();
    if (!next || value.includes(next)) return;
    onChange([...value, next]);
  }

  function remove(item: string) {
    onChange(value.filter((entry) => entry !== item));
  }

  function commitDraft() {
    if (draft.trim()) {
      add(draft);
      setDraft("");
    }
  }

  const available = (options ?? []).filter((option) => !value.includes(option));

  return (
    <div
      className={cn(
        "space-y-1 rounded-md border bg-background p-2",
        invalid && "border-red-300",
      )}
    >
      {value.length ? (
        <div className="flex flex-wrap gap-1">
          {value.map((item) => (
            <span
              key={item}
              className="inline-flex items-center gap-1 rounded-full border bg-muted px-2 py-0.5 text-xs"
            >
              {item}
              <button
                type="button"
                aria-label={`移除 ${item}`}
                className="text-muted-foreground hover:text-foreground"
                onClick={() => remove(item)}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      ) : null}
      <div className="flex gap-1">
        {options && available.length ? (
          <select
            aria-label={id ? `${id}-add` : "添加选项"}
            className="h-8 rounded-md border bg-background px-2 text-sm outline-none"
            value=""
            onChange={(event) => {
              if (event.target.value) add(event.target.value);
            }}
          >
            <option value="">添加…</option>
            {available.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        ) : null}
        <input
          id={id}
          className="h-8 flex-1 rounded-md border bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder={placeholder ?? "输入后回车添加"}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === ",") {
              event.preventDefault();
              commitDraft();
            }
          }}
          onBlur={commitDraft}
        />
      </div>
    </div>
  );
}
