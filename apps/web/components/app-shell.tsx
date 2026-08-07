"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, TrendingUp, Receipt, Wallet, Settings, Landmark } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "仪表盘", icon: LayoutDashboard },
  { href: "/portfolio", label: "持仓与资金", icon: Wallet },
  { href: "/signals", label: "每周信号", icon: TrendingUp },
  { href: "/trades", label: "交易日志", icon: Receipt },
  { href: "/settings", label: "设置", icon: Settings },
];

function NavItems({ pathname, vertical }: { pathname: string; vertical: boolean }) {
  return (
    <>
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-2.5 rounded-lg text-sm font-medium transition-colors",
              vertical ? "px-3 py-2" : "px-3 py-1.5 whitespace-nowrap",
              active
                ? "bg-primary/8 text-primary shadow-[inset_2px_0_0_var(--primary)]"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <Icon className="size-4 shrink-0" />
            {label}
          </Link>
        );
      })}
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-full flex-1">
      {/* 桌面侧边栏 */}
      <aside className="hidden md:flex w-52 shrink-0 flex-col border-r bg-surface sticky top-0 h-screen overflow-y-auto">
        <div className="flex items-center gap-2 px-4 py-4 border-b">
          <Landmark className="size-5 text-primary" />
          <div className="leading-tight">
            <div className="text-sm font-bold">规则化投资</div>
            <div className="text-[10px] text-muted-foreground">信号工作台</div>
          </div>
        </div>
        <nav className="flex flex-col gap-1 p-3">
          <NavItems pathname={pathname} vertical />
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* 移动端顶部导航 */}
        <nav className="md:hidden flex items-center gap-1 overflow-x-auto border-b bg-surface px-3 py-2">
          <Landmark className="size-4 text-primary shrink-0 mr-1" />
          <NavItems pathname={pathname} vertical={false} />
        </nav>
        <div className="flex-1">{children}</div>
      </div>
    </div>
  );
}
