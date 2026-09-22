"use client";
import React, { useEffect, useState } from 'react';
import api from '../../lib/api';
import { 
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell
} from 'recharts';
import { 
    Activity, Server, Database, AlertCircle, CheckCircle2, Cpu, FileJson, Clock
} from 'lucide-react';
import { useToast } from '../../contexts/ToastContext';

function StatCard({ title, value, subValue, icon: Icon, color }: any) {
    return (
        <div className="glass-card p-6 border border-white/5 relative overflow-hidden group">
            <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity ${color}`}>
                <Icon size={48} />
            </div>
            <div className="flex items-center gap-3 mb-2">
                <div className={`p-2 rounded-lg bg-white/5 ${color.replace('text-', 'text-opacity-80 ')}`}>
                    <Icon size={20} className={color} />
                </div>
                <span className="text-gray-400 text-sm">{title}</span>
            </div>
            <div className="text-3xl font-bold font-mono mt-2">{value}</div>
            {subValue && <div className="text-xs text-gray-500 mt-1">{subValue}</div>}
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

    if (loading) return <div className="p-8 text-center text-gray-500">Initializing Monitor Probes...</div>;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fade-in-up">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
                        <Activity className="text-[#0a84ff]" /> 
                        System Monitor
                    </h1>
                    <p className="text-gray-400">Real-time observability for AI Agents & RPA Workers</p>
                </div>
                <div className="flex items-center gap-2 text-xs text-green-400 bg-green-500/10 px-3 py-1 rounded-full border border-green-500/20">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                    System Online
                </div>
            </div>

            {/* Top Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <StatCard 
                    title="Total AI Tokens (7d)" 
                    value={(llmStats?.summary?.total_tokens / 1000).toFixed(1) + "k"}
                    subValue={`${llmStats?.summary?.total_calls} API Calls`}
                    icon={Cpu}
                    color="text-[#0a84ff]"
                />
                 <StatCard 
                    title="RPA Queue Depth" 
                    value={rpaStats?.counts?.queued || 0}
                    subValue="Pending Tasks"
                    icon={Database}
                    color="text-yellow-400"
                />
                <StatCard 
                    title="Worker Success Rate" 
                    value={
                        rpaStats?.counts?.completed + rpaStats?.counts?.failed > 0 
                        ? ((rpaStats.counts.completed / (rpaStats.counts.completed + rpaStats.counts.failed)) * 100).toFixed(1) + "%" 
                        : "N/A"
                    }
                    subValue={`${rpaStats?.counts?.completed} Completed`}
                    icon={CheckCircle2}
                    color="text-emerald-400"
                />
                 <StatCard 
                    title="Failed Jobs" 
                    value={rpaStats?.counts?.failed || 0}
                    subValue="Requires Attention"
                    icon={AlertCircle}
                    color="text-red-400"
                />
            </div>

            {/* Charts Area */}
            <div className="grid md:grid-cols-2 gap-8">
                {/* Token Usage Trend */}
                <div className="glass-card p-6 border border-white/5 rounded-xl">
                    <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                        <Server size={18} className="text-[#0a84ff]"/>
                        Token Consumption Trend
                    </h3>
                    <div className="h-64 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={llmStats?.daily_trend || []}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                                <XAxis dataKey="date" stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                                <Tooltip 
                                    contentStyle={{backgroundColor: '#0F1116', border: '1px solid #333', borderRadius: '8px'}}
                                    itemStyle={{color: '#fff'}}
                                />
                                <Line 
                                    type="monotone" 
                                    dataKey="tokens" 
                                    stroke="#6366f1" 
                                    strokeWidth={3} 
                                    dot={{fill: '#6366f1', r: 4}} 
                                    activeDot={{r: 6, stroke: '#fff'}}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* LLM Provider Distribution */}
                <div className="glass-card p-6 border border-white/5 rounded-xl">
                    <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                        <Database size={18} className="text-purple-400"/>
                        Model Usage Distribution
                    </h3>
                    <div className="space-y-4">
                        {Object.entries(llmStats?.by_provider || {}).map(([provider, tokens]: any, i) => (
                            <div key={i} className="group">
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="capitalize text-gray-300">{provider}</span>
                                    <span className="font-mono text-gray-500">{tokens} tokens</span>
                                </div>
                                <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                                    <div 
                                        className="h-full bg-gradient-to-r from-[#0a84ff] to-[#bf5af2]" 
                                        style={{width: `${(tokens / llmStats?.summary?.total_tokens) * 100}%`}}
                                    ></div>
                                </div>
                            </div>
                        ))}
                        {Object.keys(llmStats?.by_provider || {}).length === 0 && (
                            <div className="text-center text-gray-600 py-10">No usage data available</div>
                        )}
                    </div>
                </div>
            </div>

            {/* Logs Table */}
            <div className="glass-card border border-white/5 rounded-xl overflow-hidden">
                <div className="p-6 border-b border-white/5">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                        <FileJson size={18} className="text-gray-400"/>
                        Recent AI Audit Logs
                    </h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-white/5 text-gray-400 font-medium">
                            <tr>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4">Model</th>
                                <th className="px-6 py-4">Tokens (In/Out)</th>
                                <th className="px-6 py-4">Latency</th>
                                <th className="px-6 py-4">Time</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {recentLogs.map((log: any) => (
                                <tr key={log.id} className="hover:bg-white/5 transition-colors">
                                    <td className="px-6 py-4">
                                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
                                            ${log.status === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}
                                        `}>
                                            <div className={`w-1.5 h-1.5 rounded-full ${log.status === 'success' ? 'bg-green-500' : 'bg-red-500'}`}></div>
                                            {log.status === 'success' ? 'OK' : 'ERR'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 font-mono text-gray-300">{log.model}</td>
                                    <td className="px-6 py-4 text-gray-400">
                                        {log.input_tokens} / <span className="text-[#0a84ff]">{log.output_tokens}</span>
                                    </td>
                                    <td className="px-6 py-4 text-gray-400">{log.latency_ms}ms</td>
                                    <td className="px-6 py-4 text-gray-500 flex items-center gap-2">
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
                 <div className="glass-card border border-red-500/20 bg-red-500/5 rounded-xl p-6">
                    <h3 className="text-lg font-bold text-red-400 mb-4 flex items-center gap-2">
                        <AlertCircle size={18}/>
                        Recent RPA Failures
                    </h3>
                    <div className="space-y-3">
                        {rpaStats.recent_failures.map((fail: any, i:number) => (
                            <div key={i} className="flex items-start gap-3 p-3 bg-black/20 rounded border border-red-500/10">
                                <AlertCircle size={16} className="text-red-500 mt-1 shrink-0"/>
                                <div>
                                    <div className="text-sm font-bold text-gray-300">{fail.platform} Worker Error #{fail.id}</div>
                                    <div className="text-xs text-red-300/80 font-mono mt-1">{fail.msg}</div>
                                    <div className="text-xs text-gray-600 mt-1">{new Date(fail.time).toLocaleString()}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                 </div>
            )}
        </div>
    );
}
