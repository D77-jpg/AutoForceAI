"use client";
import React, { useEffect, useState } from 'react';
import { BarChart4, Coins, Layers, Zap, Calendar, TrendingUp } from 'lucide-react';
import api from '@/lib/api';

export default function TrafficPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
        try {
            const res = await api.get('/api/v1/monitor/llm/usage?days=7');
            setData(res.data);
        } catch(e) { console.error(e) }
        finally { setLoading(false) }
    };
    fetchData();
  }, []);

  const totalTokens = data?.summary?.total_tokens || 0;
  const totalCalls = data?.summary?.total_calls || 0;
  
  // Calculate max tokens for chart scaling
  const maxDailyTokens = data?.daily_trend?.reduce((acc: number, cur: any) => Math.max(acc, cur.tokens), 0) || 1;

  return (
    <div className="h-full w-full p-6 text-slate-100 flex flex-col overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
            <div>
                 <h1 className="text-2xl font-bold text-white">流量统计 (Traffic Stats)</h1>
                 <p className="text-sm text-slate-400">LLM 调用量、Token 消耗与成本分析。</p>
            </div>
             <div className="flex gap-2">
                <button className="px-3 py-1.5 bg-white/5 border border-white/5 rounded-lg text-xs text-slate-300 flex items-center gap-2">
                    <Calendar size={14}/> Last 7 Days
                </button>
             </div>
        </div>
        
        {loading ? (
             <div className="flex-1 flex items-center justify-center text-slate-500">
                <BarChart4 className="animate-pulse mr-2" /> Loading analytics...
             </div>
        ) : (
            <div className="space-y-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                     <div className="bg-[#1c1c1e] border border-white/5 p-6 rounded-xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-5">
                            <Coins size={64} />
                        </div>
                        <h3 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                            <Coins size={16} className="text-amber-400"/> 总消耗 (Total Tokens)
                        </h3>
                        <div className="text-3xl font-bold text-white font-mono">
                            {(totalTokens / 1000).toFixed(1)}k
                        </div>
                        <div className="text-xs text-slate-500 mt-1">Estimate: ${(totalTokens * 0.00001).toFixed(4)}</div>
                     </div>

                     <div className="bg-[#1c1c1e] border border-white/5 p-6 rounded-xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-5">
                            <Zap size={64} />
                        </div>
                        <h3 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                            <Zap size={16} className="text-[#0a84ff]"/> API 调用次数
                        </h3>
                        <div className="text-3xl font-bold text-white font-mono">
                            {totalCalls}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">Avg: {(totalCalls / 7).toFixed(1)} / day</div>
                     </div>

                     <div className="bg-[#1c1c1e] border border-white/5 p-6 rounded-xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-5">
                            <Layers size={64} />
                        </div>
                        <h3 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                            <Layers size={16} className="text-blue-400"/> 活跃供应商
                        </h3>
                        <div className="text-3xl font-bold text-white font-mono">
                            {Object.keys(data?.by_provider || {}).length}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">Providers</div>
                     </div>
                </div>

                {/* Chart */}
                <div className="bg-[#1c1c1e] border border-white/5 p-6 rounded-xl flex-1 min-h-[300px] flex flex-col">
                     <h3 className="text-sm font-medium text-slate-300 mb-6 flex items-center gap-2">
                         <TrendingUp size={16} className="text-[#0a84ff]"/> 每日消耗趋势
                     </h3>
                     
                     <div className="flex-1 flex items-end gap-2 h-full">
                        {data?.daily_trend?.length === 0 && (
                            <div className="w-full text-center text-slate-500 text-sm py-10">
                                暂无数据 (No Data Available)
                            </div>
                        )}
                        {data?.daily_trend?.map((day: any) => (
                            <div key={day.date} className="flex-1 flex flex-col items-center gap-2 group">
                                <div className="w-full relative flex-1 flex items-end bg-white/[0.02] rounded-t-lg hover:bg-white/[0.05] transition-colors">
                                    <div 
                                        className="w-full bg-[#0a84ff]/50 hover:bg-[#0077ed] rounded-t-lg transition-all relative group-hover:shadow-none"
                                        style={{ height: `${(day.tokens / maxDailyTokens) * 100}%` }}
                                    >
                                        <div className="absolute -top-12 left-1/2 -translate-x-1/2 bg-black/80 px-2 py-1 rounded text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                                            {day.tokens} Tokens
                                            <br/>
                                            {day.calls} Calls
                                        </div>
                                    </div>
                                </div>
                                <div className="text-xs text-slate-500 font-mono rotate-0 whitespace-nowrap overflow-hidden text-ellipsis max-w-[50px]">{day.date.slice(5)}</div>
                            </div>
                        ))}
                     </div>
                </div>

                {/* Provider Breakdown Table */}
                 <div className="bg-[#1c1c1e] border border-white/5 rounded-xl overflow-hidden">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-white/[0.02] text-slate-400 font-medium">
                            <tr>
                                <th className="p-4 pl-6">供应商 (Provider)</th>
                                <th className="p-4 text-right pr-6">总消耗 (Tokens)</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {Object.entries(data?.by_provider || {}).map(([provider, tokens]: any) => (
                                <tr key={provider} className="hover:bg-white/[0.02]">
                                    <td className="p-4 pl-6 text-white font-medium">{provider}</td>
                                    <td className="p-4 text-right pr-6 font-mono text-slate-300">{tokens}</td>
                                </tr>
                            ))}
                            {Object.keys(data?.by_provider || {}).length === 0 && (
                                <tr>
                                    <td colSpan={2} className="p-8 text-center text-slate-500">
                                        暂无供应商数据
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                 </div>
            </div>
        )}
    </div>
  )
}

