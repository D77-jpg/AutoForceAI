"use client";
import React, { useEffect, useState } from 'react';
import { BarChart4, Coins, Layers, Zap, Calendar, TrendingUp, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState } from '@/components/ui/empty-state';
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from '@/components/ui/table';

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
    <div className="h-full w-full p-6 text-text flex flex-col overflow-y-auto">
        <PageHeader
            title="流量统计"
            description="LLM 调用量、Token 消耗与成本分析。"
            actions={
                <button className="h-10 px-4 bg-text/5 border border-separator rounded-md text-sm text-text flex items-center gap-2">
                    <Calendar size={14}/> 近 7 天
                </button>
            }
        />
        
        {loading ? (
             <EmptyState
                 icon={Loader2}
                 size="sm"
                 title="正在加载分析数据…"
                 className="flex-1"
             />
        ) : (
            <div className="space-y-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                     <div className="bg-surface border border-separator p-6 rounded-xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-5">
                            <Coins size={64} />
                        </div>
                        <h3 className="text-sm font-medium text-text-secondary mb-2 flex items-center gap-2">
                            <Coins size={16} className="text-warning"/> 总消耗（Tokens）
                        </h3>
                        <div className="text-3xl font-bold text-text font-mono tabular-nums">
                            {(totalTokens / 1000).toFixed(1)}k
                        </div>
                        <div className="text-xs text-text-secondary mt-1 tabular-nums">预估成本：${(totalTokens * 0.00001).toFixed(4)}</div>
                     </div>

                     <div className="bg-surface border border-separator p-6 rounded-xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-5">
                            <Zap size={64} />
                        </div>
                        <h3 className="text-sm font-medium text-text-secondary mb-2 flex items-center gap-2">
                            <Zap size={16} className="text-accent"/> API 调用次数
                        </h3>
                        <div className="text-3xl font-bold text-text font-mono tabular-nums">
                            {totalCalls}
                        </div>
                        <div className="text-xs text-text-secondary mt-1 tabular-nums">日均 {(totalCalls / 7).toFixed(1)} 次</div>
                     </div>

                     <div className="bg-surface border border-separator p-6 rounded-xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-5">
                            <Layers size={64} />
                        </div>
                        <h3 className="text-sm font-medium text-text-secondary mb-2 flex items-center gap-2">
                            <Layers size={16} className="text-accent"/> 活跃供应商
                        </h3>
                        <div className="text-3xl font-bold text-text font-mono tabular-nums">
                            {Object.keys(data?.by_provider || {}).length}
                        </div>
                        <div className="text-xs text-text-secondary mt-1">家供应商</div>
                     </div>
                </div>

                {/* Chart */}
                <div className="bg-surface border border-separator p-6 rounded-xl flex-1 min-h-[300px] flex flex-col">
                     <h3 className="text-sm font-medium text-text mb-6 flex items-center gap-2">
                         <TrendingUp size={16} className="text-accent"/> 每日消耗趋势
                     </h3>
                     
                     {data?.daily_trend?.length === 0 ? (
                        <EmptyState
                            icon={BarChart4}
                            size="sm"
                            title="暂无消耗数据"
                            description="所选时间范围内没有 LLM 调用记录。"
                        />
                     ) : (
                     <div className="flex-1 flex items-end gap-2 h-full">
                        {data?.daily_trend?.map((day: any) => (
                            <div key={day.date} className="flex-1 flex flex-col items-center gap-2 group">
                                <div className="w-full relative flex-1 flex items-end bg-text/[0.02] rounded-t-lg hover:bg-text/[0.05] transition-colors">
                                    <div 
                                        className="w-full bg-accent/50 hover:bg-accent-hover rounded-t-lg transition-all relative group-hover:shadow-none"
                                        style={{ height: `${(day.tokens / maxDailyTokens) * 100}%` }}
                                    >
                                        <div className="absolute -top-12 left-1/2 -translate-x-1/2 bg-bg/80 px-2 py-1 rounded text-xs text-text opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10 tabular-nums">
                                            {day.tokens} Tokens
                                            <br/>
                                            {day.calls} 次调用
                                        </div>
                                    </div>
                                </div>
                                <div className="text-xs text-text-secondary font-mono tabular-nums rotate-0 whitespace-nowrap overflow-hidden text-ellipsis max-w-[50px]">{day.date.slice(5)}</div>
                            </div>
                        ))}
                     </div>
                     )}
                </div>

                {/* Provider Breakdown Table */}
                 <div className="bg-surface border border-separator rounded-xl overflow-hidden">
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableHeaderCell className="pl-6">供应商</TableHeaderCell>
                                <TableHeaderCell className="text-right pr-6">消耗（Tokens）</TableHeaderCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {Object.entries(data?.by_provider || {}).map(([provider, tokens]: any) => (
                                <TableRow key={provider}>
                                    <TableCell className="pl-6 font-medium">{provider}</TableCell>
                                    <TableCell className="text-right pr-6 font-mono tabular-nums">{tokens}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                    {Object.keys(data?.by_provider || {}).length === 0 && (
                        <EmptyState
                            icon={Layers}
                            size="sm"
                            title="暂无供应商数据"
                            description="统计周期内没有按供应商归集的消耗记录。"
                        />
                    )}
                 </div>
            </div>
        )}
    </div>
  )
}
