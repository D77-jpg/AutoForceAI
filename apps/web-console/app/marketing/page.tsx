"use client";
import React, { useEffect, useState } from 'react';
import { 
  PenTool, 
  Image as ImageIcon, 
  Send, 
  Cpu, 
  ArrowUpRight,
  MousePointerClick,
  Eye,
  Share2
} from 'lucide-react';
import Link from 'next/link';
import api from '../../lib/api';
import { PageHeader } from '@/components/PageHeader';

export default function MarketingDashboard() {
  const [kpis, setKpis] = useState<any>(null);
  useEffect(() => {
    api.get('/api/v1/marketing/funnel?days=30').then(r => setKpis(r.data.kpis)).catch(() => {});
  }, []);
  return (
    <div className="h-full w-full p-6 text-text flex flex-col gap-6">
      {/* Header */}
      <PageHeader
        title="投放参谋"
        description="外贸获客引擎 · 英文内容 · 海外分发 · GEO 监测"
        className="mb-0 shrink-0"
      />

      {/* Quick Access Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <KpiCard icon={PenTool} title="内容产出" value={String(kpis?.content ?? "—")} sub="近 30 天" />
          <KpiCard icon={Eye} title="GEO 曝光" value={String(kpis?.mentions ?? "—")} trend={kpis ? `${kpis.mention_rate}%` : undefined} trendUp />
          <KpiCard icon={Share2} title="内容分发" value={String(kpis?.jobs ?? "—")} sub="RPA 任务" />
          <KpiCard icon={Cpu} title="RPA 成功率" value={kpis ? `${kpis.success_rate}%` : "—"} trend="成功率" trendUp={true} />
      </div>

      {/* Main Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
          
          {/* Content Creation Hub */}
          <div className="glass-panel p-6 flex flex-col">
              <h3 className="font-semibold flex items-center gap-2 mb-6">
                  <PenTool size={18} strokeWidth={1.75} className="text-tint-growth" />
                  内容生产中心
              </h3>
              <div className="grid grid-cols-2 gap-4">
                  <ActionCard 
                    href="/marketing/text-gen"
                    title="文生文"
                    desc="生成 SEO 文章、社媒文案、营销邮件。"
                    icon={PenTool}
                    color="bg-tint-growth"
                  />
                  <ActionCard 
                    href="/marketing/image-gen"
                    title="文生图"
                    desc="生成海报、配图、产品展示图。"
                    icon={ImageIcon}
                    color="bg-tint-decision"
                  />
              </div>
          </div>

          {/* Operations Hub */}
          <div className="glass-panel p-6 flex flex-col">
              <h3 className="font-semibold flex items-center gap-2 mb-6">
                  <Send size={18} strokeWidth={1.75} className="text-tint-ops" />
                  自动化运营
              </h3>
              <div className="grid grid-cols-2 gap-4">
                  <ActionCard 
                    href="/marketing/distribution"
                    title="海外投放"
                    desc="LinkedIn / WordPress / X 一键入队。"
                    icon={Share2}
                    color="bg-tint-ops"
                  />
                  <ActionCard 
                    href="/marketing/analytics"
                    title="获客漏斗"
                    desc="内容 → 发布 → 曝光 → 本地询盘。"
                    icon={MousePointerClick}
                    color="bg-tint-revenue"
                  />
              </div>
          </div>
      </div>
    </div>
  );
}

function KpiCard({ icon: Icon, title, value, trend, trendUp, sub, color }: any) {
    return (
        <div className="glass-panel p-5 flex flex-col justify-between relative overflow-hidden group">
            <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity ${color || 'text-text'}`}>
                <Icon size={60} />
            </div>
            <div className="flex items-center gap-3 mb-2 text-text-secondary text-xs font-semibold">
                <Icon size={16} strokeWidth={1.75} />
                {title}
            </div>
            <div className="flex items-end gap-3 z-10">
                <span className={`text-3xl font-bold text-text tracking-tight tabular-nums`}>{value}</span>
                {trend && (
                    <span className={`text-xs font-bold mb-1.5 px-1.5 py-0.5 rounded-sm ${trendUp ? 'bg-success/20 text-success' : 'bg-surface-2 text-text-secondary'}`}>
                        {trend}
                    </span>
                )}
                {sub && <span className="text-xs text-text-secondary mb-1.5">{sub}</span>}
            </div>
        </div>
    )
}

function ActionCard({ href, title, desc, icon: Icon, color }: any) {
    return (
        <Link href={href} className="flex flex-col p-4 rounded-xl bg-text/5 border border-separator hover:bg-text/10 transition-all hover:-translate-y-1 group">
            <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center text-on-accent mb-3 shadow-card`}>
                <Icon size={20} strokeWidth={1.75} />
            </div>
            <h4 className="font-bold text-text mb-1 text-sm">{title}</h4>
            <p className="text-xs text-text-secondary leading-relaxed">{desc}</p>
            <div className="mt-3 flex justify-end">
                <ArrowUpRight size={14} className="text-text-secondary group-hover:text-text transition-colors" />
            </div>
        </Link>
    )
}
