"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Activity, BrainCircuit, Zap, RefreshCw } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';

type Overview = {
  observed_at: string; requests_today: number; successful_requests_today: number;
  failed_requests_today: number; average_latency_ms: number | null; success_rate: number | null;
  active_models: number; total_models: number;
  models: { id: number; name: string; type: string; enabled: boolean; is_default: boolean }[];
};

export default function PlatformDashboard() {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  async function refresh() {
    setLoading(true);
    setError('');
    setData(null);
    try { setData((await api.get<Overview>('/api/v1/platform/overview')).data); }
    catch { setError('无法读取平台统计，请确认管理员权限及后端连接后重试。'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);
  const metrics = [
    { title: '今日已记录调用', icon: Zap, value: data ? String(data.requests_today) : '—', note: '来自模型调用日志' },
    { title: '成功调用平均延迟', icon: Activity, value: data?.average_latency_ms != null ? `${data.average_latency_ms} ms` : '—', note: '无有效延迟记录时不显示数值' },
    { title: '启用模型', icon: BrainCircuit, value: data ? String(data.active_models) : '—', note: data ? `模型注册表共 ${data.total_models} 个` : '正在读取注册表' },
    { title: '今日调用成功率', icon: Activity, value: data?.success_rate != null ? `${data.success_rate}%` : '—', note: data ? `${data.successful_requests_today} 成功 · ${data.failed_requests_today} 失败` : '正在读取调用日志' },
  ];
  return <div className="p-4 md:p-8 space-y-6">
    <PageHeader title="AI 中台总览" description="模型注册与已记录调用统计。模型启用状态不代表远端服务已经连通。" actions={<Button variant="outline" disabled={loading} onClick={() => void refresh()} className="gap-2"><RefreshCw size={16} />刷新</Button>} />
    {loading && <p role="status" className="text-sm text-text-secondary">正在读取平台数据…</p>}
    {error && <p role="alert" className="rounded-lg bg-danger/10 border border-danger/30 p-4 text-danger">{error}</p>}
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">{metrics.map(metric => <div key={metric.title} className="glass-panel p-5 space-y-3">
      <p className="flex items-center gap-2 text-sm text-text-secondary"><metric.icon size={16} />{metric.title}</p>
      <p className="text-3xl font-semibold tabular-nums">{metric.value}</p>
      <p className="text-xs text-text-secondary">{metric.note}</p>
    </div>)}</div>
    <section className="glass-panel p-5 space-y-4">
      <div className="flex items-center justify-between gap-4"><h2 className="font-semibold">已纳管模型</h2><Link href="/platform/models" className="text-sm text-accent underline">管理与配置模型</Link></div>
      {data && data.models.length === 0 && <p className="text-text-secondary">尚未配置模型，请先添加真实模型服务。</p>}
      {data?.models.map(model => <div key={model.id} className="rounded-lg border border-separator p-4 flex flex-wrap gap-3 justify-between items-center">
        <div><p className="font-medium">{model.name}{model.is_default ? ' · 默认模型' : ''}</p><p className="text-xs text-text-secondary mt-1">{model.type}</p></div>
        <span className="text-sm text-text-secondary">{model.enabled ? '已启用，连通性需实测' : '未启用'}</span>
      </div>)}
      {data && <p className="text-xs text-text-secondary">数据读取时间：{new Date(data.observed_at).toLocaleString('zh-CN')}</p>}
    </section>
    <div className="flex flex-wrap gap-4 text-sm"><Link href="/platform/skills" className="text-accent underline">技能工具箱</Link><Link href="/ops" className="text-accent underline">系统实际运行指标</Link></div>
  </div>;
}
