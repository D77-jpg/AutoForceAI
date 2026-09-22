"use client";
import React, { useEffect, useState } from 'react';
import api from '../../lib/api';
import { 
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell
} from 'recharts';
import { 
    Server, Database, AlertCircle, CheckCircle2, Cpu, FileJson, Clock
} from 'lucide-react';
import { useToast } from '../../contexts/ToastContext';
import { PageHeader } from '@/components/PageHeader';

function StatCard({ title, value, subValue, icon: Icon, color }: any) {
    return (
        <div className="glass-card p-6 border border-separator relative overflow-hidden group">
            <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity ${color}`}>
                <Icon size={48} />
            </div>
            <div className="flex items-center gap-3 mb-2">
                <div className={`p-2 rounded-lg bg-text/5 ${color.replace('text-', 'text-opacity-80 ')}`}>
                    <Icon size={20} className={color} />
                </div>
                <span className="text-text-secondary text-sm">{title}</span>
            </div>
            <div className="text-3xl font-bold font-mono mt-2 tabular-nums">{value}</div>
            {subValue && <div className="text-xs text-text-secondary mt-1">{subValue}</div>}
        </div>
    );
}

export default function MonitorPage() {
    const { showToast } = useToast();
    const [rpaStats, setRpaStats] = useState<any>(null);
    const [llmStats, setLlmStats] = useState<any>(null);
    const [recentLogs, setRecentLogs] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 10000); // Poll every 10s
        return () => clearInterval(interval);
    }, []);

    const fetchData = async () => {
        try {
            const [rpaRes, llmRes, logsRes] = await Promise.all([
                api.get(`/api/v1/monitor/rpa/stats`),
                api.get(`/api/v1/monitor/llm/usage`), 
                api.get(`/api/v1/monitor/llm/logs?limit=20`)
            ]);
            setRpaStats(rpaRes.data);
            setLlmStats(llmRes.data);
            setRecentLogs(logsRes.data);
        } catch (error) {
            console.error("Monitor Data Load Failed", error);
            // showToast("Failed to fetch monitor data", "error");
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="p-8 text-center text-text-secondary">正在初始化监控探针...</div>;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fade-in-up">
            <PageHeader
                title="系统监控"
                description="AI Agent 与 RPA 执行器的实时运行观测"
                className="mb-0"
                actions={
                    <div className="flex items-center gap-2 text-xs text-success bg-success/10 px-3 py-1 rounded-full border border-success/20">
                        <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
                        系统在线
                    </div>
                }
            />

            {/* Top Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <StatCard 
                    title="AI Token 总量（7 天）" 
                    value={(llmStats?.summary?.total_tokens / 1000).toFixed(1) + "k"}
                    subValue={`${llmStats?.summary?.total_calls} 次 API 调用`}
                    icon={Cpu}
                    color="text-accent"
                />
                 <StatCard 
                    title="RPA 队列深度" 
                    value={rpaStats?.counts?.queued || 0}
                    subValue="待处理任务"
                    icon={Database}
                    color="text-warning"
                />
                <StatCard 
                    title="Worker 成功率" 
                    value={
                        rpaStats?.counts?.completed + rpaStats?.counts?.failed > 0 
                        ? ((rpaStats.counts.completed / (rpaStats.counts.completed + rpaStats.counts.failed)) * 100).toFixed(1) + "%" 
                        : "N/A"
                    }
                    subValue={`已完成 ${rpaStats?.counts?.completed} 项`}
                    icon={CheckCircle2}
                    color="text-success"
                />
                 <StatCard 
                    title="失败任务" 
                    value={rpaStats?.counts?.failed || 0}
                    subValue="需要关注"
                    icon={AlertCircle}
                    color="text-danger"
                />
            </div>

            {/* Charts Area */}
            <div className="grid md:grid-cols-2 gap-8">
                {/* Token Usage Trend */}
                <div className="glass-card p-6 border border-separator rounded-xl">
                    <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                        <Server size={18} className="text-accent"/>
                        Token 消耗趋势
                    </h3>
                    <div className="h-64 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={llmStats?.daily_trend || []}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--ui-separator) / var(--ui-separator-alpha))" vertical={false} />
                                <XAxis dataKey="date" stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                                <Tooltip 
                                    contentStyle={{backgroundColor: 'rgb(var(--ui-surface))', border: '1px solid rgb(var(--ui-separator) / var(--ui-separator-alpha))', borderRadius: '8px'}}
                                    itemStyle={{color: '#fff'}}
                                />
                                <Line 
                                    type="monotone" 
                                    dataKey="tokens" 
                                    stroke="rgb(var(--ui-accent))" 
                                    strokeWidth={3} 
                                    dot={{fill: "rgb(var(--ui-accent))", r: 4}} 
                                    activeDot={{r: 6, stroke: '#fff'}}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* LLM Provider Distribution */}
                <div className="glass-card p-6 border border-separator rounded-xl">
                    <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                        <Database size={18} className="text-accent"/>
                        模型用量分布
                    </h3>
                    <div className="space-y-4">
                        {Object.entries(llmStats?.by_provider || {}).map(([provider, tokens]: any, i) => (
                            <div key={i} className="group">
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="capitalize text-text">{provider}</span>
                                    <span className="font-mono tabular-nums text-text-secondary">{tokens} tokens</span>
                                </div>
                                <div className="h-2 bg-text/5 rounded-full overflow-hidden">
                                    <div 
                                        className="h-full bg-gradient-to-r from-accent to-accent-hover" 
                                        style={{width: `${(tokens / llmStats?.summary?.total_tokens) * 100}%`}}
                                    ></div>
                                </div>
                            </div>
                        ))}
                        {Object.keys(llmStats?.by_provider || {}).length === 0 && (
                            <div className="text-center text-text-tertiary py-10">暂无用量数据</div>
                        )}
                    </div>
                </div>
            </div>

            {/* Logs Table */}
            <div className="glass-card border border-separator rounded-xl overflow-hidden">
                <div className="p-6 border-b border-separator">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                        <FileJson size={18} className="text-text-secondary"/>
                        最近 AI 审计日志
                    </h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-text/5 text-text-secondary font-medium">
                            <tr>
                                <th className="px-6 py-4">状态</th>
                                <th className="px-6 py-4">模型</th>
                                <th className="px-6 py-4">Token（输入/输出）</th>
                                <th className="px-6 py-4">延迟</th>
                                <th className="px-6 py-4">时间</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-separator">
                            {recentLogs.map((log: any) => (
                                <tr key={log.id} className="hover:bg-text/5 transition-colors">
                                    <td className="px-6 py-4">
                                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
                                            ${log.status === 'success' ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}
                                        `}>
                                            <div className={`w-1.5 h-1.5 rounded-full ${log.status === 'success' ? 'bg-success' : 'bg-danger'}`}></div>
                                            {log.status === 'success' ? '成功' : '失败'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 font-mono text-text">{log.model}</td>
                                    <td className="px-6 py-4 text-text-secondary">
                                        {log.input_tokens} / <span className="text-accent">{log.output_tokens}</span>
                                    </td>
                                    <td className="px-6 py-4 text-text-secondary">{log.latency_ms}ms</td>
                                    <td className="px-6 py-4 text-text-secondary flex items-center gap-2">
                                        <Clock size={12}/>
                                        {new Date(log.created_at).toLocaleTimeString()}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            
            {/* Recent Failures */}
            {rpaStats?.recent_failures?.length > 0 && (
                 <div className="glass-card border border-danger/20 bg-danger/5 rounded-xl p-6">
                    <h3 className="text-lg font-bold text-danger mb-4 flex items-center gap-2">
                        <AlertCircle size={18}/>
                        最近 RPA 失败记录
                    </h3>
                    <div className="space-y-3">
                        {rpaStats.recent_failures.map((fail: any, i:number) => (
                            <div key={i} className="flex items-start gap-3 p-3 bg-bg/20 rounded border border-danger/10">
                                <AlertCircle size={16} className="text-danger mt-1 shrink-0"/>
                                <div>
                                    <div className="text-sm font-bold text-text">{fail.platform} Worker 错误 #{fail.id}</div>
                                    <div className="text-xs text-danger/80 font-mono mt-1">{fail.msg}</div>
                                    <div className="text-xs text-text-tertiary mt-1">{new Date(fail.time).toLocaleString()}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                 </div>
            )}
        </div>
    );
}
