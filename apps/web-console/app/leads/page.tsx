"use client";
import React, { useEffect, useState } from "react";
import { Inbox } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { Label } from "@/components/ui/label";
import api from "@/lib/api";
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from "@/components/ui/table";

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
  if (crm.job_status && crm.job_status !== 'succeeded') {
    const meta = CRM_LABELS[crm.job_status] || { label: crm.job_status, cls: 'text-text-secondary' };
    return <span className={meta.cls} title={crm.last_error || undefined}>{crm.synced ? '已交接 · 更新' : ''}{meta.label}</span>;
  }
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
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editing, setEditing] = useState<number | null | undefined>(undefined);
  const empty = { company: "", name: "", email: "", products: "", country: "", phone: "", conversation: "" };
  const [form, setForm] = useState(empty);
  function failure(err: any) {
    const detail = err.response?.data?.detail;
    setError(typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map(it => it.msg).join("；") : "操作失败，请检查服务后重试");
  }
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/api/v1/leads", { params: { status: status || undefined, q: q || undefined } });
      setItems(data.items || []);
    } catch (err) { failure(err); } finally { setLoading(false); }
  };
  useEffect(()=>{ load(); }, [status]);
  const setSt = async (id, s) => {
    setBusy(true); setError(""); setNotice("");
    try { await api.patch("/api/v1/leads/" + id, { status: s }); await load(); }
    catch (err) { failure(err); } finally { setBusy(false); }
  };
  const resync = async (id) => {
    setBusy(true); setError(""); setNotice("");
    try { await api.post(`/api/v1/crm/integration/leads/${id}/resync`); setNotice("已加入投递队列，实际同步结果请刷新查看"); await load(); }
    catch (err) { failure(err); } finally { setBusy(false); }
  };
  const exportCsv = async () => {
    setBusy(true); setError("");
    try {
      const { data } = await api.get("/api/v1/leads/export.csv", { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const a = document.createElement("a"); a.href = url; a.download = "leads.csv";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (err) { failure(err); } finally { setBusy(false); }
  };
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      if (editing === null) await api.post("/api/v1/leads", { ...form, source: "Manual" });
      else await api.patch(`/api/v1/leads/${editing}`, form);
      setEditing(undefined); setNotice("线索已保存"); await load();
    } catch (err) { failure(err); } finally { setBusy(false); }
  };
  return (
    <div className="min-h-screen bg-bg text-text p-8">
      <PageHeader
        title="本地线索池"
        description="AI 客服识别的询盘先落在这里。CRM 就绪后由投递器同步，无需返工。"
        actions={<div className="flex gap-2"><Button disabled={busy} onClick={() => { setForm(empty); setEditing(null); setError(""); setNotice(""); }}>新建线索</Button><Button disabled={busy} variant="outline" onClick={exportCsv}>导出 CSV</Button></div>}
      />
      {error && <p role="alert" className="mb-4 rounded-lg bg-danger/10 p-3 text-danger">{error}</p>}
      {notice && <p role="status" className="mb-4 text-success">{notice}</p>}
      {editing !== undefined && <form onSubmit={save} className="mb-6 space-y-4 rounded-xl border border-separator bg-surface p-5">
        <h2 className="text-lg font-semibold">{editing === null ? "新建线索" : "编辑线索"}</h2>
        <p className="text-sm text-text-secondary">至少填写公司、联系人或邮箱。同一企业的相同邮箱会合并更新。</p>
        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries({ company: "公司", name: "联系人", email: "邮箱", products: "产品", country: "国家/地区", phone: "电话" }).map(([key, label]) => <div key={key} className="space-y-2"><Label htmlFor={`lead-${key}`}>{label}</Label><Input id={`lead-${key}`} type={key === "email" ? "email" : "text"} value={form[key]} maxLength={key === "products" ? 2000 : key === "company" ? 300 : key === "email" ? 254 : 100} disabled={busy} onChange={e => setForm({ ...form, [key]: e.target.value })} /></div>)}
        </div>
        <div className="space-y-2"><Label htmlFor="lead-conversation">询盘记录</Label><textarea id="lead-conversation" className="min-h-24 w-full rounded-lg bg-surface-2 p-3" maxLength={20000} value={form.conversation} disabled={busy} onChange={e => setForm({ ...form, conversation: e.target.value })} /></div>
        <div className="flex gap-2"><Button type="submit" disabled={busy}>{busy ? "保存中…" : "保存线索"}</Button><Button type="button" variant="outline" disabled={busy} onClick={() => setEditing(undefined)}>取消</Button></div>
      </form>}
      <div className="flex gap-2 mb-4">
        <Input
          value={q}
          onChange={e=>setQ(e.target.value)}
          placeholder="搜索邮箱/公司/产品"
          aria-label="搜索线索"
          className="max-w-xs"
        />
        <Button onClick={load} disabled={loading}>搜索</Button>
        <Button variant="outline" onClick={load} disabled={loading}>刷新</Button>
        <select
          value={status}
          aria-label="线索状态"
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
        {loading ? <p role="status" className="p-5">正在加载线索…</p> : items.length ? (
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
                    <Button variant="secondary" size="sm" disabled={busy} onClick={() => { setForm(Object.fromEntries(Object.keys(empty).map(key => [key, it[key] || ""])) as typeof empty); setEditing(it.id); setError(""); setNotice(""); }}>编辑</Button>
                    {it.crm && !it.crm.synced && it.crm.job_status !== "pending" && it.crm.job_status !== "leased" && (
                      <Button variant="secondary" size="sm" disabled={busy} onClick={()=>resync(it.id)}>重投</Button>
                    )}
                    {ACTION_STATUSES.map(s=>(
                      <Button key={s} variant="secondary" size="sm" disabled={busy} onClick={()=>setSt(it.id,s)}>{STATUS_LABELS[s]}</Button>
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
