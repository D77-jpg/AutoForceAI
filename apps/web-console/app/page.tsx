"use client";

import { useEffect, useState } from 'react';
import { AlertCircle, DatabaseZap, Eye } from 'lucide-react';
import AppSidebar from '@/components/dashboard/AppSidebar';
import TopBar from '@/components/dashboard/TopBar';
import CommandConsole from '@/components/dashboard/CommandConsole';
import InboxPanel from '@/components/dashboard/InboxPanel';
import KpiStrip from '@/components/dashboard/KpiStrip';
import ActivityFeed from '@/components/dashboard/ActivityFeed';
import TaskPipeline from '@/components/dashboard/TaskPipeline';
import AgentRoster from '@/components/dashboard/AgentRoster';
import AgentCard from '@/components/dashboard/AgentCard';
import { fetchDashboardData, INITIAL_DASHBOARD_DATA } from '@/lib/dashboard-api';
import { DASHBOARD_QUICK_COMMANDS } from '@/lib/dashboard-mock';
import type { Agent } from '@/lib/dashboard-types';

export default function HomePage() {
  const [mounted, setMounted] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const [dashboard, setDashboard] = useState(INITIAL_DASHBOARD_DATA);

  useEffect(() => {
    setMounted(true);
    fetchDashboardData().then(setDashboard);
  }, []);

  // Esc 关闭移动端抽屉
  useEffect(() => {
    if (!mobileNavOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileNavOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mobileNavOpen]);

  if (!mounted) return null;

  // 重点员工：三种状态各取一名代表
  const featured = (['running', 'needs_action', 'idle'] as const)
    .map((s) => dashboard.agents.find((a) => a.status === s))
    .filter((a): a is Agent => Boolean(a));

  return (
    <div className="min-h-dvh bg-bg text-text font-sans w-full overflow-x-hidden">
      <a
        href="#dashboard-main"
        className="sr-only focus:not-sr-only fixed top-2 left-2 z-[100] rounded-md bg-accent px-3 py-2 text-sm font-medium text-on-accent"
      >
        跳到主要内容
      </a>
      {/* 背景氛围光（沿用原首页） */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-18%] left-[12%] w-[720px] h-[420px] bg-accent/10 blur-[140px]" />
      </div>

      <AppSidebar
        agentCount={dashboard.agents.length}
        leadCount={dashboard.newLeadCount}
        mobileOpen={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />
      <TopBar status={dashboard.status} onMenuClick={() => setMobileNavOpen(true)} />

      <main id="dashboard-main" className="relative z-10 lg:pl-60 pt-16">
        <div className="max-w-[1600px] mx-auto px-4 md:px-8 py-8 flex flex-col gap-5">
          <div
            role="status"
            className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-separator bg-surface px-4 py-3 text-xs text-text-secondary shadow-card"
          >
            <span className="inline-flex items-center gap-1.5 text-text">
              <DatabaseZap size={14} className="text-success" aria-hidden="true" />
              {dashboard.sources.loading
                ? '正在连接实时数据'
                : `实时数据：${dashboard.sources.liveSections.join('、') || '无'}`}
            </span>
            {dashboard.sources.unavailableSections.length > 0 && (
              <span className="inline-flex items-center gap-1.5 text-warning">
                <AlertCircle size={14} aria-hidden="true" />
                暂不可用：{dashboard.sources.unavailableSections.join('、')}
              </span>
            )}
            <span className="inline-flex items-center gap-1.5">
              <Eye size={14} className="text-accent" aria-hidden="true" />
              功能预览：{dashboard.sources.previewSections.join('、')}
            </span>
          </div>

          {/* 第一行：指挥台 2 : 1 待我处理 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">
            <div className="lg:col-span-2">
              <CommandConsole quickCommands={DASHBOARD_QUICK_COMMANDS} />
            </div>
            <InboxPanel items={dashboard.inbox} />
          </div>

          {/* 核心指标 */}
          <KpiStrip metrics={dashboard.kpis} />

          {/* 第三行：实时动态 1.35 : 1 任务流水线 */}
          <div className="grid grid-cols-1 lg:grid-cols-[1.35fr_1fr] gap-5 items-start">
            <ActivityFeed events={dashboard.activities} />
            <TaskPipeline tasks={dashboard.pipeline} />
          </div>

          {/* 重点员工（三种状态示例卡） */}
          {featured.length > 0 && (
            <section aria-label="重点数字员工" className="flex flex-col gap-3">
              <div className="flex items-baseline gap-2 px-1">
                <h2 className="text-sm font-semibold text-text tracking-tight">重点员工</h2>
                <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[11px] font-medium text-accent">
                  功能预览
                </span>
                <span className="text-xs text-text-tertiary">等待数字员工聚合接口接入</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 items-start">
                {featured.map((agent) => (
                  <AgentCard key={agent.id} agent={agent} />
                ))}
              </div>
            </section>
          )}

          {/* 数字员工花名册 */}
          <AgentRoster agents={dashboard.agents} />
        </div>
      </main>
    </div>
  );
}
