import Link from 'next/link';
import type { ActivityEvent } from '@/lib/dashboard-types';
import { TINT_SOFT_BG, TINT_TEXT } from './tints';

/**
 * CRM 同步动态：新事件从顶部淡入（animate-fade-in-up + key 变化触发）。
 * aria-live="polite" 供屏幕阅读器感知新事件。
 */
export default function ActivityFeed({ events }: { events: ActivityEvent[] }) {
  return (
    <section aria-label="CRM 同步动态" className="bg-surface border border-separator rounded-xl p-5 shadow-card flex flex-col gap-2">
      <div className="flex items-center gap-2 pb-1">
        <h2 className="text-sm font-semibold text-text tracking-tight">CRM 同步动态</h2>
        <span className="flex items-center gap-1.5 text-[11px] font-medium text-success">
          <span className="w-1.5 h-1.5 rounded-full bg-success status-dot-breathe" />
          实时
        </span>
        <Link href="/crm" className="ml-auto text-xs text-accent hover:text-accent-hover transition-colors">
          集成门户
        </Link>
      </div>

      <ul aria-live="polite" className="flex flex-col">
        {events.map((ev, idx) => (
          <li
            key={ev.id}
            className={`grid grid-cols-[44px_26px_minmax(0,1fr)] items-center gap-2.5 py-2.5 animate-fade-in-up ${
              idx > 0 ? 'border-t border-separator' : ''
            }`}
            style={{ animationDelay: `${idx * 40}ms` }}
          >
            <span className="text-xs text-text-tertiary tabular-nums">{ev.time}</span>
            <span
              aria-hidden="true"
              className={`w-[26px] h-[26px] rounded-[7px] flex items-center justify-center text-[11px] font-bold ${TINT_SOFT_BG[ev.tint]} ${TINT_TEXT[ev.tint]}`}
            >
              {ev.agentInitial}
            </span>
            <span className="text-[13px] text-text-secondary leading-snug">
              <b className="text-text font-semibold">{ev.agentName}</b> {ev.description}
            </span>
          </li>
        ))}
      </ul>
      {events.length === 0 && (
        <p className="py-6 text-center text-sm text-text-tertiary">暂无最近同步记录</p>
      )}
    </section>
  );
}
