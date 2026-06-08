"use client";

import Link from "next/link";
import { useSeedGames } from "@/lib/queries";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function GamesPage() {
  const { data, isLoading, isError, refetch } = useSeedGames();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;
  if (data.length === 0) return <EmptyState message="种子库暂无游戏" />;

  return (
    <div>
      <PageHeader title="游戏入库" description="按设计相关性精选的种子游戏" />
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>标题</TableHead>
            <TableHead>简述</TableHead>
            <TableHead>选择理由</TableHead>
            <TableHead className="text-right">来源</TableHead>
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
              <TableCell className="text-muted-foreground">
                {game.selection_reason}
              </TableCell>
              <TableCell className="text-right">{game.source_refs.length}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
