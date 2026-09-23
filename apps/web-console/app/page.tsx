"use client";

import { useEffect, useState } from 'react';
import AppSidebar from '@/components/dashboard/AppSidebar';
import TopBar from '@/components/dashboard/TopBar';
import CommandConsole from '@/components/dashboard/CommandConsole';
import InboxPanel from '@/components/dashboard/InboxPanel';
import KpiStrip from '@/components/dashboard/KpiStrip';
import ActivityFeed from '@/components/dashboard/ActivityFeed';
import TaskPipeline from '@/components/dashboard/TaskPipeline';
import AgentRoster from '@/components/dashboard/AgentRoster';
import AgentCard from '@/components/dashboard/AgentCard';
import {
  fetchActivities,
  fetchAgents,
  fetchInbox,
  fetchKpis,
  fetchPipeline,
  fetchSystemStatus,
} from '@/lib/dashboard-api';
import { MOCK_QUICK_COMMANDS } from '@/lib/dashboard-mock';
import type {
  ActivityEvent,
  Agent,
  InboxItem,
  KpiMetric,
  PipelineTask,
  SystemStatus,
} from '@/lib/dashboard-types';

export default function HomePage() {
  const [mounted, setMounted] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const [status, setStatus] = useState<SystemStatus>({ healthPercent: 0, onlineAgents: 0, totalAgents: 0 });
  const [inbox, setInbox] = useState<InboxItem[]>([]);
  const [kpis, setKpis] = useState<KpiMetric[]>([]);
  const [activities, setActivities] = useState<ActivityEvent[]>([]);
  const [pipeline, setPipeline] = useState<PipelineTask[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    setMounted(true);
    // 数据接入层：有接口走接口，没有走 mock（见 lib/dashboard-api.ts）
    fetchSystemStatus().then(setStatus);
    fetchInbox().then(setInbox);
    fetchKpis().then(setKpis);
    fetchActivities().then(setActivities);
    fetchPipeline().then(setPipeline);
    fetchAgents().then(setAgents);
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
    .map((s) => agents.find((a) => a.status === s))
    .filter((a): a is Agent => Boolean(a));

  return (
    <div className="min-h-screen bg-bg text-text font-sans w-full overflow-x-hidden">
      {/* 背景氛围光（沿用原首页） */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-18%] left-[12%] w-[720px] h-[420px] bg-accent/10 blur-[140px]" />
      </div>

      <AppSidebar
        agentCount={status.onlineAgents}
        mobileOpen={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />
      <TopBar status={status} onMenuClick={() => setMobileNavOpen(true)} />

      <main className="relative z-10 lg:pl-60 pt-16">
        <div className="max-w-[1600px] mx-auto px-4 md:px-8 py-8 flex flex-col gap-5">
          {/* 第一行：指挥台 2 : 1 待我处理 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">
            <div className="lg:col-span-2">
              <CommandConsole quickCommands={MOCK_QUICK_COMMANDS} />
            </div>
            <InboxPanel items={inbox} />
          </div>

          {/* 核心指标 */}
          <KpiStrip metrics={kpis} />

          {/* 第三行：实时动态 1.35 : 1 任务流水线 */}
          <div className="grid grid-cols-1 lg:grid-cols-[1.35fr_1fr] gap-5 items-start">
            <ActivityFeed events={activities} />
            <TaskPipeline tasks={pipeline} />
          </div>

          {/* 重点员工（三种状态示例卡） */}
          {featured.length > 0 && (
            <section aria-label="重点数字员工" className="flex flex-col gap-3">
              <div className="flex items-baseline gap-2 px-1">
                <h2 className="text-sm font-semibold text-text tracking-tight">重点员工</h2>
                <span className="text-xs text-text-tertiary">正在运行、需要处理与待机的代表</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 items-start">
                {featured.map((agent) => (
                  <AgentCard key={agent.id} agent={agent} />
                ))}
              </div>
            </section>
          )}

          {/* 数字员工花名册 */}
          <AgentRoster agents={agents} />
        </div>
      </main>
    </div>
  );
}
