"use client";

import { useState } from "react";
import { JsonInput } from "@/components/import/json-input";
import { ImportPreview } from "@/components/import/import-preview";
import { ImportResult } from "@/components/import/import-result";
import { PageHeader } from "@/components/shell/view-states";
import { useImportGame } from "@/lib/queries";
import type { ImportDocument } from "@/lib/import/schema";

export default function ImportPage() {
  const [doc, setDoc] = useState<ImportDocument | null>(null);
  const mutation = useImportGame();

  function reset() {
    mutation.reset();
    setDoc(null);
  }

  if (mutation.isSuccess) {
    return (
      <div>
        <PageHeader title="导入游戏" description="入库结果" />
        <ImportResult summary={mutation.data} onImportAnother={reset} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="导入游戏" description="粘贴或上传 GameImportDocument,校验后预览并入库" />
      {doc === null ? (
        <JsonInput onValid={setDoc} />
      ) : (
        <div className="space-y-3">
          {mutation.isError ? (
            <p className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">
              {"入库失败:"}{(mutation.error as Error).message}
            </p>
          ) : null}
          <ImportPreview
            document={doc}
            onBack={reset}
            onConfirm={() => mutation.mutate(doc)}
            pending={mutation.isPending}
          />
        </div>
      )}
    </div>
  );
}
