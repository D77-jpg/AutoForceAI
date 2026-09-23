"use client";

import { useMemo, useState } from 'react';
import Link from 'next/link';
import type { Agent, AgentStatus } from '@/lib/dashboard-types';
import { countByStatus } from '@/lib/dashboard-mock';
import SegmentedControl from './SegmentedControl';
import Sparkline from './Sparkline';
import { TINT_SOFT_BG, TINT_TEXT } from './tints';

type Filter = 'all' | AgentStatus;

const STATUS_META: Record<AgentStatus, { label: string; dot: string }> = {
  running: { label: '运行中', dot: 'bg-success' },
  needs_action: { label: '待审批', dot: 'bg-warning' },
  idle: { label: '待机', dot: 'bg-text-tertiary/60' },
};

const ACTION_LABEL: Record<AgentStatus, string> = {
  running: '日志',
  needs_action: '审核',
  idle: '唤醒',
};

/** 数字员工花名册：语义化 table + 分段控件筛选 */
export default function AgentRoster({ agents }: { agents: Agent[] }) {
  const [filter, setFilter] = useState<Filter>('all');
  const counts = useMemo(() => countByStatus(agents), [agents]);
  const visible = useMemo(
    () => (filter === 'all' ? agents : agents.filter((a) => a.status === filter)),
    [agents, filter]
  );

  return (
    <section aria-label="数字员工花名册" className="bg-surface border border-separator rounded-xl shadow-card p-5 pb-2 flex flex-col">
      <div className="flex items-center gap-3 flex-wrap pb-3">
        <h2 className="text-sm font-semibold text-text tracking-tight">数字员工</h2>
        <SegmentedControl<Filter>
          ariaLabel="按状态筛选数字员工"
          value={filter}
          onChange={setFilter}
          options={[
            { value: 'all', label: '全部', count: counts.all },
            { value: 'running', label: '运行中', count: counts.running },
            { value: 'needs_action', label: '待审批', count: counts.needs_action },
            { value: 'idle', label: '待机', count: counts.idle },
          ]}
        />
        <Link href="/workforce" className="ml-auto text-xs text-accent hover:text-accent-hover transition-colors">
          查看全部
        </Link>
      </div>

      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full min-w-[860px] border-collapse text-left">
          <thead>
            <tr className="border-b border-separator text-[11px] text-text-tertiary tracking-[0.03em]">
              <th scope="col" className="font-medium py-2 pr-4 w-[220px]">员工</th>
              <th scope="col" className="font-medium py-2 pr-4 w-[100px]">状态</th>
              <th scope="col" className="font-medium py-2 pr-4">当前工作</th>
              <th scope="col" className="font-medium py-2 pr-4 w-[80px] text-right">今日产出</th>
              <th scope="col" className="font-medium py-2 pr-4 w-[120px]">7 日趋势</th>
              <th scope="col" className="font-medium py-2 w-[64px]">
                <span className="sr-only">操作</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((agent) => {
              const meta = STATUS_META[agent.status];
              return (
                <tr key={agent.id} className="border-b border-separator last:border-b-0 hover:bg-text/[0.03] transition-colors">
                  <td className="py-2.5 pr-4">
                    <div className="flex items-center gap-2.5">
                      <span
                        aria-hidden="true"
                        className={`w-8 h-8 rounded-lg flex items-center justify-center text-[13px] font-bold shrink-0 ${TINT_SOFT_BG[agent.tint]} ${TINT_TEXT[agent.tint]}`}
                      >
                        {agent.initial}
                      </span>
                      <div className="min-w-0">
                        <div className="text-[13px] font-medium text-text leading-tight">{agent.name}</div>
                        <div className="text-xs text-text-secondary truncate">
                          {agent.role} · {agent.moduleLabel}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="py-2.5 pr-4">
                    <span className="flex items-center gap-1.5 text-xs text-text">
                      <span
                        className={`w-[7px] h-[7px] rounded-full ${meta.dot} ${
                          agent.status === 'running' ? 'status-dot-breathe' : ''
                        }`}
                        aria-hidden="true"
                      />
                      {meta.label}
                    </span>
                  </td>
                  <td className="py-2.5 pr-4">
                    <span className="text-[13px] text-text-secondary block truncate max-w-[320px]">
                      {agent.workSummary}
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 text-right">
                    <span className="text-[13px] text-text tabular-nums">{agent.todayOutput}</span>
                  </td>
                  <td className="py-2.5 pr-4">
                    <Sparkline data={agent.trend} width={110} height={24} strokeWidth={1.6} />
                  </td>
                  <td className="py-2.5">
                    <Link
                      href={agent.status === 'idle' ? '/workforce' : '/workforce/mission'}
                      className="h-7 px-2.5 inline-flex items-center rounded-md border border-separator bg-surface hover:bg-surface-2 text-xs text-text transition-colors"
                    >
                      {ACTION_LABEL[agent.status]}
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {visible.length === 0 && (
        <p className="py-8 text-center text-sm text-text-tertiary">当前筛选下没有数字员工</p>
      )}
    </section>
  );
}
