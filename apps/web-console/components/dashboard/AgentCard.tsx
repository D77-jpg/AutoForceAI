"use client";

import { MoreHorizontal, Play } from 'lucide-react';
import Link from 'next/link';
import type { Agent } from '@/lib/dashboard-types';
import Sparkline from './Sparkline';
import { TINT_SOFT_BG, TINT_TEXT } from './tints';

/**
 * AgentCard — 可复用数字员工卡片，由 agent.status 决定三种形态：
 *  running       当前任务 + 进度 + 双指标 + 趋势线；按钮：查看日志 / 追加任务
 *  needs_action  橙色提示区（等待时长 + 待处理事项）；按钮：全部通过 / 去审核
 *  idle          降低饱和度；上次/下次运行 + 快捷任务胶囊；按钮：唤醒
 */
export default function AgentCard({ agent }: { agent: Agent }) {
  const { status } = agent;

  const shellBase =
    'rounded-xl p-[18px] flex flex-col gap-4 transition-all duration-base ease-apple hover:-translate-y-0.5 hover:shadow-popover';
  const shellByStatus: Record<Agent['status'], string> = {
    running: 'bg-surface border border-separator shadow-card',
    needs_action: 'bg-surface border border-warning/40 shadow-card',
    idle: 'bg-surface-2/60 border border-dashed border-separator',
  };

  return (
    <article className={`${shellBase} ${shellByStatus[status]}`} aria-label={`数字员工 ${agent.name}`}>
      {/* 头部：头像 + 名字 + 角色 */}
      <div className="flex items-center gap-2.5">
        <div className="relative w-[38px] h-[38px] shrink-0">
          <span
            aria-hidden="true"
            className={`w-[38px] h-[38px] rounded-[10px] flex items-center justify-center text-[15px] font-bold ${TINT_SOFT_BG[agent.tint]} ${TINT_TEXT[agent.tint]} ${
              status === 'idle' ? 'opacity-70 saturate-50' : ''
            }`}
          >
            {agent.initial}
          </span>
          <span
            aria-hidden="true"
            className={`absolute -right-0.5 -bottom-0.5 w-2.5 h-2.5 rounded-full border-2 border-surface ${
              status === 'running'
                ? 'bg-success status-dot-breathe'
                : status === 'needs_action'
                  ? 'bg-warning'
                  : 'bg-text-tertiary/60'
            }`}
          />
        </div>
        <div className="min-w-0">
          <div className={`text-sm font-bold leading-tight ${status === 'idle' ? 'text-text-secondary' : 'text-text'}`}>
            {agent.name}
          </div>
          <div className="text-xs text-text-secondary truncate">
            {agent.role} · {agent.moduleLabel}
          </div>
        </div>
        <button
          type="button"
          aria-label={`${agent.name} 更多操作`}
          title="功能预览，更多操作尚未接入"
          disabled
          className="ml-auto w-[30px] h-[30px] rounded-md flex items-center justify-center text-text-tertiary opacity-50 cursor-not-allowed"
        >
          <MoreHorizontal size={16} />
        </button>
      </div>

      {/* ── running：当前任务 ── */}
      {status === 'running' && agent.currentTask && (
        <div className="flex flex-col gap-2 p-3 rounded-lg bg-bg/60 border border-separator">
          <div className="flex items-center text-xs text-text-secondary">
            <span>当前任务</span>
            <span className="ml-auto tabular-nums">
              {agent.currentTask.stepDone}/{agent.currentTask.stepTotal}
            </span>
          </div>
          <span className="text-[13px] font-medium text-text leading-snug">{agent.currentTask.name}</span>
          <div
            className="h-1 rounded-full bg-text/10 overflow-hidden"
            role="progressbar"
            aria-valuenow={agent.currentTask.progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`${agent.currentTask.name} 进度`}
          >
            <div className="h-full rounded-full bg-success" style={{ width: `${agent.currentTask.progress}%` }} />
          </div>
        </div>
      )}

      {/* ── needs_action：待处理提示区 ── */}
      {status === 'needs_action' && agent.pending && (
        <div className="flex flex-col gap-1.5 p-3 rounded-lg bg-warning/10">
          <div className="flex items-center gap-1.5 text-xs font-medium text-warning">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5l3 2" />
            </svg>
            已等待 {agent.pending.waitMinutes} 分钟
          </div>
          <span className="text-[13px] font-medium text-text leading-snug">{agent.pending.title}</span>
          {agent.pending.note && <span className="text-xs text-text-secondary">{agent.pending.note}</span>}
        </div>
      )}

      {/* ── idle：待机信息 + 快捷任务 ── */}
      {status === 'idle' && agent.idleInfo && (
        <>
          <div className="flex flex-col gap-1">
            <span className="text-[13px] text-text-secondary">待机中，{agent.idleInfo.lastRun}</span>
            <span className="text-xs text-text-tertiary">{agent.idleInfo.nextPlan}</span>
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-xs text-text-tertiary">可以让他做</span>
            <div className="flex flex-wrap gap-1.5">
              {agent.idleInfo.suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  disabled
                  title="任务派发接口尚未接入"
                  className="h-7 px-2.5 rounded-pill border border-separator bg-surface text-xs text-text-secondary opacity-55 cursor-not-allowed"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {/* 双指标（running / needs_action） */}
      {status !== 'idle' && (
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-0.5">
            <span className="text-xs text-text-secondary">今日产出</span>
            <span className="text-[22px] leading-none font-bold tracking-tight text-text tabular-nums">
              {agent.outputValue}
              <span className="text-xs text-text-tertiary font-normal"> {agent.outputUnit}</span>
            </span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-xs text-text-secondary">采纳率</span>
            <span className="text-[22px] leading-none font-bold tracking-tight text-text tabular-nums">
              {agent.adoptionRate}
              <span className="text-xs text-text-tertiary font-normal">%</span>
            </span>
          </div>
        </div>
      )}

      {/* 趋势线（running） */}
      {status === 'running' && (
        <Sparkline data={agent.trend} width={270} height={36} className="text-success w-full" />
      )}

      {/* 操作按钮 */}
      {status === 'running' && (
        <div className="flex gap-2">
          <Link
            href="/workforce/mission"
            className="flex-1 h-[34px] rounded-md border border-separator bg-surface hover:bg-surface-2 text-xs text-text transition-colors"
          >
            <span className="h-full flex items-center justify-center">查看任务</span>
          </Link>
          <button
            type="button"
            disabled
            title="追加任务接口尚未接入"
            className="flex-1 h-[34px] rounded-md bg-text text-bg text-xs font-medium opacity-40 cursor-not-allowed"
          >
            追加任务待接入
          </button>
        </div>
      )}
      {status === 'needs_action' && (
        <div className="flex gap-2">
          <button
            type="button"
            disabled
            title="批量审批接口尚未接入"
            className="flex-1 h-[34px] rounded-md border border-separator bg-surface text-xs text-text opacity-50 cursor-not-allowed"
          >
            批量审批待接入
          </button>
          <Link
            href="/workforce/mission"
            className="flex-1 h-[34px] rounded-md bg-accent hover:bg-accent-hover text-on-accent text-xs font-medium transition-colors"
          >
            <span className="h-full flex items-center justify-center">去审核</span>
          </Link>
        </div>
      )}
      {status === 'idle' && (
        <Link
          href="/workforce"
          className="h-[34px] rounded-md border border-separator bg-surface hover:bg-surface-2 text-xs text-text flex items-center justify-center gap-1.5 transition-colors"
        >
          <Play size={13} />
          去编排
        </Link>
      )}
    </article>
  );
}
