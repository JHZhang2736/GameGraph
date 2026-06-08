"use client";

import { useState } from "react";
import { JsonInput } from "@/components/import/json-input";
import { PageHeader } from "@/components/shell/view-states";
import type { ImportDocument } from "@/lib/import/schema";

export default function ImportPage() {
  const [doc, setDoc] = useState<ImportDocument | null>(null);

  return (
    <div>
      <PageHeader title="导入游戏" description="粘贴或上传 GameImportDocument,校验后预览并入库" />
      {doc === null ? (
        <JsonInput onValid={setDoc} />
      ) : (
        <p className="text-sm text-muted-foreground">{"已校验通过:"}{doc.candidate.title}{"(预览见下一步)"}</p>
      )}
    </div>
  );
}
