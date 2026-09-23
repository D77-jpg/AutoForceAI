"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowUpRight,
  Bell,
  ChevronRight,
  LayoutGrid,
  LogOut,
  Menu,
  Search,
  Settings,
  User as UserIcon,
} from 'lucide-react';
import ThemeToggle from '../ThemeToggle';
import { useAuth } from '@/contexts/AuthContext';
import type { SystemStatus } from '@/lib/dashboard-types';
import { TINT_BG } from './tints';

/** 产品矩阵下拉数据（沿用原首页 mega menu 内容） */
import { SYSTEM_PRODUCTS } from './system-products';

const IconButton = ({
  icon: Icon,
  onClick,
  badge,
  label,
}: {
  icon: any;
  onClick?: () => void;
  badge?: boolean;
  label: string;
}) => (
  <button
    type="button"
    onClick={onClick}
    aria-label={label}
    title={label}
    className="relative w-9 h-9 rounded-full bg-text/5 hover:bg-text/10 flex items-center justify-center text-text-secondary hover:text-text transition-colors"
  >
    <Icon size={16} />
    {badge && <span className="absolute top-0.5 right-0.5 w-2 h-2 bg-danger rounded-full" />}
  </button>
);

export default function TopBar({
  status,
  onMenuClick,
}: {
  status: SystemStatus;
  onMenuClick: () => void;
}) {
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showProductMenu, setShowProductMenu] = useState(false);

  // Esc 关闭产品矩阵菜单
  useEffect(() => {
    if (!showProductMenu) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowProductMenu(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [showProductMenu]);

  // 组件仅在客户端 mounted 后由父级渲染，读取 navigator 安全
  const isMac =
    typeof window !== 'undefined' && /Mac|iPhone|iPad/i.test(window.navigator.userAgent);

  return (
    <>
      {showProductMenu && (
        <div
          className="fixed inset-0 top-16 z-40 bg-overlay/30"
          onClick={() => setShowProductMenu(false)}
          aria-hidden="true"
        />
      )}

      <header className="fixed top-0 left-0 right-0 lg:left-60 z-50 h-16 border-b border-separator bg-bg/70 backdrop-blur-2xl pl-4 pr-6 flex justify-between items-center gap-4">
        {/* 左：菜单（移动）+ 页面标题 + 系统状态 */}
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={onMenuClick}
            aria-label="打开导航"
            className="lg:hidden w-9 h-9 rounded-full bg-text/5 hover:bg-text/10 flex items-center justify-center text-text-secondary hover:text-text transition-colors shrink-0"
          >
            <Menu size={16} />
          </button>
          <div className="min-w-0">
            <h1 className="text-[17px] font-semibold tracking-tight text-text leading-tight truncate">
              数字人调度中心
            </h1>
            <p className="hidden sm:flex items-center gap-1.5 text-[11px] text-text-secondary">
              <span className="w-1.5 h-1.5 rounded-full bg-success status-dot-breathe shrink-0" />
              全天候运行中
              <span className="text-text-tertiary">·</span>
              健康度 <span className="text-text font-medium tabular-nums">{status.healthPercent}%</span>
              <span className="text-text-tertiary">·</span>
              在线 <span className="text-text font-medium tabular-nums">{status.onlineAgents}</span> 名
            </p>
          </div>
        </div>

        {/* 右：搜索 / 产品矩阵 / 主题 / 通知 / 设置 / 用户 */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden lg:flex items-center bg-surface border border-separator rounded-full h-9 px-4 w-[280px] focus-within:border-accent/40 focus-within:bg-surface-2 transition-all">
            <Search size={14} className="text-text-secondary mr-2 shrink-0" />
            <input
              type="text"
              placeholder="呼叫数字员工 / 搜索业务数据..."
              aria-label="搜索"
              className="bg-transparent border-none outline-none text-xs text-text placeholder:text-text-tertiary flex-1 min-w-0"
            />
            <span className="bg-text/10 px-1.5 py-0.5 rounded border border-separator text-[10px] text-text-tertiary font-mono shrink-0">
              {isMac ? '⌘ K' : 'Ctrl K'}
            </span>
          </div>

          {/* 产品矩阵：保留为下拉面板（理由：侧边栏仅覆盖 14 个业务模块，
              AI 电商 / CRM / 中台等产品级入口仍需可达） */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowProductMenu((v) => !v)}
              aria-label="产品矩阵"
              aria-expanded={showProductMenu}
              title="产品矩阵"
              className="relative w-9 h-9 rounded-full bg-text/5 hover:bg-text/10 flex items-center justify-center text-text-secondary hover:text-text transition-colors"
            >
              <LayoutGrid size={16} />
            </button>
            {showProductMenu && (
              <div className="absolute top-full right-0 mt-2 w-[720px] max-w-[calc(100vw-2rem)] menu-glass rounded-2xl p-5 z-50">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {SYSTEM_PRODUCTS.map((prod) => (
                    <Link
                      key={prod.id}
                      href={prod.href}
                      onClick={() => setShowProductMenu(false)}
                      className="flex items-start gap-3.5 p-3.5 rounded-xl hover:bg-text/5 border border-transparent transition-all group/card"
                    >
                      <div
                        className={`w-10 h-10 rounded-[22%] flex items-center justify-center ${TINT_BG[prod.tint]} text-on-accent group-hover/card:scale-105 transition-transform duration-300 shrink-0`}
                      >
                        <prod.icon size={20} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start mb-0.5 gap-2">
                          <h4 className="text-sm font-semibold text-text">{prod.name}</h4>
                          <span className="text-[10px] font-medium bg-surface-2 px-1.5 py-0.5 rounded-full text-text-secondary shrink-0 tabular-nums">
                            {prod.keyData}
                          </span>
                        </div>
                        <p className="text-[11px] font-medium text-text-secondary mb-0.5">{prod.slogan}</p>
                        <p className="text-xs text-text-secondary leading-relaxed line-clamp-2">{prod.desc}</p>
                      </div>
                    </Link>
                  ))}
                </div>
                <div className="mt-3 pt-3 border-t border-separator flex justify-between items-center px-1">
                  <span className="text-xs text-text-tertiary">GlobalPilot AI © 2026</span>
                  <Link
                    href="/solution"
                    onClick={() => setShowProductMenu(false)}
                    className="text-xs text-accent hover:text-accent-hover flex items-center gap-1 group/link"
                  >
                    查看全景图
                    <ArrowUpRight
                      size={12}
                      className="group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform"
                    />
                  </Link>
                </div>
              </div>
            )}
          </div>

          <ThemeToggle />
          <IconButton icon={Bell} badge label="通知" />
          <IconButton icon={Settings} label="设置" />

          <div
            className="flex items-center gap-3 pl-3 border-l border-separator cursor-pointer group relative"
            onClick={() => setShowUserMenu(!showUserMenu)}
          >
            <div className="text-right hidden sm:block">
              <div className="text-xs font-bold text-text">{user?.nickname || user?.username || 'GUEST'}</div>
              <div className="text-[10px] text-text-secondary uppercase">
                {user?.role === 'admin' ? '系统管理员' : user?.role === 'enterprise_admin' ? '企业管理员' : '普通成员'}
              </div>
            </div>
            <div className="w-9 h-9 rounded-full bg-surface-2 overflow-hidden relative">
              {user?.avatar || user?.headimgurl ? (
                <img src={user?.headimgurl || user?.avatar} alt="头像" className="w-full h-full object-cover" />
              ) : (
                <UserIcon className="w-5 h-5 m-2 text-text-secondary" />
              )}
            </div>

            {showUserMenu && (
              <div className="absolute top-full right-0 mt-2 w-56 bg-surface border border-separator rounded-2xl shadow-popover overflow-hidden animate-fade-in-up z-50">
                <div className="p-3 border-b border-separator">
                  <p className="text-xs text-text-secondary">当前账号</p>
                  <div className="text-sm font-bold text-text truncate flex items-center gap-1">
                    {user?.nickname || user?.username || 'Guest'}
                    {user?.org_name && (
                      <>
                        <span className="text-text-secondary mx-0.5">|</span>
                        <span className="text-accent font-normal truncate max-w-[100px]" title={user.org_name}>
                          {user.org_name}
                        </span>
                      </>
                    )}
                  </div>
                </div>
                <div className="p-1">
                  <Link href="/settings/profile" className="flex items-center gap-2 px-3 py-2 text-xs text-text hover:bg-text/5 rounded-lg transition-colors">
                    <UserIcon size={14} /> 用户中心
                  </Link>
                  <Link href="/ops" className="flex items-center gap-2 px-3 py-2 text-xs text-text hover:bg-text/5 rounded-lg transition-colors">
                    <Settings size={14} /> 系统配置
                  </Link>
                  <div className="h-px bg-text/5 my-1" />
                  <button
                    type="button"
                    onClick={logout}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-danger hover:bg-danger/10 rounded-lg transition-colors text-left"
                  >
                    <LogOut size={14} /> 退出登录
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>
    </>
  );
}
