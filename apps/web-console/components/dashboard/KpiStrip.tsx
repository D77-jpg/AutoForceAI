import type { KpiMetric } from '@/lib/dashboard-types';
import Sparkline from './Sparkline';

/** 核心指标：一个整体卡片内分四格，格间细分隔线 */
export default function KpiStrip({ metrics }: { metrics: KpiMetric[] }) {
  return (
    <section
      aria-label="核心指标"
      className="bg-surface border border-separator rounded-xl shadow-card grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4"
    >
      {metrics.map((m, idx) => (
        <div
          key={m.id}
          className={`p-5 flex flex-col gap-1.5 border-separator ${
            idx > 0 ? 'border-t sm:border-t-0' : ''
          } ${
            // 4 列时：2–4 格左分隔线；2 列时（sm-xl）：偶数格左分隔线，3、4 格上分隔线
            idx > 0 ? 'xl:border-l' : ''
          } ${idx % 2 === 1 ? 'sm:border-l' : ''} ${idx >= 2 ? 'sm:border-t xl:border-t-0' : ''}`}
        >
          <span className="text-xs text-text-secondary">{m.label}</span>
          <div className="flex items-end gap-2.5">
            <span className="text-[28px] leading-none font-bold tracking-tight text-text tabular-nums">
              {m.value}
              {m.suffix && (
                <span className="text-base text-text-tertiary font-normal">{m.suffix}</span>
              )}
            </span>
            {m.delta && (
              <span
                className={`text-xs font-medium tabular-nums ${
                  m.delta.direction === 'up' ? 'text-success' : 'text-danger'
                }`}
              >
                {m.delta.value}
              </span>
            )}
            {m.spark && (
              <Sparkline
                data={m.spark}
                className={`ml-auto ${
                  m.delta?.direction === 'down' ? 'text-accent' : 'text-success'
                }`}
              />
            )}
          </div>

          {/* 三段状态条（仅在线数字员工） */}
          {m.segments && (
            <div className="flex gap-[3px] h-1.5 mt-1" role="img" aria-label={m.caption}>
              <span className="rounded-full bg-success" style={{ flexGrow: m.segments.running }} />
              <span className="rounded-full bg-warning" style={{ flexGrow: m.segments.needsAction }} />
              <span className="rounded-full bg-text-tertiary/40" style={{ flexGrow: m.segments.idle }} />
            </div>
          )}

          <span className="text-xs text-text-tertiary">{m.caption}</span>
        </div>
      ))}
    </section>
  );
}
