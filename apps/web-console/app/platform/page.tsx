"use client";
import React from 'react';
import { 
  Activity, 
  BrainCircuit, 
  Server, 
  TrendingUp, 
  Zap,
  Database,
  ArrowRight
} from 'lucide-react';
import Link from 'next/link';
import { PageHeader } from '@/components/PageHeader';

export default function PlatformDashboard() {
  return (
    <div className="h-full w-full p-6 text-text flex flex-col gap-6">
      <PageHeader
        title="AI 中台总览"
        description="企业级 AI 基础设施与模型路由"
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard icon={Zap} title="今日调用量" value="1.2M" trend="+12.5%" trendUp />
        <KpiCard icon={Activity} title="平均延迟" value="240ms" trend="-5%" trendUp={true} />
        <KpiCard icon={BrainCircuit} title="活跃模型" value="8" sub="共 12 个" />
        <KpiCard icon={Server} title="GPU 算力负载" value="78%" trend="高负载" trendUp={false} color="text-warning" />
      </div>

       {/* Main Content Area */}
       <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
          
          {/* Left: Model Services Status */}
          <div className="glass-panel p-6 overflow-y-auto">
             <div className="flex justify-between items-center mb-6">
                <h3 className="font-semibold flex items-center gap-2">
                    <Database size={18} className="text-accent" />
                    核心模型服务状态
                </h3>
                <Link href="/platform/models" className="text-xs text-accent hover:text-accent-hover flex items-center gap-1 transition-colors">
                    管理模型 <ArrowRight size={12}/>
                </Link>
             </div>
             <div className="space-y-4">
                <ModelStatusRow name="GPT-4-Turbo (Azure)" type="LLM" status="Healthy" latency="850ms" qps="45" />
                <ModelStatusRow name="Llama-3-70B-Instruct" type="LLM (Local)" status="Healthy" latency="120ms" qps="120" />
                <ModelStatusRow name="Text-Embedding-3-Large" type="Embedding" status="Healthy" latency="45ms" qps="350" />
                <ModelStatusRow name="Stable-Diffusion-XL" type="Image" status="Degraded" latency="4.5s" qps="2" statusColor="text-warning" />
                <ModelStatusRow name="Whisper-v3" type="ASR" status="Healthy" latency="1.2s" qps="8" />
             </div>
          </div>

          {/* Right: Traffic Overview & Quick Actions */}
          <div className="flex flex-col gap-6">
              {/* Traffic Mini Chart */}
              <div className="glass-panel p-6 flex-1">
                 <div className="flex justify-between items-center mb-4">
                    <h3 className="font-semibold flex items-center gap-2">
                        <TrendingUp size={18} className="text-success" />
                        实时流量趋势
                    </h3>
                 </div>
                 {/* Visual Placeholder for Chart */}
                 <div className="flex items-end justify-between h-32 gap-1 px-2">
                    {[30, 45, 35, 60, 75, 50, 65, 80, 70, 90, 85, 95].map((h, i) => (
                        <div key={i} className="w-full bg-gradient-to-t from-accent/20 to-accent/70 rounded-t-sm" style={{height: `${h}%`}}></div>
                    ))}
                 </div>
                 <div className="mt-4 flex justify-between text-xs text-text-secondary">
                    <span>00:00</span>
                    <span>12:00</span>
                    <span>现在</span>
                 </div>
              </div>

               {/* System Health */}
               <div className="glass-panel p-6">
                  <h3 className="font-semibold mb-4 text-sm text-text">系统健康度</h3>
                  <div className="flex items-center gap-4">
                      <div className="relative w-16 h-16 flex items-center justify-center">
                          <div className="absolute inset-0 border-4 border-separator rounded-full"></div>
                          <div className="absolute inset-0 border-4 border-success rounded-full border-l-transparent border-r-transparent rotate-45"></div>
                          <span className="text-lg font-bold text-success tabular-nums">98</span>
                      </div>
                      <div className="flex-1 space-y-2">
                          <HealthItem label="API 网关" status="正常" />
                          <HealthItem label="向量数据库" status="正常" />
                          <HealthItem label="模型路由" status="正常" />
                      </div>
                  </div>
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
                <Icon size={16} />
                {title}
            </div>
            <div className="flex items-end gap-3 z-10">
                <span className="text-3xl font-bold text-text tracking-tight tabular-nums">{value}</span>
                {trend && (
                    <span className={`text-xs font-bold mb-1.5 px-1.5 py-0.5 rounded tabular-nums ${trendUp ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'}`}>
                        {trend}
                    </span>
                )}
                {sub && <span className="text-xs text-text-secondary mb-1.5">{sub}</span>}
            </div>
        </div>
    )
}

function ModelStatusRow({ name, type, status, latency, qps, statusColor }: any) {
    const isHealthy = status === 'Healthy';
    return (
        <div className="flex items-center justify-between p-3 rounded-lg bg-text/5 border border-separator hover:bg-text/10 transition-colors">
            <div className="flex items-center gap-4">
                <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-success shadow-[0_0_8px_rgb(var(--ui-success)/0.5)]' : 'bg-warning'}`}></div>
                <div>
                    <div className="font-bold text-sm text-text">{name}</div>
                    <div className="text-[10px] text-text-secondary uppercase font-mono">{type}</div>
                </div>
            </div>
            <div className="flex items-center gap-6 text-xs text-text-secondary font-mono">
                <div className="flex flex-col items-end">
                    <span className="text-text-secondary text-[10px]">延迟</span>
                    <span className="tabular-nums">{latency}</span>
                </div>
                <div className="flex flex-col items-end w-12">
                    <span className="text-text-secondary text-[10px]">QPS</span>
                    <span className="tabular-nums">{qps}</span>
                </div>
                <div className={`px-2 py-1 rounded text-[10px] font-bold ${isHealthy ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'}`}>
                    {isHealthy ? '正常' : '降级'}
                </div>
            </div>
        </div>
    )
}

function HealthItem({ label, status }: any) {
    return (
        <div className="flex justify-between items-center text-xs">
            <span className="text-text-secondary">{label}</span>
            <span className="text-success font-mono font-bold">{status}</span>
        </div>
    )
}
