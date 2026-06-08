"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_GROUPS, OVERVIEW_ITEM } from "@/lib/nav";
import { cn } from "@/lib/utils";

function NavLink({ href, label }: { href: string; label: string }) {
  const pathname = usePathname();
  const active = pathname !== null && (pathname === href || pathname.startsWith(`${href}/`));
  return (
    <Link
      href={href}
      className={cn(
        "block rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground",
        active && "bg-accent font-medium text-accent-foreground",
      )}
    >
      {label}
    </Link>
  );
}

export function AppSidebar() {
  return (
    <aside className="flex w-56 flex-col gap-4 border-r bg-background p-3">
      <div className="flex items-center gap-2 px-2 py-1 font-semibold">
        <span className="inline-block h-4 w-4 rounded bg-primary" />
        GameGraph
      </div>
      {NAV_GROUPS.map((group) => (
        <div key={group.title}>
          <div className="px-3 pb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
            {group.title}
          </div>
          {group.items.map((item) => (
            <NavLink key={item.href} {...item} />
          ))}
        </div>
      ))}
      <div className="mt-auto border-t pt-2">
        <NavLink {...OVERVIEW_ITEM} />
      </div>
    </aside>
  );
}
