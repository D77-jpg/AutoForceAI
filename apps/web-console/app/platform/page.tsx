"use client";
import React from 'react';
import { 
  Activity, 
  BrainCircuit, 
  Cpu, 
  Server, 
  TrendingUp, 
  Zap,
  Globe,
  Database,
  ArrowRight
} from 'lucide-react';
import Link from 'next/link';

export default function PlatformDashboard() {
  return (
    <div className="h-full w-full p-6 text-[#f5f5f7] flex flex-col gap-6">
      <div>
        <h1 className="text-[28px] font-semibold tracking-tight text-[#f5f5f7]">AI 中台总览</h1>
        <p className="text-[15px] text-[#86868b] mt-1.5">Enterprise AI Infrastructure & Model Routing</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard icon={Zap} title="今日调用量 (Requests)" value="1.2M" trend="+12.5%" trendUp />
        <KpiCard icon={Activity} title="平均响应 (Avg Latency)" value="240ms" trend="-5%" trendUp={true} />
        <KpiCard icon={BrainCircuit} title="活跃模型 (Active Models)" value="8" sub="Total 12" />
        <KpiCard icon={Server} title="GPU 算力负载" value="78%" trend="High Load" trendUp={false} color="text-orange-400" />
      </div>

       {/* Main Content Area */}
       <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
          
          {/* Left: Model Services Status */}
          <div className="lg:col-span-2 glass-panel p-6 overflow-y-auto">
             <div className="flex justify-between items-center mb-6">
                <h3 className="font-semibold flex items-center gap-2">
                    <Database size={18} className="text-[#0a84ff]" />
                    核心模型服务状态
                </h3>
                <Link href="/platform/models" className="text-xs text-[#0a84ff] hover:text-[#64d2ff] flex items-center gap-1">
                    管理模型 <ArrowRight size={12}/>
                </Link>
             </div>
             <div className="space-y-4">
                <ModelStatusRow name="GPT-4-Turbo (Azure)" type="LLM" status="Healthy" latency="850ms" qps="45" />
                <ModelStatusRow name="Llama-3-70B-Instruct" type="LLM (Local)" status="Healthy" latency="120ms" qps="120" />
                <ModelStatusRow name="Text-Embedding-3-Large" type="Embedding" status="Healthy" latency="45ms" qps="350" />
                <ModelStatusRow name="Stable-Diffusion-XL" type="Image" status="Degraded" latency="4.5s" qps="2" statusColor="text-yellow-400" />
                <ModelStatusRow name="Whisper-v3" type="ASR" status="Healthy" latency="1.2s" qps="8" />
             </div>
          </div>

          {/* Right: Traffic Overview & Quick Actions */}
          <div className="flex flex-col gap-6">
              {/* Traffic Mini Chart */}
              <div className="glass-panel p-6 flex-1">
                 <div className="flex justify-between items-center mb-4">
                    <h3 className="font-semibold flex items-center gap-2">
                        <TrendingUp size={18} className="text-emerald-400" />
                        实时流量趋势
                    </h3>
                 </div>
                 {/* Visual Placeholder for Chart */}
                 <div className="flex items-end justify-between h-32 gap-1 px-2">
                    {[30, 45, 35, 60, 75, 50, 65, 80, 70, 90, 85, 95].map((h, i) => (
                        <div key={i} className="w-full bg-gradient-to-t from-[#0a84ff]/20 to-[#0a84ff]/70 rounded-t-sm" style={{height: `${h}%`}}></div>
                    ))}
                 </div>
                 <div className="mt-4 flex justify-between text-xs text-slate-500">
                    <span>00:00</span>
                    <span>12:00</span>
                    <span>Now</span>
                 </div>
              </div>

               {/* System Health */}
               <div className="glass-panel p-6">
                  <h3 className="font-semibold mb-4 text-sm text-slate-300">系统健康度</h3>
                  <div className="flex items-center gap-4">
                      <div className="relative w-16 h-16 flex items-center justify-center">
                          <div className="absolute inset-0 border-4 border-white/10 rounded-full"></div>
                          <div className="absolute inset-0 border-4 border-emerald-500 rounded-full border-l-transparent border-r-transparent rotate-45"></div>
                          <span className="text-lg font-bold text-emerald-400">98</span>
                      </div>
                      <div className="flex-1 space-y-2">
                          <HealthItem label="API Gateway" status="OK" />
                          <HealthItem label="Vector DB" status="OK" />
                          <HealthItem label="Model Router" status="OK" />
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
            <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity ${color || 'text-white'}`}>
                <Icon size={60} />
            </div>
            <div className="flex items-center gap-3 mb-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
                <Icon size={16} />
                {title}
            </div>
            <div className="flex items-end gap-3 z-10">
                <span className={`text-3xl font-bold text-white tracking-tight`}>{value}</span>
                {trend && (
                    <span className={`text-xs font-bold mb-1.5 px-1.5 py-0.5 rounded ${trendUp ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                        {trend}
                    </span>
                )}
                {sub && <span className="text-xs text-slate-500 mb-1.5">{sub}</span>}
            </div>
        </div>
    )
}

function ModelStatusRow({ name, type, status, latency, qps, statusColor }: any) {
    const isHealthy = status === 'Healthy';
    return (
        <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
            <div className="flex items-center gap-4">
                <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-yellow-500'}`}></div>
                <div>
                    <div className="font-bold text-sm text-slate-200">{name}</div>
                    <div className="text-[10px] text-slate-500 uppercase font-mono">{type}</div>
                </div>
            </div>
            <div className="flex items-center gap-6 text-xs text-slate-400 font-mono">
                <div className="flex flex-col items-end">
                    <span className="text-slate-500 text-[10px]">LATENCY</span>
                    <span>{latency}</span>
                </div>
                <div className="flex flex-col items-end w-12">
                    <span className="text-slate-500 text-[10px]">QPS</span>
                    <span>{qps}</span>
                </div>
                <div className={`px-2 py-1 rounded text-[10px] font-bold ${isHealthy ? 'bg-emerald-500/10 text-emerald-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
                    {status}
                </div>
            </div>
        </div>
    )
}

function HealthItem({ label, status }: any) {
    return (
        <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400">{label}</span>
            <span className="text-emerald-400 font-mono font-bold">{status}</span>
        </div>
    )
}
