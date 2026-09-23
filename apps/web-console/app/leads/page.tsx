"use client";
import React, { useEffect, useState } from "react";
import { Inbox } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from "@/components/ui/table";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function auth(){ return { Authorization: "Bearer " + (localStorage.getItem("token")||"") }; }

const STATUS_LABELS: Record<string, string> = {
  new: "新线索",
  contacted: "已联系",
  converted: "已转化",
  dropped: "已放弃",
};
const ACTION_STATUSES = ["contacted", "converted", "dropped"];

// CRM 同步状态（Wave C）
const CRM_LABELS: Record<string, { label: string; cls: string }> = {
  succeeded: { label: "已同步", cls: "text-green-500" },
  pending: { label: "待投递", cls: "text-text-secondary" },
  leased: { label: "投递中", cls: "text-accent" },
  retrying: { label: "重试中", cls: "text-amber-500" },
  dead: { label: "死信", cls: "text-red-500" },
};

function CrmBadge({ crm }: { crm: any }) {
  if (!crm || (!crm.job_status && !crm.synced)) return <span className="text-text-secondary">-</span>;
  if (crm.synced) {
    return (
      <span className="text-green-500" title={`Genesis 客户 ${crm.remote_customer_id || ""}`}>
        已同步{crm.remote_status ? ` · ${crm.remote_status}` : ""}
      </span>
    );
  }
  const meta = CRM_LABELS[crm.job_status] || { label: crm.job_status, cls: "text-text-secondary" };
  return (
    <span className={meta.cls} title={crm.last_error || undefined}>
      {meta.label}
    </span>
  );
}

export default function LeadsPage() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const load = async () => {
    const u = new URL(API + "/api/v1/leads");
    if (status) u.searchParams.set("status", status);
    if (q) u.searchParams.set("q", q);
    const res = await fetch(u.toString(), { headers: auth() });
    const data = await res.json();
    setItems(data.items || []);
  };
  useEffect(()=>{ load(); }, [status]);
  const setSt = async (id, s) => {
    await fetch(API+"/api/v1/leads/"+id, { method:"PATCH", headers:{...auth(),"Content-Type":"application/json"}, body: JSON.stringify({status:s}) });
    load();
  };
  const resync = async (id) => {
    await fetch(API+`/api/v1/crm/integration/leads/${id}/resync`, { method:"POST", headers: auth() });
    load();
  };
  const exportCsv = () => {
    fetch(API+"/api/v1/leads/export.csv", { headers: auth() }).then(r=>r.blob()).then(b=>{
      const a=document.createElement("a"); a.href=URL.createObjectURL(b); a.download="leads.csv"; a.click();
    });
  };
  return (
    <div className="min-h-screen bg-bg text-text p-8">
      <PageHeader
        title="本地线索池"
        description="AI 客服识别的询盘先落在这里。CRM 就绪后由投递器同步，无需返工。"
        actions={<Button variant="outline" onClick={exportCsv}>导出 CSV</Button>}
      />
      <div className="flex gap-2 mb-4">
        <Input
          value={q}
          onChange={e=>setQ(e.target.value)}
          placeholder="搜索邮箱/公司/产品"
          className="max-w-xs"
        />
        <Button onClick={load}>搜索</Button>
        <select
          value={status}
          onChange={e=>setStatus(e.target.value)}
          className="h-10 rounded-md border border-transparent bg-surface-2 px-3 text-sm text-text focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-accent/30 transition-all"
        >
          <option value="">全部状态</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>
      <div className="bg-surface border border-separator rounded-xl">
        {items.length ? (
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>公司/联系人</TableHeaderCell>
                <TableHeaderCell>邮箱</TableHeaderCell>
                <TableHeaderCell>产品</TableHeaderCell>
                <TableHeaderCell>来源</TableHeaderCell>
                <TableHeaderCell>状态</TableHeaderCell>
                <TableHeaderCell>CRM 同步</TableHeaderCell>
                <TableHeaderCell className="text-right">操作</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map(it=>(
                <TableRow key={it.id}>
                  <TableCell>{it.company || "-"} / {it.name || "-"}</TableCell>
                  <TableCell>{it.email || "-"}</TableCell>
                  <TableCell>{it.products || (it.intent_json && it.intent_json.intent) || "-"}</TableCell>
                  <TableCell>{it.source}</TableCell>
                  <TableCell>{STATUS_LABELS[it.status] || it.status}</TableCell>
                  <TableCell><CrmBadge crm={it.crm} /></TableCell>
                  <TableCell className="text-right space-x-1">
                    {it.crm && !it.crm.synced && it.crm.job_status !== "pending" && it.crm.job_status !== "leased" && (
                      <Button variant="secondary" size="sm" onClick={()=>resync(it.id)}>重投</Button>
                    )}
                    {ACTION_STATUSES.map(s=>(
                      <Button key={s} variant="secondary" size="sm" onClick={()=>setSt(it.id,s)}>{STATUS_LABELS[s]}</Button>
                    ))}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyState
            icon={Inbox}
            size="sm"
            title="暂无线索"
            description="嵌入独立站聊天插件或在检索测试后产生询盘即可入库。"
          />
        )}
      </div>
    </div>
  );
}
