"use client";
import React, { useEffect, useState } from 'react';
import { Activity, Server, Cpu, Database, Users, Box, Zap, Clock } from 'lucide-react';
import api from '@/lib/api';

export default function MonitorPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const res = await api.get('/api/v1/monitor/system');
      setStats(res.data);
    } catch (err) {
      console.error(err);
    } finally {
        setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-full w-full p-6 text-text flex flex-col overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
            <div>
                 <h1 className="text-2xl font-bold text-white">系统监控 (System Monitor)</h1>
                 <p className="text-sm text-text-secondary">实时服务器状态与资源概览。</p>
            </div>
            <div className="flex items-center gap-2 text-xs text-text-secondary">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
                </span>
                Live Updates (5s)
            </div>
        </div>
        
        {loading && !stats ? (
             <div className="flex-1 flex items-center justify-center text-text-secondary">
                <Activity className="animate-pulse mr-2" /> Connecting to telemetry...
             </div>
        ) : (
            <div className="space-y-6">
                {/* Hardware Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {/* CPU */}
                    <div className="bg-surface border border-separator p-4 rounded-xl">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="p-2 bg-accent/10 text-accent rounded-lg">
                                <Cpu size={20} />
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-text">CPU 使用率</h3>
                                <p className="text-xs text-text-secondary">{stats?.system_info?.platform || 'Linux'} Server</p>
                            </div>
                        </div>
                        <div className="flex items-end gap-2 mb-2">
                             <span className="text-2xl font-bold text-white">{stats?.cpu_usage}%</span>
                             <span className="text-xs text-text-secondary mb-1">Load</span>
                        </div>
                        <div className="w-full bg-text/5 rounded-full h-1.5 overflow-hidden">
                            <div 
                                className={`h-full rounded-full transition-all duration-500 ${stats?.cpu_usage > 80 ? 'bg-danger' : 'bg-accent'}`} 
                                style={{ width: `${stats?.cpu_usage}%` }}
                            ></div>
                        </div>
                    </div>

                    {/* Memory */}
                    <div className="bg-surface border border-separator p-4 rounded-xl">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="p-2 bg-danger/10 text-danger rounded-lg">
                                <Database size={20} />
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-text">内存状态</h3>
                                <p className="text-xs text-text-secondary">RAM Allocation</p>
                            </div>
                        </div>
                        <div className="flex items-end gap-2 mb-2">
                             <span className="text-2xl font-bold text-white">{stats?.memory_usage?.percent}%</span>
                             <span className="text-xs text-text-secondary mb-1">
                                {(stats?.memory_usage?.used / 1024 / 1024 / 1024 || 0).toFixed(1)}GB / 
                                {(stats?.memory_usage?.total / 1024 / 1024 / 1024 || 0).toFixed(1)}GB
                             </span>
                        </div>
                        <div className="w-full bg-text/5 rounded-full h-1.5 overflow-hidden">
                            <div 
                                className={`h-full rounded-full transition-all duration-500 ${stats?.memory_usage?.percent > 80 ? 'bg-danger' : 'bg-danger'}`} 
                                style={{ width: `${stats?.memory_usage?.percent}%` }}
                            ></div>
                        </div>
                    </div>

                     {/* Platform Info */}
                     <div className="bg-surface border border-separator p-4 rounded-xl">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="p-2 bg-success/10 text-success rounded-lg">
                                <Server size={20} />
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-text">系统环境</h3>
                                <p className="text-xs text-text-secondary">Environment Info</p>
                            </div>
                        </div>
                        <div className="space-y-2">
                             <div className="flex justify-between text-xs">
                                 <span className="text-text-secondary">OS Release</span>
                                 <span className="text-text font-mono">{stats?.system_info?.release || '-'}</span>
                             </div>
                             <div className="flex justify-between text-xs">
                                 <span className="text-text-secondary">Python Runtime</span>
                                 <span className="text-text font-mono">{stats?.system_info?.python_version || '-'}</span>
                             </div>
                             <div className="flex justify-between text-xs">
                                 <span className="text-text-secondary">API Status</span>
                                 <span className="text-success flex items-center gap-1">
                                     <span className="w-1.5 h-1.5 rounded-full bg-success"></span> Online
                                 </span>
                             </div>
                        </div>
                    </div>
                </div>

                {/* DB Stats Grid */}
                <h3 className="text-text-secondary text-sm font-medium mt-6 mb-4">业务指标 (Business Metrics)</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                     <StatCard label="活跃模型" value={stats?.resources?.active_models} icon={<Box size={16}/>} color="text-accent" />
                     <StatCard label="活跃用户" value={stats?.resources?.active_users} icon={<Users size={16}/>} color="text-accent" />
                     <StatCard label="RPA 任务队列" value={stats?.resources?.queued_jobs} icon={<Clock size={16}/>} color="text-warning" />
                     <StatCard label="服务状态" value="Normal" icon={<Activity size={16}/>} color="text-success" valueClass="text-success text-lg" />
                </div>
            </div>
        )}
    </div>
  )
}

function StatCard({ label, value, icon, color, valueClass }: any) {
    return (
        <div className="bg-surface border border-separator p-4 rounded-xl flex flex-col justify-between h-24">
            <div className={`flex items-center gap-2 text-xs font-medium ${color}`}>
                {icon} {label}
            </div>
            <div className={valueClass || "text-2xl font-bold text-white font-mono"}>
                {value ?? '-'}
            </div>
        </div>
    )
}
