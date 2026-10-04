"use client";
import React, { useEffect, useRef, useState } from "react";
import { Upload, Database, RefreshCw, Trash2, FileText, Plus } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/ui/empty-state";
import { Modal } from "@/components/ui/modal";
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// Same-origin by default: Next.js and nginx both proxy /api to the backend, so a
// build without NEXT_PUBLIC_API_URL never makes a visitor call their own localhost.
const API = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
function token() { return typeof window !== "undefined" ? localStorage.getItem("token") : null; }
function auth() { return { Authorization: "Bearer " + (token() || "") }; }

const STATUS_LABELS: Record<string, string> = {
  indexed: "已索引",
  embedded: "已向量化",
  parsing: "解析中",
  processing: "处理中",
  pending: "排队中",
  failed: "失败",
};
function statusLabel(s: string) { return STATUS_LABELS[s] ?? s; }

export default function KnowledgePage() {
  const [kbs, setKbs] = useState([]);
  const [active, setActive] = useState(null);
  const [docs, setDocs] = useState([]);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState([]);
  const [newName, setNewName] = useState("");
  const [msg, setMsg] = useState("");
  const [embedder, setEmbedder] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const request = async (path: string, options: RequestInit = {}) => {
    const response = await fetch(API + path, { ...options, headers: { ...auth(), ...options.headers } });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "操作失败，请检查输入或重新登录");
    return data;
  };
  const errorMessage = (error: unknown) => error instanceof Error ? error.message : "请求失败，请检查网络后重试";

  const loadKbs = async () => {
    try {
      const data = await request("/api/v1/kb/bases");
      setKbs(data.items || []);
      if (!active && data.items?.length) setActive(data.items[0].id);
    } catch (error) { setMsg(errorMessage(error)); }
  };
  const loadDocs = async (id) => {
    if (!id) return;
    try {
      const data = await request("/api/v1/kb/bases/" + id + "/docs");
      setDocs(data.items || []);
    } catch (error) { setMsg(errorMessage(error)); }
  };
  useEffect(() => { loadKbs(); }, []);
  useEffect(() => { loadDocs(active); }, [active]);
  useEffect(() => {
    if (!active || !docs.some(d => ["pending", "parsing", "processing"].includes(d.status))) return;
    const timer = setInterval(() => loadDocs(active), 3000);
    return () => clearInterval(timer);
  }, [active, docs]);

  const createKb = async () => {
    if (!newName.trim()) return;
    setBusy(true);
    try {
      await request("/api/v1/kb/bases", {
        method: "POST", headers: { ...auth(), "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName, is_public: true })
      });
      setNewName("");
      setCreateOpen(false);
      loadKbs();
      setMsg("知识库已创建");
    } catch (error) { setMsg(errorMessage(error)); }
    finally { setBusy(false); }
  };
  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !active) return;
    const fd = new FormData();
    fd.append("file", file);
    setMsg("正在上传并解析...");
    setBusy(true);
    try {
      await request("/api/v1/kb/bases/" + active + "/docs", { method: "POST", body: fd });
      setMsg("文件已上传，正在解析；文档列表将自动更新状态");
      await loadDocs(active);
      await loadKbs();
    } catch (error) { setMsg(errorMessage(error)); }
    finally { setBusy(false); e.target.value = ""; }
  };
  const search = async () => {
    if (!query.trim()) return setMsg("请填写检索问题");
    setBusy(true);
    setMsg("");
    try {
      const data = await request("/api/v1/kb/search", {
        method: "POST", headers: { ...auth(), "Content-Type": "application/json" },
        body: JSON.stringify({ query, kb_ids: active ? [active] : null, score_threshold: 0.1 })
      });
      setHits(data.hits || []);
      setEmbedder(data.embedder);
      if (!data.hits?.length) setMsg("没有检索到相关文档，请调整问题或检查文档状态");
    } catch (error) { setHits([]); setMsg(errorMessage(error)); }
    finally { setBusy(false); }
  };
  const reindex = async (id) => {
    setBusy(true);
    try {
      await request("/api/v1/kb/docs/" + id + "/reindex", { method: "POST" });
      setMsg("已提交重新索引");
      await loadDocs(active);
    } catch (error) { setMsg(errorMessage(error)); }
    finally { setBusy(false); }
  };
  const remove = async (id) => {
    setBusy(true);
    try {
      await request("/api/v1/kb/docs/" + id, { method: "DELETE" });
      setMsg("文档已删除");
      await loadDocs(active);
      await loadKbs();
    } catch (error) { setMsg(errorMessage(error)); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-bg text-text p-8">
      <div className="max-w-7xl mx-auto">
        <PageHeader
          title="知识文档"
          description="上传产品资料 / FAQ / 证书，供 AI 客服检索。无嵌入密钥时自动走词法检索。"
          actions={<Button onClick={() => setCreateOpen(true)}><Plus size={16} strokeWidth={1.75} className="mr-1.5" />新建知识库</Button>}
        />
        {msg && <div role="status" className="text-sm text-warning mb-4">{msg}</div>}
        {!kbs.length ? (
          <EmptyState
            icon={Database}
            title="还没有知识库"
            description="先创建一个知识库，再上传产品资料、FAQ 或证书，供 AI 客服检索使用。"
            actionLabel="新建知识库"
            onAction={() => setCreateOpen(true)}
            size="lg"
          />
        ) : (
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-3">
            <div className="bg-surface border border-separator rounded-xl p-2 space-y-1">
              {kbs.map(kb => (
                <button key={kb.id} onClick={()=>setActive(kb.id)} className={"w-full text-left p-3.5 rounded-lg border transition-colors " + (active===kb.id ? "border-accent/40 bg-accent/10" : "border-transparent hover:bg-surface-2")}>
                  <div className="font-medium text-text">{kb.name}</div>
                  <div className="text-xs text-text-tertiary mt-1 tabular-nums">{kb.doc_count} 文档 · {kb.chunk_count} 分块 {kb.is_public ? "· 公开" : ""}</div>
                </button>
              ))}
            </div>
          </div>
          <div className="col-span-9 space-y-6">
            <div className="bg-surface border border-separator rounded-xl p-5">
              <div className="flex justify-between items-center mb-4">
                <h2 className="font-semibold tracking-tight">文档列表</h2>
                <input ref={fileRef} type="file" className="hidden" accept=".pdf,.docx,.txt,.md" onChange={upload}/>
                <Button disabled={busy} variant="secondary" onClick={() => fileRef.current?.click()}><Upload size={14} strokeWidth={1.75} className="mr-1.5"/> 上传 PDF / Word / MD</Button>
              </div>
              {docs.length ? (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>文件</TableHeaderCell>
                    <TableHeaderCell className="text-center">状态</TableHeaderCell>
                    <TableHeaderCell className="text-center">分块数</TableHeaderCell>
                    <TableHeaderCell />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {docs.map(d => (
                    <TableRow key={d.id}>
                      <TableCell><span className="flex items-center gap-2"><FileText size={14} strokeWidth={1.75} className="text-text-secondary"/> {d.filename}</span></TableCell>
                      <TableCell className="text-center">{statusLabel(d.status)}{d.error_msg ? <span className="block text-xs text-warning">{d.error_msg}</span> : null}</TableCell>
                      <TableCell className="text-center tabular-nums">{d.chunk_count}</TableCell>
                      <TableCell className="text-right">
                        <button disabled={busy} aria-label={`重新索引 ${d.filename}`} onClick={()=>reindex(d.id)} className="p-1 text-text-secondary hover:text-text"><RefreshCw size={14} strokeWidth={1.75}/></button>
                        <button disabled={busy} aria-label={`删除 ${d.filename}`} onClick={()=>remove(d.id)} className="p-1 text-danger"><Trash2 size={14} strokeWidth={1.75}/></button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              ) : (
              <EmptyState
                icon={FileText}
                title="该库暂无文档"
                description="上传 PDF、Word 或 Markdown 文件，解析后即可被检索。"
                actionLabel="上传文档"
                onAction={() => fileRef.current?.click()}
                size="sm"
              />
              )}
            </div>
            <div className="bg-surface border border-separator rounded-xl p-5">
              <h2 className="font-semibold tracking-tight mb-3">检索测试台</h2>
              <div className="flex gap-2">
                <Input value={query} onChange={e=>setQuery(e.target.value)} placeholder="用自然语言提问，例如 What's the MOQ for product X?" className="flex-1"/>
                <Button disabled={busy} onClick={search}>{busy ? "处理中..." : "检索"}</Button>
              </div>
              {embedder && <p className="text-xs text-text-secondary mt-2">嵌入：{embedder.available ? embedder.model : "未配置，使用词法检索"}</p>}
              <div className="mt-3 space-y-2">
                {hits.map((h,i)=>(
                  <div key={i} className="p-3 bg-bg/40 rounded-md border border-separator">
                    <div className="text-xs text-text-secondary mb-1">{h.doc_name} · 相关度 <span className="tabular-nums">{Number(h.score).toFixed(2)}</span></div>
                    <div className="text-sm whitespace-pre-wrap">{h.content}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
        )}
        <Modal
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          title="新建知识库"
          footer={<>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>取消</Button>
            <Button disabled={busy} onClick={createKb}>{busy ? "创建中..." : "创建"}</Button>
          </>}
        >
          <div className="flex gap-2">
            <Input value={newName} onChange={e=>setNewName(e.target.value)} placeholder="知识库名称" className="flex-1"/>
            <Button onClick={createKb}>创建</Button>
          </div>
        </Modal>
      </div>
    </div>
  );
}
