"use client";

import { useState } from "react";
import { parseImportDocument, type FieldError } from "@/lib/import/schema";
import type { ImportDocument } from "@/lib/import/schema";

export function JsonInput({
  onValid,
}: {
  onValid: (doc: ImportDocument) => void;
}) {
  const [text, setText] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldError[]>([]);

  function validate() {
    setParseError(null);
    setFieldErrors([]);
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      setParseError("无法解析 JSON,请检查格式");
      return;
    }
    const result = parseImportDocument(parsed);
    if (result.ok) {
      onValid(result.document);
    } else {
      setFieldErrors(result.errors);
    }
  }

  async function pasteFromClipboard() {
    try {
      setText(await navigator.clipboard.readText());
    } catch {
      setParseError("无法读取剪贴板,请手动粘贴");
    }
  }

  function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    file.text().then(setText);
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={pasteFromClipboard}
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent"
        >
          从剪贴板粘贴
        </button>
        <label className="cursor-pointer rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
          上传 .json 文件
          <input type="file" accept="application/json,.json" className="hidden" onChange={onFile} />
        </label>
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="粘贴 GameImportDocument JSON…"
        className="h-64 w-full rounded-md border p-3 font-mono text-xs"
      />
      <button
        type="button"
        onClick={validate}
        className="rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground hover:opacity-90"
      >
        校验并预览
      </button>
      {parseError ? (
        <p className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">{parseError}</p>
      ) : null}
      {fieldErrors.length > 0 ? (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          <p className="mb-1 font-medium">{"校验未通过:"}</p>
          <ul className="list-disc space-y-1 pl-5">
            {fieldErrors.map((e, i) => (
              <li key={i}>
                <code>{e.path || "(根)"}</code> — {e.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
