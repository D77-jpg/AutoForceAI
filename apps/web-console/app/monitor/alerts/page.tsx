"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, ArrowLeft, Loader2, RefreshCw } from "lucide-react";
import api from "../../../lib/api";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/ui/empty-state";

type AlertRecord = {
    id: string;
    source: string;
    severity: string;
    status: string;
    first_seen_at: string | null;
    last_seen_at: string | null;
    summary: string;
    occurrences?: number;
    occurrence_count?: number;
};

type AlertList = { items: AlertRecord[]; total: number };
type AlertAction = "ack" | "resolve";

const severityLabels: Record<string, string> = {
    critical: "严重", high: "高", warning: "警告", medium: "中", low: "低", info: "提示",
};
const statusLabels: Record<string, string> = {
    open: "待处理", acknowledged: "已确认", resolved: "已解决",
};

function formatTime(value: string | null) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("zh-CN");
}

export default function AlertsPage() {
    const [data, setData] = useState<AlertList | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [actionError, setActionError] = useState<string | null>(null);
    const [pendingId, setPendingId] = useState<string | null>(null);

    const load = useCallback(async (signal?: AbortSignal) => {
        const response = await api.get<AlertList>("/api/v1/monitor/alerts", { signal });
        if (!response.data || !Array.isArray(response.data.items) || typeof response.data.total !== "number") {
            throw new Error("Invalid alerts response");
        }
        setData(response.data);
        setError(null);
        setActionError(null);
    }, []);

    useEffect(() => {
        const controller = new AbortController();
        load(controller.signal).catch(() => {
            if (!controller.signal.aborted) setError("告警加载失败，请检查连接或稍后重试。");
        }).finally(() => {
            if (!controller.signal.aborted) setLoading(false);
        });
        return () => controller.abort();
    }, [load]);

    const refresh = async () => {
        setRefreshing(true);
        try {
            await load();
        } catch {
            setError("告警刷新失败，当前列表可能不是最新状态。");
        } finally {
            setRefreshing(false);
        }
    };

    const performAction = async (alert: AlertRecord, action: AlertAction) => {
        setPendingId(alert.id);
        setActionError(null);
        try {
            await api.post(`/api/v1/monitor/alerts/${encodeURIComponent(alert.id)}/${action}`);
            // Never change the local status based on a click or a POST alone.
            await load();
        } catch {
            setActionError("操作或状态同步失败，请刷新列表核实后再试。");
        } finally {
            setPendingId(null);
        }
    };

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-6 animate-fade-in-up">
            <Link href="/monitor" className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-accent">
                <ArrowLeft size={16} /> 返回系统监控
            </Link>
            <PageHeader title="告警记录" description="查看持久化告警及其确认、解决状态" className="mb-0" actions={
                <button type="button" onClick={refresh} disabled={loading || refreshing || pendingId !== null}
                    className="inline-flex items-center gap-2 rounded-md border border-separator px-3 py-2 text-sm text-text hover:bg-text/5 disabled:opacity-50">
                    <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} /> 刷新
                </button>
            } />
            {error && <div role="alert" className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div>}
            {actionError && <div role="alert" className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{actionError}</div>}
            {loading ? (
                <div role="status" className="flex items-center justify-center gap-2 rounded-lg bg-surface py-20 text-text-secondary">
                    <Loader2 size={20} className="animate-spin" /> 正在加载告警…
                </div>
            ) : !data ? (
                <EmptyState icon={AlertCircle} title="无法获取告警记录" description="请稍后重试。" actionLabel="重试" onAction={refresh} />
            ) : data.items.length === 0 ? (
                <EmptyState icon={AlertCircle} title={error ? "无法确认当前告警状态" : "暂无告警"} description={error ? "上次成功加载时没有告警，请刷新后核实。" : "目前没有告警记录。"} />
            ) : (
                <section className="rounded-lg bg-surface shadow-card overflow-hidden" aria-label="告警列表">
                    <div className="border-b border-separator px-6 py-4 text-sm text-text-secondary">共 {data.total} 条告警{error ? "（以下为上次成功加载的记录）" : ""}</div>
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[1000px] text-left text-sm">
                            <thead className="bg-text/5 text-text-secondary"><tr>
                                <th scope="col" className="px-4 py-3">时间（最近）</th>
                                <th scope="col" className="px-4 py-3">来源</th>
                                <th scope="col" className="px-4 py-3">严重度</th>
                                <th scope="col" className="px-4 py-3">状态</th>
                                <th scope="col" className="px-4 py-3">首次 / 最近发生</th>
                                <th scope="col" className="px-4 py-3">脱敏摘要</th>
                                <th scope="col" className="px-4 py-3">次数</th>
                                <th scope="col" className="px-4 py-3">操作</th>
                            </tr></thead>
                            <tbody className="divide-y divide-separator">
                                {data.items.map((alert) => (
                                    <tr key={alert.id} className="align-top">
                                        <td className="px-4 py-4 whitespace-nowrap text-text-secondary">{formatTime(alert.last_seen_at)}</td>
                                        <td className="px-4 py-4 break-words max-w-32">{alert.source || "—"}</td>
                                        <td className="px-4 py-4 whitespace-nowrap"><span className={alert.severity === "critical" || alert.severity === "high" ? "text-danger font-semibold" : "text-text-secondary"}>{severityLabels[alert.severity] || alert.severity || "—"}</span></td>
                                        <td className="px-4 py-4 whitespace-nowrap">{statusLabels[alert.status] || alert.status || "—"}</td>
                                        <td className="px-4 py-4 whitespace-nowrap text-text-secondary">{formatTime(alert.first_seen_at)}<br />{formatTime(alert.last_seen_at)}</td>
                                        <td className="px-4 py-4 max-w-sm break-words whitespace-pre-wrap">{alert.summary || "—"}</td>
                                        <td className="px-4 py-4 tabular-nums">{alert.occurrences ?? alert.occurrence_count ?? "—"}</td>
                                        <td className="px-4 py-4 whitespace-nowrap">
                                            <div className="flex gap-2">
                                                {alert.status === "open" && <button type="button" disabled={pendingId !== null || refreshing || !!error} onClick={() => performAction(alert, "ack")}
                                                    className="rounded-md border border-separator px-2 py-1 text-accent hover:bg-text/5 disabled:opacity-50">{pendingId === alert.id ? "处理中…" : "确认"}</button>}
                                                {(alert.status === "open" || alert.status === "acknowledged") && <button type="button" disabled={pendingId !== null || refreshing || !!error} onClick={() => performAction(alert, "resolve")}
                                                    className="rounded-md border border-separator px-2 py-1 text-accent hover:bg-text/5 disabled:opacity-50">{pendingId === alert.id ? "处理中…" : "解决"}</button>}
                                                {alert.status === "resolved" && <span className="text-text-tertiary">已解决</span>}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>
            )}
        </div>
    );
}
