"use client";

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BarChart3, Gauge, Megaphone, Network, PenTool, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SYSTEM_PRODUCTS } from './system-products';
import { TINT_BG } from './tints';

const BUSINESS_PRODUCTS = SYSTEM_PRODUCTS.filter(({ id }) =>
  ['marketing', 'geo', 'service', 'crm', 'knowledge'].includes(id)
);
const PLATFORM_PRODUCTS = SYSTEM_PRODUCTS.filter(({ id }) =>
  ['workforce', 'digital-human', 'mid-platform', 'ops'].includes(id)
);

const QUICK_LINKS = [
  { href: '/optimize', label: '内容创作', icon: PenTool },
  { href: '/distribution', label: '广告投放', icon: Megaphone },
  { href: '/diagnosis', label: '竞品分析', icon: BarChart3 },
  { href: '/organization', label: '团队管理', icon: Network },
];

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

  const renderProducts = (products: typeof SYSTEM_PRODUCTS) =>
    products.map((product) => {
      const Icon = product.icon;
      const active = pathname === product.href || pathname.startsWith(`${product.href}/`);
      const count = product.id === 'workforce' ? agentCount : product.id === 'service' ? leadCount : null;
      return (
        <Link
          key={product.id}
          href={product.href}
          onClick={onClose}
          aria-current={active ? 'page' : undefined}
          className={cn(
            'flex min-h-14 items-center gap-3 rounded-xl px-2.5 py-2 text-text transition-colors hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent',
            active && 'bg-accent/10 text-accent'
          )}
        >
          <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] text-on-accent', TINT_BG[product.tint])}>
            <Icon size={18} aria-hidden="true" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[13px] font-semibold leading-5">{product.name}</span>
            <span className="block truncate text-[11px] leading-4 text-text-secondary">{product.slogan}</span>
          </span>
          {count !== null && count > 0 && (
            <span className="shrink-0 rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-text-secondary" aria-label={`${count} ${product.id === 'workforce' ? '名数字员工' : '条线索'}`}>
              {count}
            </span>
          )}
          {product.id === 'digital-human' && (
            <span className="shrink-0 text-[10px] text-text-secondary">规划中</span>
          )}
        </Link>
      );
    });

  const body = (
    <nav aria-label="主导航" className="flex h-full flex-col overflow-y-auto px-3 py-4">
      <div className="mb-5 flex items-center gap-2.5 px-2 pt-1">
        <Link href={process.env.NEXT_PUBLIC_OFFICIAL_SITE_URL || '/'} className="relative h-8 w-8 shrink-0 transition-opacity hover:opacity-80">
          <Image src="/logo.png" alt="GlobalPilot AI" fill className="object-contain" />
        </Link>
        <div className="min-w-0">
          <div className="truncate text-[15px] font-semibold leading-tight tracking-tight text-text">GlobalPilot AI</div>
          <div className="text-[11px] text-text-secondary">B2B 增长操作系统</div>
        </div>
        <button type="button" onClick={onClose} aria-label="关闭导航" className="ml-auto flex h-9 w-9 items-center justify-center rounded-full text-text-secondary hover:bg-surface-2 lg:hidden">
          <X size={16} aria-hidden="true" />
        </button>
      </div>

      <Link
        href="/"
        onClick={onClose}
        aria-current={pathname === '/' ? 'page' : undefined}
        className={cn(
          'mb-5 flex min-h-11 items-center gap-3 rounded-xl px-3 text-[13px] font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent',
          pathname === '/' ? 'bg-accent text-on-accent' : 'text-text hover:bg-surface-2'
        )}
      >
        <Gauge size={18} aria-hidden="true" />
        工作台
      </Link>

      <div className="mb-4">
        <h2 className="px-2.5 pb-1 text-[11px] font-semibold tracking-wide text-text-secondary">业务应用</h2>
        <div className="space-y-0.5">{renderProducts(BUSINESS_PRODUCTS)}</div>
      </div>

      <div className="mb-4">
        <h2 className="px-2.5 pb-1 text-[11px] font-semibold tracking-wide text-text-secondary">团队与平台</h2>
        <div className="space-y-0.5">{renderProducts(PLATFORM_PRODUCTS)}</div>
      </div>

      <div className="border-t border-separator pt-3">
        <h2 className="px-2.5 pb-1 text-[11px] font-semibold tracking-wide text-text-secondary">常用功能</h2>
        <div className="grid grid-cols-2 gap-1">
          {QUICK_LINKS.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} onClick={onClose} className="flex min-h-10 items-center gap-1.5 rounded-lg px-2 text-[11px] text-text-secondary transition-colors hover:bg-surface-2 hover:text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              <Icon size={14} className="shrink-0" aria-hidden="true" />
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );

  return (
    <>
      <aside className="ui-glass fixed bottom-0 left-0 top-0 z-40 hidden w-60 border-r border-separator !border-b-0 lg:block">{body}</aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-overlay/30" onClick={onClose} aria-hidden="true" />
          <aside className="ui-glass animate-slide-in-right absolute bottom-0 left-0 top-0 w-64 border-r border-separator !border-b-0">{body}</aside>
        </div>
      )}
    </>
  );
}
