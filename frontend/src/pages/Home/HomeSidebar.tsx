import type { LucideIcon } from "lucide-react";
import {
  Bot,
  ChevronLeft,
  ChevronRight,
  Clock3,
  LayoutDashboard,
  MessageCircleMore,
  Settings2,
  Sparkles,
  UserRound,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

type SidebarItemProps = {
  active?: boolean;
  collapsed: boolean;
  icon: LucideIcon;
  label: string;
  meta?: string;
};

type HomeSidebarProps = {
  collapsed: boolean;
  onToggle: () => void;
};

const navigationItems = [
  { icon: LayoutDashboard, label: "控制台", meta: "AI 舱室" },
  { icon: Sparkles, label: "角色设定", meta: "Live2D" },
  { icon: MessageCircleMore, label: "对话剧本", meta: "12 段" },
  { icon: Settings2, label: "系统设置", meta: "音色 / 动作" },
];

const recentSessions = [
  { label: "早安唤醒流程", meta: "刚刚" },
  { label: "陪伴模式测试", meta: "14:20" },
  { label: "角色口吻微调", meta: "昨天" },
];

function SidebarItem({
  active = false,
  collapsed,
  icon: Icon,
  label,
  meta,
}: SidebarItemProps) {
  return (
    <button
      className={cn(
        "flex w-full items-center gap-3 rounded-2xl border px-3 py-3 text-left transition-all",
        active
          ? "border-sky-300/70 bg-sky-200/80 text-sky-950 shadow-[0_14px_34px_rgba(96,165,250,0.18)]"
          : "border-transparent bg-white/55 text-slate-600 hover:border-sky-200/80 hover:bg-white/80 hover:text-sky-900",
        collapsed && "justify-center px-0"
      )}
      title={label}
      type="button"
    >
      <span
        className={cn(
          "flex size-10 shrink-0 items-center justify-center rounded-2xl border border-sky-100 bg-sky-50 text-sky-500",
          active && "border-sky-300 bg-white text-sky-600"
        )}
      >
        <Icon className="size-4" />
      </span>

      {!collapsed && (
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium text-sm">{label}</span>
          {meta ? (
            <span className="block truncate text-sky-400 text-xs">{meta}</span>
          ) : null}
        </span>
      )}
    </button>
  );
}

export function HomeSidebar({ collapsed, onToggle }: HomeSidebarProps) {
  return (
    <aside
      className={cn(
        "relative z-10 flex shrink-0 flex-col border-sky-200/70 border-r bg-white/72 backdrop-blur-2xl transition-[width] duration-300",
        collapsed ? "w-[84px]" : "w-[280px]"
      )}
    >
      <div className="flex items-center justify-between border-sky-200/70 border-b p-3">
        <div
          className={cn(
            "flex min-w-0 items-center gap-3 overflow-hidden",
            collapsed && "justify-center"
          )}
        >
          <div className="flex size-11 shrink-0 items-center justify-center rounded-[1.25rem] border border-sky-200 bg-sky-100 text-sky-600 shadow-[0_10px_30px_rgba(125,211,252,0.28)]">
            <Bot className="size-5" />
          </div>

          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate font-semibold text-sky-900 text-sm">青空陪伴</p>
              <p className="truncate text-sky-400 text-xs">二次元首页静态预览</p>
            </div>
          )}
        </div>

        <Button
          aria-label={collapsed ? "展开菜单" : "收起菜单"}
          className={cn(
            "rounded-2xl border-sky-200/80 bg-white/85 text-sky-700 hover:bg-sky-50",
            collapsed && "absolute top-3 right-3"
          )}
          onClick={onToggle}
          size="icon-sm"
          type="button"
          variant="outline"
        >
          {collapsed ? (
            <ChevronRight className="size-4" />
          ) : (
            <ChevronLeft className="size-4" />
          )}
        </Button>
      </div>

      <div className="p-3">
        <Button
          className={cn(
            "w-full rounded-2xl bg-sky-400 text-white shadow-[0_12px_30px_rgba(96,165,250,0.24)] hover:bg-sky-500",
            collapsed ? "justify-center px-0" : "justify-start gap-2.5"
          )}
          type="button"
        >
          <Sparkles className="size-4" />
          {!collapsed && <span>新建对话场景</span>}
        </Button>
      </div>

      <ScrollArea className="flex-1 px-3 pb-3">
        <div className="space-y-6 pb-4">
          <section className="space-y-2">
            {!collapsed && (
              <p className="px-1 font-medium text-[11px] tracking-[0.24em] text-sky-400 uppercase">
                Navigation
              </p>
            )}
            {navigationItems.map((item, index) => (
              <SidebarItem
                active={index === 0}
                collapsed={collapsed}
                icon={item.icon}
                key={item.label}
                label={item.label}
                meta={item.meta}
              />
            ))}
          </section>

          <section className="space-y-2">
            {!collapsed && (
              <p className="px-1 font-medium text-[11px] tracking-[0.24em] text-sky-400 uppercase">
                Recent
              </p>
            )}

            {recentSessions.map((session) => (
              <button
                className={cn(
                  "flex w-full items-center gap-3 rounded-2xl border border-transparent px-3 py-3 text-left text-slate-600 transition-all hover:border-sky-200/80 hover:bg-white/85 hover:text-sky-900",
                  collapsed && "justify-center px-0"
                )}
                key={session.label}
                title={session.label}
                type="button"
              >
                <span className="flex size-10 shrink-0 items-center justify-center rounded-2xl border border-sky-100 bg-sky-50 text-sky-500">
                  <Clock3 className="size-4" />
                </span>
                {!collapsed && (
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm">{session.label}</span>
                    <span className="block truncate text-sky-400 text-xs">
                      {session.meta}
                    </span>
                  </span>
                )}
              </button>
            ))}
          </section>
        </div>
      </ScrollArea>

      <div className="border-sky-200/70 border-t p-3">
        <div
          className={cn(
            "flex items-center gap-3 rounded-2xl border border-sky-100 bg-white/75 p-3",
            collapsed && "justify-center px-0"
          )}
        >
          <div className="flex size-10 shrink-0 items-center justify-center rounded-2xl bg-sky-100 text-sky-600">
            <UserRound className="size-4" />
          </div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium text-sky-900 text-sm">Producer</p>
              <p className="truncate text-sky-400 text-xs">Aozora Visual Mode</p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
