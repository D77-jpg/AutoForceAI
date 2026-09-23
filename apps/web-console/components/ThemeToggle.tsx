"use client";
import { Moon, Sun } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * 深浅色切换按钮：无状态组件——直接读写 <html data-theme> 并持久化到 localStorage。
 * 两个图标同时渲染，显隐由 globals.css 依据 data-theme 控制，
 * 避免 useState/useEffect 带来的 hydration 不一致与 lint 问题。
 */
export default function ThemeToggle({ className }: { className?: string }) {
  const toggle = () => {
    const cur = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try {
      window.localStorage.setItem('theme', next);
    } catch {
      /* 忽略隐私模式下的写入失败 */
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="切换深浅色模式"
      title="切换深浅色模式"
      className={cn(
        'relative w-9 h-9 rounded-full bg-text/5 hover:bg-text/10 flex items-center justify-center text-text-secondary hover:text-text transition-colors',
        className
      )}
    >
      {/* 深色模式下显示太阳（点击切浅色），浅色模式下显示月亮 */}
      <Sun size={16} className="theme-icon-sun" />
      <Moon size={16} className="theme-icon-moon" />
    </button>
  );
}
