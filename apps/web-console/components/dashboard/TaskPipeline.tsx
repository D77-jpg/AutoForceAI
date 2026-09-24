import Link from 'next/link';
import type { PipelineTask } from '@/lib/dashboard-types';

const STATUS_STYLE: Record<PipelineTask['status'], { tag: string; bar: string }> = {
  running: { tag: 'bg-accent/10 text-accent', bar: 'bg-accent' },
  review: { tag: 'bg-warning/12 text-warning', bar: 'bg-warning' },
  queued: { tag: 'bg-surface-2 text-text-secondary', bar: 'bg-text-tertiary/50' },
  complete: { tag: 'bg-success/10 text-success', bar: 'bg-success' },
};

/** CRM 集成流水线 */
export default function TaskPipeline({ tasks }: { tasks: PipelineTask[] }) {
  return (
    <section aria-label="CRM 集成流水线" className="bg-surface border border-separator rounded-xl p-5 shadow-card flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold text-text tracking-tight">CRM 集成流水线</h2>
        <Link href="/crm" className="ml-auto text-xs text-accent hover:text-accent-hover transition-colors">
          集成门户
        </Link>
      </div>

      {tasks.map((task) => {
        const style = STATUS_STYLE[task.status];
        return (
          <div key={task.id} className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <span className="text-[13px] font-medium text-text">{task.name}</span>
              <span className={`ml-auto text-[11px] font-medium px-2 py-0.5 rounded-full ${style.tag}`}>
                {task.statusLabel}
              </span>
            </div>
            <div
              className="h-1 rounded-full bg-text/10 overflow-hidden"
              role="progressbar"
              aria-valuenow={task.progress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${task.name} 进度`}
            >
              <div
                className={`h-full rounded-full transition-[width] duration-base ease-apple ${style.bar}`}
                style={{ width: `${task.progress}%` }}
              />
            </div>
            <div className="flex text-xs text-text-secondary">
              <span>
                {task.agentName} · {task.detail}
              </span>
              <span className="ml-auto tabular-nums">
                {task.status === 'queued' ? '—' : `${task.progress}%`}
              </span>
            </div>
          </div>
        );
      })}
      {tasks.length === 0 && (
        <p className="py-6 text-center text-sm text-text-tertiary">CRM 队列暂不可用</p>
      )}
    </section>
  );
}
