"use client";

import { useState } from "react";

const CUSTOM_VALUE = "__custom__";
const EMPTY_VALUE = "";

interface EditableSelectProps {
  id?: string;
  value: string | null;
  options: string[];
  onChange: (value: string | null) => void;
  placeholder?: string;
  invalid?: boolean;
}

// A dropdown of common values plus a "自定义" path that reveals a free text input.
// `null` means the field is unset (shown as 缺失). Custom mode is also forced when
// the current value is not one of the preset options (e.g. after a reparse).
export function EditableSelect({
  id,
  value,
  options,
  onChange,
  placeholder,
  invalid,
}: EditableSelectProps) {
  const [customActive, setCustomActive] = useState(false);
  const valueIsCustom = value !== null && value !== "" && !options.includes(value);
  const showCustom = customActive || valueIsCustom;

  const selectClass =
    "h-9 w-full rounded-md border bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring" +
    (invalid ? " border-red-300" : "");

  function handleSelect(next: string) {
    if (next === CUSTOM_VALUE) {
      setCustomActive(true);
      return;
    }
    setCustomActive(false);
    onChange(next === EMPTY_VALUE ? null : next);
  }

  return (
    <div className="space-y-1">
      <select
        id={id}
        className={selectClass}
        value={showCustom ? CUSTOM_VALUE : (value ?? EMPTY_VALUE)}
        onChange={(event) => handleSelect(event.target.value)}
      >
        <option value={EMPTY_VALUE}>缺失</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
        <option value={CUSTOM_VALUE}>自定义…</option>
      </select>
      {showCustom ? (
        <input
          aria-label={id ? `${id}-custom` : undefined}
          className="h-9 w-full rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder={placeholder ?? "自定义取值"}
          value={value ?? ""}
          onChange={(event) => onChange(event.target.value || null)}
        />
      ) : null}
    </div>
  );
}
