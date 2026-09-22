"use client";
import React, { useState, useEffect } from 'react';
import {
  Terminal, Cpu, HardDrive, Activity, Users, Building2,
  RefreshCw, AlertTriangle, ArrowRight, BrainCircuit, Bot
} from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

interface SystemStatus {
  status: string;
  cpu_usage: number;
  memory_usage: { total: number; used: number; percent: number };
  system_info: { platform: string; release: string; python_version: string };
  resources: { active_models: number; active_users: number; queued_jobs: number };
}

const QUICK_ACTIONS = [
  { label: '用户管理', href: '/ops/users', icon: Users, desc: '管理系统账号权限' },
  { label: '企业管理', href: '/ops/enterprises', icon: Building2, desc: '多租户组织架构' },
  { label: '模型纳管', href: '/platform/models', icon: BrainCircuit, desc: '配置 LLM 服务商' },
  { label: '技能工具箱', href: '/platform/skills', icon: Bot, desc: 'Agent 能力中心' },
];

function formatGB(bytes: number) { return (bytes / (1024 ** 3)).toFixed(1); }

export default function OpsPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [sys, setSys] = useState<SystemStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  const fetchStatus = async () => {
    try {
      const res = await fetch(API_URL + '/api/v1/monitor/system');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      setSys(data);
      setLoadError(null);
      setLastUpdated(new Date().toLocaleTimeString('zh-CN'));
    } catch (e) {
      setLoadError(e.message || '无法连接后端');
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const stats = sys ? [
    { label: 'CPU 使用率', value: sys.cpu_usage.toFixed(0) + '%', status: sys.cpu_usage > 85 ? 'warning' : 'normal', icon: Cpu, color: 'text-accent', bg: 'bg-accent/10', border: 'border-accent/20' },
    { label: '内存占用', value: formatGB(sys.memory_usage.used) + ' GB', total: formatGB(sys.memory_usage.total) + ' GB', status: sys.memory_usage.percent > 85 ? 'warning' : 'normal', icon: HardDrive, color: 'text-warning', bg: 'bg-warning/10', border: 'border-warning/20' },
    { label: '活跃用户', value: String(sys.resources.active_users), sub: sys.resources.active_models + ' 个模型在线', status: 'normal', icon: Users, color: 'text-success', bg: 'bg-success/10', border: 'border-success/20' },
    { label: 'RPA 队列', value: String(sys.resources.queued_jobs), sub: '待执行任务', status: 'normal', icon: Bot, color: 'text-accent', bg: 'bg-accent/10', border: 'border-accent/20' },
  ] : [];

  return (
    <div className="h-full flex flex-col bg-bg overflow-hidden">
      <div className="flex-none p-6 border-b border-separator">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-[28px] font-semibold tracking-tight text-white flex items-center gap-3">
              <Terminal className="text-accent" />
              运维控制台
            </h1>
            <p className="text-sm text-text-secondary mt-1">
              系统运行状态概览与快捷操作中心
              {sys && <span className="ml-2 text-text-secondary">· {sys.system_info.platform} {sys.system_info.release} · Python {sys.system_info.python_version}</span>}
            </p>
          </div>
          <div className="flex items-center gap-3">
             {loadError ? (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-danger/10 border border-danger/20 rounded-full">
                   <div className="w-2 h-2 rounded-full bg-danger"></div>
                   <span className="text-xs text-danger font-medium">后端连接异常</span>
                </div>
             ) : (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-success/10 border border-success/20 rounded-full">
                   <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
                   <span className="text-xs text-success font-medium">系统运行正常</span>
                </div>
             )}
             <button onClick={fetchStatus} className="p-1.5 text-text-secondary hover:text-white transition-colors" title="刷新">
                <RefreshCw size={14} />
             </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {sys ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, idx) => (
            <div key={idx} className="p-5 rounded-xl border border-separator bg-surface relative overflow-hidden group hover:bg-surface-2 transition-all">
              <div className="flex justify-between items-start mb-4">
                <div className="p-2 rounded-xl bg-text/5">
                  <stat.icon size={20} className={stat.color} />
                </div>
                {stat.status === 'warning' && <AlertTriangle size={16} className="text-warning" />}
              </div>
              <div className="space-y-1">
                <p className="text-[11px] text-text-secondary uppercase font-semibold tracking-[0.12em]">{stat.label}</p>
                <div className="flex items-end gap-2">
                  <span className="text-[26px] font-semibold tracking-tight text-white">{stat.value}</span>
                  {stat.total && <span className="text-xs text-text-secondary mb-1">/ {stat.total}</span>}
                  {stat.sub && <span className="text-xs text-text-secondary mb-1">{stat.sub}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
        ) : (
          <div className="flex items-center justify-center h-40 text-text-secondary gap-2">
            {loadError ? ('无法加载系统状态：' + loadError) : (
              <><RefreshCw size={16} className="animate-spin" /> 正在加载系统状态...</>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 gap-6">
           <div className="bg-surface border border-separator rounded-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Activity size={18} className="text-accent"/>
                  快捷操作
                </h3>
                {lastUpdated && <span className="text-xs text-text-tertiary">数据更新于 {lastUpdated}</span>}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {QUICK_ACTIONS.map((action, idx) => (
                    <Link key={idx} href={action.href} className="flex flex-col p-4 bg-surface-2/70 hover:bg-surface-2 border border-separator rounded-[16px] transition-all group">
                      <div className="flex justify-between items-center mb-3">
                         <action.icon size={20} className="text-text-secondary group-hover:text-accent transition-colors" />
                         <ArrowRight className="opacity-0 group-hover:opacity-100 transition-opacity -rotate-45 text-accent" size={14} />
                      </div>
                      <span className="text-sm font-medium text-text group-hover:text-white">{action.label}</span>
                      <span className="text-xs text-text-secondary mt-1 line-clamp-1">{action.desc}</span>
                    </Link>
                ))}
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
