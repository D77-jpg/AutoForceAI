"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink, RefreshCw, Settings } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function auth() {
  return { Authorization: "Bearer " + (localStorage.getItem("token") || "") };
}

// Genesis 八段状态中文标签（与 Genesis CUSTOMER_STATUS 对齐）
const FUNNEL_LABELS: Record<string, string> = {
  pending: "待开发",
  contacted: "已联系",
  replied: "已回复",
  interested: "有意向",
  quoting: "报价中",
  negotiating: "谈判中",
  won: "已成交",
  lost: "已流失",
};
const QUOTATION_LABELS: Record<string, string> = {
  draft: "草稿",
  sent: "已发送",
  negotiating: "谈判中",
  accepted: "已接受",
  rejected: "已拒绝",
  expired: "已过期",
};
const QUEUE_LABELS: Record<string, string> = {
  pending: "待投递",
  leased: "投递中",
  retrying: "重试中",
  succeeded: "已同步",
  dead: "死信",
};

export default function CrmPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(API + "/api/v1/crm/integration/overview", { headers: auth() });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "加载失败");
      setData(json);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const cfg = data?.config;
  const queue = data?.queue || {};
  const local = data?.local || {};
  const genesis = data?.genesis;

  return (
    <div className="min-h-screen bg-bg text-text p-8">
      <PageHeader
        title="CRM 集成门户"
        description="获客线索在此交接给 Genesis_CRM；销售进展以 Genesis 为准，此处只读摘要。"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={load} disabled={loading}>
              <RefreshCw size={16} className="mr-2" />刷新
            </Button>
            <Link href="/crm/settings">
              <Button variant="outline"><Settings size={16} className="mr-2" />集成设置</Button>
            </Link>
            <Link href="/leads">
              <Button>本地线索池</Button>
            </Link>
          </div>
        }
      />

      {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

      {!cfg && data && (
        <div className="bg-surface border border-border rounded-lg p-8 text-center max-w-xl">
          <p className="text-text-secondary mb-4">
            尚未配置 Genesis_CRM 连接。配置后，合格线索将可靠投递到 CRM，成交结果自动回流归因。
          </p>
          <Link href="/crm/settings"><Button>去配置集成</Button></Link>
        </div>
      )}

      {cfg && (
        <div className="space-y-6">
          {/* 连接状态 + 队列计数 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-surface border border-border rounded-lg p-5 shadow-card">
              <h3 className="font-medium mb-3">连接状态</h3>
              <div className="text-sm space-y-1 text-text-secondary">
                <p>项目：{cfg.project_name || cfg.project_id} · 契约 v{cfg.contract_version}</p>
                <p>
                  健康：
                  <span className={cfg.last_health_status === "ok" ? "text-green-500" : cfg.last_health_status === "auth_invalid" ? "text-red-500" : ""}>
                    {" "}{cfg.last_health_status || "未测试"}
                  </span>
                  {cfg.last_health_checked_at && ` · ${new Date(cfg.last_health_checked_at).toLocaleString()}`}
                </p>
                <p>投递：{cfg.enabled ? "已启用" : "已停用"} · 最近回流：{cfg.outcome_polled_at ? new Date(cfg.outcome_polled_at).toLocaleString() : "—"}</p>
                {cfg.last_health_detail && <p className="text-xs">{cfg.last_health_detail}</p>}
              </div>
            </div>
            <div className="bg-surface border border-border rounded-lg p-5 shadow-card">
              <h3 className="font-medium mb-3">投递队列</h3>
              <div className="flex flex-wrap gap-4 text-sm">
                {Object.entries(QUEUE_LABELS).map(([k, label]) => (
                  <div key={k} className="text-center">
                    <div className={`text-xl font-semibold ${k === "dead" && queue[k] > 0 ? "text-red-500" : ""}`}>
                      {queue[k] || 0}
                    </div>
                    <div className="text-text-secondary text-xs">{label}</div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-text-secondary mt-3">
                已交接客户 {local.synced_total || 0} · 成交 {local.won || 0} · 流失 {local.lost || 0}
              </p>
            </div>
          </div>

          {/* Genesis 实时漏斗 */}
          <div className="bg-surface border border-border rounded-lg p-5 shadow-card">
            <h3 className="font-medium mb-3">Genesis 销售漏斗（实时）</h3>
            {genesis ? (
              <>
                <div className="flex flex-wrap gap-3">
                  {genesis.funnel.map((s: any) => (
                    <div key={s.status} className="bg-surface-2 rounded-lg px-4 py-3 text-center min-w-[88px]">
                      <div className={`text-xl font-semibold ${s.status === "won" ? "text-green-500" : ""}`}>{s.count}</div>
                      <div className="text-xs text-text-secondary">{FUNNEL_LABELS[s.status] || s.status}</div>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-text-secondary mt-3">
                  客户总数 {genesis.totalCustomers} · 报价：
                  {(genesis.quotations || []).map((q: any) => `${QUOTATION_LABELS[q.status] || q.status} ${q.count}`).join(" / ")}
                  {" · "}生成于 {new Date(genesis.generatedAt).toLocaleString()}
                </p>
              </>
            ) : (
              <p className="text-sm text-text-secondary">
                {data?.genesis_error ? `Genesis 暂不可达：${data.genesis_error}` : "加载中…"}
              </p>
            )}
          </div>

          {/* 最近同步线索 */}
          <div className="bg-surface border border-border rounded-lg p-5 shadow-card">
            <h3 className="font-medium mb-3">最近同步线索</h3>
            {data?.recent_synced?.length ? (
              <div className="divide-y divide-separator">
                {data.recent_synced.map((r: any) => (
                  <div key={r.remote_customer_id} className="py-2 flex items-center justify-between text-sm">
                    <span>
                      {r.company || r.name || `线索 #${r.lead_id}`}
                      <span className="text-text-secondary ml-2">
                        {FUNNEL_LABELS[r.remote_status] || r.remote_status || "已同步"}
                      </span>
                    </span>
                    <a
                      href={r.genesis_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-accent inline-flex items-center gap-1 hover:underline"
                    >
                      在 Genesis 中打开 <ExternalLink size={13} />
                    </a>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-secondary">暂无已同步线索。新询盘入库后由投递器自动交接。</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
