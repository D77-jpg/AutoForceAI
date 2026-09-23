/**
 * 分区主题色的静态 Tailwind 映射（保证类名可被扫描到）。
 * 颜色值全部来自 @autoforce/ui-tokens，暗色模式自动切换。
 */
import type { DepartmentKey } from '@/lib/dashboard-types';

/** 实心图标底（macOS 设置风格） */
export const TINT_BG: Record<DepartmentKey, string> = {
  growth: 'bg-tint-growth',
  revenue: 'bg-tint-revenue',
  decision: 'bg-tint-decision',
  ops: 'bg-tint-ops',
};

/** 文字色 */
export const TINT_TEXT: Record<DepartmentKey, string> = {
  growth: 'text-tint-growth',
  revenue: 'text-tint-revenue',
  decision: 'text-tint-decision',
  ops: 'text-tint-ops',
};

/** 浅底色（图标浅底 / 高亮块） */
export const TINT_SOFT_BG: Record<DepartmentKey, string> = {
  growth: 'bg-tint-growth/12',
  revenue: 'bg-tint-revenue/12',
  decision: 'bg-tint-decision/12',
  ops: 'bg-tint-ops/12',
};
