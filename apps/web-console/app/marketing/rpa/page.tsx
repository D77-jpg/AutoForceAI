"use client";
import React, { useEffect, useState } from "react";
import { Cpu, RefreshCw, CheckCircle, AlertTriangle, Clock } from "lucide-react";
import api from "../../../lib/api";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from "@/components/ui/table";

const STATUS_LABELS: Record<string, string> = {
  queued: "排队中",
  claimed: "执行中",
  running: "执行中",
  pending: "等待中",
  success: "成功",
  failed: "失败",
  paused: "已暂停",
};

const statusLabel = (s: string) => STATUS_LABELS[s] || s;

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
      <PageHeader
        title="RPA 执行"
        description="Worker 认领队列与海外渠道任务状态。详情请到营销矩阵。"
        className="mb-0"
        actions={
          <Button variant="outline" size="sm" onClick={load}>
            <RefreshCw size={12} className="mr-1" /> 刷新
          </Button>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Kpi icon={Cpu} label="执行中 / 排队" value={running} />
        <Kpi icon={Clock} label="队列" value={counts.queued || 0} />
        <Kpi icon={CheckCircle} label="成功" value={counts.success || 0} />
        <Kpi icon={AlertTriangle} label="失败" value={counts.failed || 0} />
      </div>

      <div className="glass-panel flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-10 text-center text-text-secondary">同步 Worker 状态...</div>
        ) : jobs.length === 0 ? (
          <EmptyState
            size="sm"
            icon={Cpu}
            title="暂无任务"
            description="从「海外投放」创建 LinkedIn / WordPress / X 任务"
          />
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>ID</TableHeaderCell>
                <TableHeaderCell>平台</TableHeaderCell>
                <TableHeaderCell>状态</TableHeaderCell>
                <TableHeaderCell>标题</TableHeaderCell>
                <TableHeaderCell className="text-right">时间</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobs.map((j) => (
                <TableRow key={j.id}>
                  <TableCell className="font-mono text-xs tabular-nums">#{j.id}</TableCell>
                  <TableCell>{j.platform}</TableCell>
                  <TableCell>{statusLabel(j.status)}</TableCell>
                  <TableCell className="truncate max-w-xs">{j.payload?.title || "—"}</TableCell>
                  <TableCell className="text-right text-xs text-text-secondary tabular-nums">
                    {j.created_at ? new Date(j.created_at).toLocaleString() : ""}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
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
      <div className="text-2xl font-bold mt-1 tabular-nums">{value}</div>
    </div>
  );
}
