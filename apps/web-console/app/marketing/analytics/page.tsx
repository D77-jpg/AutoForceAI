"use client";
import React, { useEffect, useState } from "react";
import { BarChart4, RefreshCw, Share2, Users, Loader2 } from "lucide-react";
import api from "../../../lib/api";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

export default function AnalyticsPage() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState("");

  const load = async () => {
    try {
      const res = await api.get("/api/v1/marketing/funnel?days=30");
      setData(res.data);
      setErr("");
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "无法加载漏斗");
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (!data) {
    if (err) {
      return (
        <EmptyState
          size="lg"
          icon={BarChart4}
          title="无法加载漏斗数据"
          description={err}
          actionLabel="重试"
          onAction={load}
        />
      );
    }
    return (
      <div className="h-full flex items-center justify-center">
        <EmptyState
          size="sm"
          icon={Loader2}
          title="加载漏斗数据"
          description="正在同步近 30 天漏斗指标..."
        />
      </div>
    );
  }

  return (
    <div className="h-full w-full p-6 text-text flex flex-col gap-4 overflow-y-auto">
      <PageHeader
        title="获客漏斗"
        description="内容 → 发布 → GEO 曝光 → 本地询盘。CRM 归因待阶段 2。"
        className="mb-0 shrink-0"
        actions={
          <Button variant="outline" size="sm" onClick={load}>
            <RefreshCw size={12} strokeWidth={1.75} className="mr-1" /> 刷新
          </Button>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {data.steps.map((s: any) => (
          <div key={s.key} className="glass-panel p-4">
            <div className="text-[10px] text-text-secondary">{s.label}</div>
            <div className="text-3xl font-bold mt-1 tabular-nums">{s.value === null ? "—" : s.value}</div>
            <div className="text-[11px] text-text-secondary mt-1">{s.hint}</div>
          </div>
        ))}
      </div>

      <div className="glass-panel p-4 h-64">
        <div className="text-xs text-text-secondary mb-2">近两周趋势</div>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data.trend || []}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--ui-text-tertiary))" opacity={0.3} />
            <XAxis dataKey="date" stroke="rgb(var(--ui-text-secondary))" fontSize={10} />
            <YAxis stroke="rgb(var(--ui-text-secondary))" fontSize={10} />
            <Tooltip contentStyle={{ background: "rgb(var(--ui-surface))", borderColor: "rgb(var(--ui-separator) / var(--ui-separator-alpha))" }} />
            <Area type="monotone" dataKey="content" name="内容" stroke="rgb(var(--ui-warning))" fill="rgb(var(--ui-warning))" fillOpacity={0.15} />
            <Area type="monotone" dataKey="publish" name="发布" stroke="rgb(var(--ui-accent))" fill="rgb(var(--ui-accent))" fillOpacity={0.15} />
            <Area type="monotone" dataKey="mentions" name="曝光" stroke="rgb(var(--ui-success))" fill="rgb(var(--ui-success))" fillOpacity={0.15} />
            <Area type="monotone" dataKey="leads" name="询盘" stroke="rgb(var(--ui-accent-hover))" fill="rgb(var(--ui-accent-hover))" fillOpacity={0.15} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-panel p-4">
          <h3 className="text-sm font-bold mb-3">渠道发布</h3>
          {Object.keys(data.by_platform || {}).length === 0 && (
            <EmptyState size="sm" icon={Share2} title="暂无发布任务" description="从「海外投放」创建任务后可在此查看渠道数据" />
          )}
          {Object.entries(data.by_platform || {}).map(([k, v]: any) => (
            <div key={k} className="flex justify-between text-xs py-1 border-b border-separator">
              <span>{k}</span>
              <span>
                {v.success}/{v.total} 成功 · {v.failed} 失败
              </span>
            </div>
          ))}
        </div>
        <div className="glass-panel p-4">
          <h3 className="text-sm font-bold mb-3">最近询盘（本地线索池）</h3>
          {(data.recent_leads || []).length === 0 && (
            <EmptyState size="sm" icon={Users} title="暂无线索" description="GEO 曝光转化出的本地询盘将显示在这里" />
          )}
          {(data.recent_leads || []).map((l: any) => (
            <div key={l.id} className="text-xs py-1 border-b border-separator">
              <span className="text-text">{l.email || l.company || "匿名"}</span>
              <span className="text-text-secondary ml-2">{l.source}</span>
              <span className="text-text-tertiary ml-2">{l.products}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
