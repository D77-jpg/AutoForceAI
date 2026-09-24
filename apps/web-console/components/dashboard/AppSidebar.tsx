"use client";

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  Brain,
  Briefcase,
  Compass,
  FlaskConical,
  Gauge,
  Globe,
  MessageSquare,
  Mic2,
  Network,
  PenTool,
  Radar,
  ShieldCheck,
  Target,
  Terminal,
  Users,
  X,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DepartmentNav } from '@/lib/dashboard-types';
import { DASHBOARD_DEPARTMENTS } from '@/lib/dashboard-mock';
import { TINT_BG } from './tints';

/** 模块图标映射（复用现有 lucide 图标） */
const MODULE_ICONS: Record<string, LucideIcon> = {
  pen: PenTool,
  radar: Radar,
  target: Target,
  mic: Mic2,
  message: MessageSquare,
  briefcase: Briefcase,
  activity: Activity,
  shield: ShieldCheck,
  compass: Compass,
  globe: Globe,
  flask: FlaskConical,
  brain: Brain,
  network: Network,
  terminal: Terminal,
};

function ModuleBadge({ badge }: { badge: number | 'dot' }) {
  if (badge === 'dot') {
    return <span className="ml-auto w-1.5 h-1.5 rounded-full bg-danger shrink-0" aria-label="有待办" />;
  }
  return (
    <span className="ml-auto min-w-[18px] h-[18px] px-1 rounded-full bg-accent/12 text-accent text-[10px] font-semibold tabular-nums flex items-center justify-center shrink-0">
      {badge}
    </span>
  );
}

export default function AppSidebar({
  agentCount,
  leadCount,
  mobileOpen,
  onClose,
}: {
  agentCount: number;
  leadCount: number;
  mobileOpen: boolean;
  onClose: () => void;
}) {
  const pathname = usePathname();
  const departments: DepartmentNav[] = DASHBOARD_DEPARTMENTS;

  const body = (
    <nav aria-label="主导航" className="flex flex-col h-full gap-5 px-3 py-4 overflow-y-auto">
      {/* Logo + 产品名 */}
      <div className="flex items-center gap-2.5 px-2 pt-1">
        <Link
          href={process.env.NEXT_PUBLIC_OFFICIAL_SITE_URL || '/'}
          className="w-8 h-8 relative shrink-0 hover:opacity-80 transition-opacity"
        >
          <Image src="/logo.png" alt="GlobalPilot AI" fill className="object-contain" />
        </Link>
        <div className="min-w-0">
          <div className="text-[15px] font-semibold tracking-tight text-text leading-tight truncate">
            GlobalPilot AI
          </div>
          <div className="text-[11px] text-text-tertiary">B2B 增长操作系统</div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="关闭导航"
          className="ml-auto lg:hidden w-8 h-8 rounded-full flex items-center justify-center text-text-secondary hover:bg-text/5 hover:text-text transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {/* 一级入口 */}
      <div className="flex flex-col gap-0.5">
        <Link
          href="/"
          aria-current="page"
          className="flex items-center gap-2.5 h-9 px-2.5 rounded-md bg-accent text-on-accent text-[13px] font-semibold"
        >
          <Gauge size={16} />
          调度中心
        </Link>
        <Link
          href="/workforce"
          className="nav-item h-9 !py-0 text-[13px]"
          onClick={onClose}
        >
          <Users size={16} />
          数字员工
          <span className="ml-auto text-[11px] text-text-tertiary tabular-nums">{agentCount}</span>
        </Link>
      </div>

      {/* 分组模块 */}
      <div className="flex flex-col gap-4 flex-1">
        {departments.map((dept) => (
          <div key={dept.key} className="flex flex-col gap-0.5">
            <span className="text-[11px] font-medium text-text-tertiary px-2.5 pb-1.5 tracking-[0.04em]">
              {dept.title}
            </span>
            {dept.modules.map((mod) => {
              const Icon = MODULE_ICONS[mod.iconKey] || Activity;
              const active = pathname === mod.href && mod.id !== 'scan' && mod.id !== 'research';
              const badge = mod.id === 'leads' && leadCount > 0 ? leadCount : mod.badge;
              return (
                <Link
                  key={mod.id}
                  href={mod.href}
                  onClick={onClose}
                  aria-current={active ? 'page' : undefined}
                  className={cn('nav-item h-8 !py-0 text-[13px]', active && 'active')}
                >
                  <span
                    className={cn(
                      'w-[22px] h-[22px] rounded-[6px] flex items-center justify-center text-on-accent shrink-0',
                      TINT_BG[mod.tint]
                    )}
                  >
                    <Icon size={12} />
                  </span>
                  <span className="truncate">{mod.label}</span>
                  {badge !== undefined && <ModuleBadge badge={badge} />}
                </Link>
              );
            })}
          </div>
        ))}
      </div>
    </nav>
  );

  return (
    <>
      {/* 桌面：固定左侧毛玻璃栏 */}
      <aside className="hidden lg:block fixed left-0 top-0 bottom-0 w-60 z-40 ui-glass !border-b-0 border-r border-separator">
        {body}
      </aside>

      {/* 移动/平板：抽屉 */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-overlay/30" onClick={onClose} aria-hidden="true" />
          <aside className="absolute left-0 top-0 bottom-0 w-64 ui-glass !border-b-0 border-r border-separator animate-slide-in-right">
            {body}
          </aside>
        </div>
      )}
    </>
  );
}
