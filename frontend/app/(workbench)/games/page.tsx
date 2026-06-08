"use client";

import Link from "next/link";
import { useGames } from "@/lib/queries";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function GamesPage() {
  const { data, isLoading, isError, refetch } = useGames();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <PageHeader title="游戏入库" description="已入库的种子游戏" />
        <Link
          href="/games/import"
          className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:opacity-90"
        >
          导入游戏
        </Link>
      </div>
      {data.length === 0 ? (
        <EmptyState message={'种子库暂无游戏，点右上角“导入游戏”开始'} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>标题</TableHead>
              <TableHead>简述</TableHead>
              <TableHead>置信度</TableHead>
              <TableHead>质量</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((game) => (
              <TableRow key={game.id}>
                <TableCell className="font-medium">
                  <Link href={`/games/${game.id}`} className="hover:underline">
                    {game.title}
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {game.short_description}
                </TableCell>
                <TableCell>
                  <ConfidenceBadge level={game.confidence} />
                </TableCell>
                <TableCell>
                  <QualityBadge status={game.quality_status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
