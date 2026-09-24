import Link from 'next/link';
import type { InboxItem } from '@/lib/dashboard-types';

const TONE_DOT: Record<InboxItem['tone'], string> = {
  warning: 'bg-warning',
  accent: 'bg-accent',
  danger: 'bg-danger',
};

/** 待我处理 */
export default function InboxPanel({ items }: { items: InboxItem[] }) {
  return (
    <section aria-label="待我处理" className="bg-surface border border-separator rounded-xl p-5 shadow-card flex flex-col gap-2">
      <div className="flex items-center gap-2 pb-1">
        <h2 className="text-sm font-semibold text-text tracking-tight">待我处理</h2>
        {items.length > 0 && (
          <span className="min-w-[20px] h-5 px-1.5 rounded-full bg-danger/12 text-danger text-[11px] font-semibold tabular-nums flex items-center justify-center">
            {items.length}
          </span>
        )}
        <Link href="/crm" className="ml-auto text-xs text-accent hover:text-accent-hover transition-colors">
          全部
        </Link>
      </div>

      <ul className="flex flex-col">
        {items.map((item, idx) => (
          <li
            key={item.id}
            className={`flex items-center gap-2.5 py-3 ${idx > 0 ? 'border-t border-separator' : ''}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${TONE_DOT[item.tone]}`} aria-hidden="true" />
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <span className="text-[13px] font-medium text-text leading-snug">{item.title}</span>
              <span className="text-xs text-text-secondary truncate">
                {item.agentName} · {item.moduleLabel} · {item.timeAgo}
              </span>
            </div>
            <Link
              href={item.href}
              className="h-7 px-2.5 rounded-md border border-separator bg-surface hover:bg-surface-2 text-xs text-text flex items-center transition-colors shrink-0"
            >
              {item.actionLabel}
            </Link>
          </li>
        ))}
      </ul>
      {items.length === 0 && (
        <p className="py-6 text-center text-sm text-text-tertiary">当前没有需要处理的集成异常</p>
      )}
    </section>
  );
}
