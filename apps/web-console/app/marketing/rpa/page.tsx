"use client";
import React, { useEffect, useState } from "react";
import { Cpu, RefreshCw, CheckCircle, AlertTriangle, Clock } from "lucide-react";
import api from "../../../lib/api";
import Link from "next/link";

export default function RPAPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [j, s] = await Promise.all([
        api.get("/api/v1/rpa/jobs?limit=30&exclude_job_type=view_browser"),
        api.get("/api/v1/monitor/rpa/stats").catch(() => ({ data: null })),
      ]);
      const items = Array.isArray(j.data) ? j.data : j.data.items || [];
      setJobs(items);
      setStats(s.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  const counts = stats?.counts || {};
  const running = jobs.filter((j) => j.status === "claimed" || j.status === "queued").length;

  return (
    <div className="h-full w-full p-6 text-text flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">RPA 执行</h1>
          <p className="text-sm text-text-secondary">Worker 认领队列与海外渠道任务状态。详情请到营销矩阵。</p>
        </div>
        <button onClick={load} className="px-3 py-2 text-xs rounded bg-text/10 hover:bg-text/15 flex items-center gap-1">
          <RefreshCw size={12} /> 刷新
        </button>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <Kpi icon={Cpu} label="执行中 / 排队" value={running} />
        <Kpi icon={Clock} label="队列" value={counts.queued || 0} />
        <Kpi icon={CheckCircle} label="成功" value={counts.success || 0} />
        <Kpi icon={AlertTriangle} label="失败" value={counts.failed || 0} />
      </div>

      <div className="glass-panel flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-10 text-center text-text-secondary">同步 Worker 状态...</div>
        ) : jobs.length === 0 ? (
          <div className="p-10 text-center text-text-secondary">暂无任务。从「海外投放」创建 LinkedIn / WordPress / X 任务。</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-xs text-text-secondary uppercase">
              <tr>
                <th className="p-3 text-left">ID</th>
                <th className="p-3 text-left">平台</th>
                <th className="p-3 text-left">状态</th>
                <th className="p-3 text-left">标题</th>
                <th className="p-3 text-right">时间</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id} className="border-t border-separator">
                  <td className="p-3 font-mono text-xs">#{j.id}</td>
                  <td className="p-3">{j.platform}</td>
                  <td className="p-3">{j.status}</td>
                  <td className="p-3 truncate max-w-xs">{j.payload?.title || "—"}</td>
                  <td className="p-3 text-right text-xs text-text-secondary">
                    {j.created_at ? new Date(j.created_at).toLocaleString() : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <Link href="/distribution" className="text-xs text-accent hover:underline">
        打开营销矩阵查看实时日志 →
      </Link>
    </div>
  );
}

function Kpi({ icon: Icon, label, value }: any) {
  return (
    <div className="glass-panel p-4">
      <div className="text-[10px] uppercase text-text-secondary flex items-center gap-1">
        <Icon size={12} /> {label}
      </div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  );
}
