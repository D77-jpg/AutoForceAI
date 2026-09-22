"use client";
import React, { useEffect, useState } from "react";
import { Upload, Search, Database, RefreshCw, Trash2, FileText, Plus } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function token() { return typeof window !== "undefined" ? localStorage.getItem("token") : null; }
function auth() { return { Authorization: "Bearer " + (token() || "") }; }

export default function KnowledgePage() {
  const [kbs, setKbs] = useState([]);
  const [active, setActive] = useState(null);
  const [docs, setDocs] = useState([]);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState([]);
  const [newName, setNewName] = useState("");
  const [msg, setMsg] = useState("");
  const [embedder, setEmbedder] = useState(null);

  const loadKbs = async () => {
    const res = await fetch(API + "/api/v1/kb/bases", { headers: auth() });
    const data = await res.json();
    setKbs(data.items || []);
    if (!active && data.items?.length) setActive(data.items[0].id);
  };
  const loadDocs = async (id) => {
    if (!id) return;
    const res = await fetch(API + "/api/v1/kb/bases/" + id + "/docs", { headers: auth() });
    const data = await res.json();
    setDocs(data.items || []);
  };
  useEffect(() => { loadKbs(); }, []);
  useEffect(() => { loadDocs(active); }, [active]);

  const createKb = async () => {
    if (!newName.trim()) return;
    await fetch(API + "/api/v1/kb/bases", {
      method: "POST", headers: { ...auth(), "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName, is_public: true })
    });
    setNewName("");
    loadKbs();
  };
  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !active) return;
    const fd = new FormData();
    fd.append("file", file);
    setMsg("正在上传并解析...");
    const res = await fetch(API + "/api/v1/kb/bases/" + active + "/docs", { method: "POST", headers: auth(), body: fd });
    const data = await res.json();
    setMsg(res.ok ? "已提交解析，稍后刷新查看状态" : (data.detail || "上传失败"));
    setTimeout(() => loadDocs(active), 1500);
  };
  const search = async () => {
    const res = await fetch(API + "/api/v1/kb/search", {
      method: "POST", headers: { ...auth(), "Content-Type": "application/json" },
      body: JSON.stringify({ query, kb_ids: active ? [active] : null, score_threshold: 0.1 })
    });
    const data = await res.json();
    setHits(data.hits || []);
    setEmbedder(data.embedder);
  };
  const reindex = async (id) => {
    await fetch(API + "/api/v1/kb/docs/" + id + "/reindex", { method: "POST", headers: auth() });
    setTimeout(() => loadDocs(active), 1200);
  };
  const remove = async (id) => {
    await fetch(API + "/api/v1/kb/docs/" + id, { method: "DELETE", headers: auth() });
    loadDocs(active);
  };

  return (
    <div className="min-h-screen bg-black text-[#f5f5f7] p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-[28px] font-semibold tracking-tight text-white flex items-center gap-2"><Database className="text-[#0a84ff]"/> 知识文档</h1>
            <p className="text-[15px] text-[#86868b] mt-1.5">上传产品资料 / FAQ / 证书，供 AI 客服检索。无嵌入密钥时自动走词法检索。</p>
          </div>
          <div className="flex gap-2">
            <input value={newName} onChange={e=>setNewName(e.target.value)} placeholder="新知识库名称" className="bg-[#1c1c1e] border border-white/10 rounded-full px-4 py-2 text-sm placeholder:text-[#6e6e73] focus:outline-none focus:border-[#0a84ff]/40"/>
            <button onClick={createKb} className="bg-[#0071e3] hover:bg-[#0077ed] px-4 py-2 rounded-full text-sm font-medium flex items-center gap-1"><Plus size={14}/>创建</button>
          </div>
        </div>
        {msg && <div className="text-xs text-[#ffd60a]">{msg}</div>}
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-3 space-y-2">
            {kbs.map(kb => (
              <button key={kb.id} onClick={()=>setActive(kb.id)} className={"w-full text-left p-3.5 rounded-[16px] border transition-colors " + (active===kb.id ? "border-[#0a84ff]/40 bg-[#0a84ff]/10" : "border-white/8 bg-[#1c1c1e] hover:bg-[#2c2c2e]")}>
                <div className="font-medium text-white">{kb.name}</div>
                <div className="text-xs text-[#6e6e73] mt-1">{kb.doc_count} 文档 · {kb.chunk_count} 切片 {kb.is_public ? "· 公开" : ""}</div>
              </button>
            ))}
            {!kbs.length && <p className="text-sm text-slate-500">还没有知识库，先创建一个。</p>}
          </div>
          <div className="col-span-9 space-y-6">
            <div className="bg-[#1c1c1e] border border-white/8 rounded-[20px] p-5">
              <div className="flex justify-between items-center mb-4">
                <h2 className="font-semibold tracking-tight">文档列表</h2>
                <label className="cursor-pointer bg-[#2c2c2e] hover:bg-[#3a3a3c] px-3.5 py-2 rounded-full text-sm flex items-center gap-1.5 transition-colors">
                  <Upload size={14}/> 上传 PDF / Word / MD
                  <input type="file" className="hidden" accept=".pdf,.docx,.txt,.md" onChange={upload}/>
                </label>
              </div>
              <table className="w-full text-sm">
                <thead className="text-slate-500 text-xs"><tr><th className="text-left py-2">文件</th><th>状态</th><th>切片</th><th></th></tr></thead>
                <tbody>
                  {docs.map(d => (
                    <tr key={d.id} className="border-t border-white/5">
                      <td className="py-2 flex items-center gap-2"><FileText size={14}/> {d.filename}</td>
                      <td className="text-center">{d.status}{d.error_msg ? <span className="block text-[10px] text-amber-400">{d.error_msg}</span> : null}</td>
                      <td className="text-center">{d.chunk_count}</td>
                      <td className="text-right">
                        <button onClick={()=>reindex(d.id)} className="p-1 text-slate-400 hover:text-white"><RefreshCw size={14}/></button>
                        <button onClick={()=>remove(d.id)} className="p-1 text-red-400"><Trash2 size={14}/></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!docs.length && <p className="text-sm text-slate-500 py-6 text-center">该库暂无文档</p>}
            </div>
            <div className="bg-[#1c1c1e] border border-white/5 rounded-xl p-4">
              <h2 className="font-semibold mb-3 flex items-center gap-2"><Search size={16}/> 检索测试台</h2>
              <div className="flex gap-2">
                <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="用自然语言提问，例如 What's the MOQ for product X?" className="flex-1 bg-black/40 border border-white/10 rounded px-3 py-2 text-sm"/>
                <button onClick={search} className="bg-[#0071e3] px-4 py-2 rounded text-sm">检索</button>
              </div>
              {embedder && <p className="text-xs text-slate-500 mt-2">嵌入：{embedder.available ? embedder.model : "未配置，使用词法检索"}</p>}
              <div className="mt-3 space-y-2">
                {hits.map((h,i)=>(
                  <div key={i} className="p-3 bg-black/30 rounded border border-white/5">
                    <div className="text-xs text-slate-500 mb-1">{h.doc_name} · score {Number(h.score).toFixed(2)}</div>
                    <div className="text-sm whitespace-pre-wrap">{h.content}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
