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

export default function MarketingDashboard() {
  const [kpis, setKpis] = useState<any>(null);
  useEffect(() => {
    api.get('/api/v1/marketing/funnel?days=30').then(r => setKpis(r.data.kpis)).catch(() => {});
  }, []);
  return (
    <div className="h-full w-full p-6 text-text flex flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-orange-400 to-rose-400">AI 营销云看板</h1>
        <p className="text-sm text-text-secondary mt-1">外贸获客引擎 · 英文内容 · 海外分发 · GEO 监测</p>
      </div>

      {/* Quick Access Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <KpiCard icon={PenTool} title="内容产出 (30d)" value={String(kpis?.content ?? "—")} sub="英文文案" />
          <KpiCard icon={Eye} title="GEO 曝光" value={String(kpis?.mentions ?? "—")} trend={kpis ? `${kpis.mention_rate}%` : undefined} trendUp />
          <KpiCard icon={Share2} title="内容分发" value={String(kpis?.jobs ?? "—")} sub="RPA 任务" />
          <KpiCard icon={Cpu} title="RPA 成功率" value={kpis ? `${kpis.success_rate}%` : "—"} trend="Success Rate" trendUp={true} />
      </div>

      {/* Main Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
          
          {/* Content Creation Hub */}
          <div className="glass-panel p-6 flex flex-col">
              <h3 className="font-semibold flex items-center gap-2 mb-6">
                  <PenTool size={18} className="text-warning" />
                  内容生产中心 (AIGC Hub)
              </h3>
              <div className="grid grid-cols-2 gap-4">
                  <ActionCard 
                    href="/marketing/text-gen"
                    title="文生文 (Text Gen)"
                    desc="生成 SEO 文章、社媒文案、营销邮件。"
                    icon={PenTool}
                    color="bg-warning"
                  />
                  <ActionCard 
                    href="/marketing/image-gen"
                    title="文生图 (Image Gen)"
                    desc="生成海报、配图、产品展示图。"
                    icon={ImageIcon}
                    color="bg-danger"
                  />
              </div>
          </div>

          {/* Operations Hub */}
          <div className="glass-panel p-6 flex flex-col">
              <h3 className="font-semibold flex items-center gap-2 mb-6">
                  <Send size={18} className="text-accent" />
                  自动化运营 (Ops Automation)
              </h3>
              <div className="grid grid-cols-2 gap-4">
                  <ActionCard 
                    href="/marketing/distribution"
                    title="海外投放 (Distribute)"
                    desc="LinkedIn / WordPress / X 一键入队。"
                    icon={Share2}
                    color="bg-accent"
                  />
                  <ActionCard 
                    href="/marketing/analytics"
                    title="获客漏斗 (Analytics)"
                    desc="内容 → 发布 → 曝光 → 本地询盘。"
                    icon={MousePointerClick}
                    color="bg-accent"
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
            <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity ${color || 'text-white'}`}>
                <Icon size={60} />
            </div>
            <div className="flex items-center gap-3 mb-2 text-text-secondary text-xs font-semibold uppercase tracking-wider">
                <Icon size={16} />
                {title}
            </div>
            <div className="flex items-end gap-3 z-10">
                <span className={`text-3xl font-bold text-white tracking-tight`}>{value}</span>
                {trend && (
                    <span className={`text-xs font-bold mb-1.5 px-1.5 py-0.5 rounded ${trendUp ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'}`}>
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
            <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center text-white mb-3 shadow-lg`}>
                <Icon size={20} />
            </div>
            <h4 className="font-bold text-text mb-1 text-sm">{title}</h4>
            <p className="text-xs text-text-secondary leading-relaxed">{desc}</p>
            <div className="mt-3 flex justify-end">
                <ArrowUpRight size={14} className="text-text-secondary group-hover:text-white transition-colors" />
            </div>
        </Link>
    )
}
