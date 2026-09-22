const fs = require('fs');
const path = require('path');

function write(rel, content) {
  const p = path.join('D:/D77/project/AutoForceAI', rel);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, content.replace(/\n/g, '\n'), 'utf8');
  console.log('wrote', rel);
}

const knowledgePage = `"use client";
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
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Database className="text-indigo-400"/> 知识文档</h1>
            <p className="text-sm text-slate-400 mt-1">上传产品资料 / FAQ / 证书，供 AI 客服检索。无嵌入密钥时自动走词法检索。</p>
          </div>
          <div className="flex gap-2">
            <input value={newName} onChange={e=>setNewName(e.target.value)} placeholder="新知识库名称" className="bg-black/40 border border-white/10 rounded px-3 py-2 text-sm"/>
            <button onClick={createKb} className="bg-indigo-600 hover:bg-indigo-500 px-3 py-2 rounded text-sm flex items-center gap-1"><Plus size={14}/>创建</button>
          </div>
        </div>
        {msg && <div className="text-xs text-amber-400">{msg}</div>}
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-3 space-y-2">
            {kbs.map(kb => (
              <button key={kb.id} onClick={()=>setActive(kb.id)} className={"w-full text-left p-3 rounded-lg border " + (active===kb.id ? "border-indigo-500 bg-indigo-500/10" : "border-white/5 bg-white/[0.02]")}>
                <div className="font-medium text-white">{kb.name}</div>
                <div className="text-xs text-slate-500 mt-1">{kb.doc_count} 文档 · {kb.chunk_count} 切片 {kb.is_public ? "· 公开" : ""}</div>
              </button>
            ))}
            {!kbs.length && <p className="text-sm text-slate-500">还没有知识库，先创建一个。</p>}
          </div>
          <div className="col-span-9 space-y-6">
            <div className="bg-[#141720] border border-white/5 rounded-xl p-4">
              <div className="flex justify-between items-center mb-3">
                <h2 className="font-semibold">文档列表</h2>
                <label className="cursor-pointer bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded text-sm flex items-center gap-1">
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
            <div className="bg-[#141720] border border-white/5 rounded-xl p-4">
              <h2 className="font-semibold mb-3 flex items-center gap-2"><Search size={16}/> 检索测试台</h2>
              <div className="flex gap-2">
                <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="用自然语言提问，例如 What's the MOQ for product X?" className="flex-1 bg-black/40 border border-white/10 rounded px-3 py-2 text-sm"/>
                <button onClick={search} className="bg-indigo-600 px-4 py-2 rounded text-sm">检索</button>
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
`;

const knowledgeSettings = `"use client";
import React, { useEffect, useState } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function auth(){ return { Authorization: "Bearer " + (localStorage.getItem("token")||""), "Content-Type":"application/json" }; }
export default function KnowledgeSettings() {
  const [cfg, setCfg] = useState({ top_k:5, score_threshold:0.35, chunk_size:1000, chunk_overlap:200, sensitive_words:"" });
  const [msg, setMsg] = useState("");
  useEffect(()=>{ fetch(API+"/api/v1/kb/config",{headers:auth()}).then(r=>r.json()).then(setCfg); },[]);
  const save = async () => {
    await fetch(API+"/api/v1/kb/config",{method:"PUT", headers:auth(), body: JSON.stringify(cfg)});
    setMsg("已保存");
  };
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8">
      <div className="max-w-xl space-y-4">
        <h1 className="text-2xl font-bold">知识库参数</h1>
        {["top_k","score_threshold","chunk_size","chunk_overlap"].map(k=>(
          <label key={k} className="block text-sm">{k}
            <input className="mt-1 w-full bg-black/40 border border-white/10 rounded px-3 py-2" value={cfg[k]??""} onChange={e=>setCfg({...cfg,[k]: Number(e.target.value)})}/>
          </label>
        ))}
        <button onClick={save} className="bg-indigo-600 px-4 py-2 rounded">保存</button>
        {msg && <span className="ml-3 text-green-400 text-sm">{msg}</span>}
      </div>
    </div>
  );
}
`;

const knowledgeBrain = `"use client";
export default function KnowledgeBrain() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8">
      <h1 className="text-2xl font-bold mb-2">企业知识大脑</h1>
      <p className="text-slate-400">对话入口已在右侧 ChatSidebar。请先在「知识文档」上传资料，再回到工作台提问。</p>
    </div>
  );
}
`;

const knowledgeStats = `"use client";
export default function KnowledgeStats() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8">
      <h1 className="text-2xl font-bold">知识库统计</h1>
      <p className="text-slate-400 mt-2">文档数量、切片数量请在知识文档页查看。更细的报表会在阶段 5 接入监控。</p>
    </div>
  );
}
`;

const leadsPage = `"use client";
import React, { useEffect, useState } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function auth(){ return { Authorization: "Bearer " + (localStorage.getItem("token")||"") }; }
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
  const exportCsv = () => {
    fetch(API+"/api/v1/leads/export.csv", { headers: auth() }).then(r=>r.blob()).then(b=>{
      const a=document.createElement("a"); a.href=URL.createObjectURL(b); a.download="leads.csv"; a.click();
    });
  };
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8">
      <div className="flex justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">本地线索池</h1>
          <p className="text-sm text-slate-400">AI 客服识别的询盘先落在这里。CRM 就绪后由投递器同步，无需返工。</p>
        </div>
        <button onClick={exportCsv} className="bg-white/10 px-3 py-2 rounded text-sm">导出 CSV</button>
      </div>
      <div className="flex gap-2 mb-4">
        <input value={q} onChange={e=>setQ(e.target.value)} placeholder="搜索邮箱/公司/产品" className="bg-black/40 border border-white/10 rounded px-3 py-2 text-sm"/>
        <button onClick={load} className="bg-indigo-600 px-3 rounded text-sm">搜索</button>
        <select value={status} onChange={e=>setStatus(e.target.value)} className="bg-black/40 border border-white/10 rounded px-2 text-sm">
          <option value="">全部状态</option>
          <option value="new">new</option>
          <option value="contacted">contacted</option>
          <option value="converted">converted</option>
          <option value="dropped">dropped</option>
        </select>
      </div>
      <table className="w-full text-sm">
        <thead className="text-slate-500"><tr><th className="text-left py-2">公司/联系人</th><th>邮箱</th><th>产品</th><th>来源</th><th>状态</th><th></th></tr></thead>
        <tbody>
          {items.map(it=>(
            <tr key={it.id} className="border-t border-white/5">
              <td className="py-2">{it.company || "-"} / {it.name || "-"}</td>
              <td>{it.email || "-"}</td>
              <td>{it.products || (it.intent_json && it.intent_json.intent) || "-"}</td>
              <td>{it.source}</td>
              <td>{it.status}</td>
              <td className="text-right space-x-1">
                {["contacted","converted","dropped"].map(s=>(
                  <button key={s} onClick={()=>setSt(it.id,s)} className="text-xs px-2 py-1 bg-white/5 rounded">{s}</button>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!items.length && <p className="text-slate-500 mt-8">暂无线索。嵌入独立站聊天插件或在检索测试后产生询盘即可入库。</p>}
    </div>
  );
}
`;

write("apps/web-console/app/knowledge/page.tsx", knowledgePage);
write("apps/web-console/app/knowledge/settings/page.tsx", knowledgeSettings);
write("apps/web-console/app/knowledge/brain/page.tsx", knowledgeBrain);
write("apps/web-console/app/knowledge/stats/page.tsx", knowledgeStats);
write("apps/web-console/app/knowledge/solution/page.tsx", `"use client";
export default function Page(){ return <div className="min-h-screen bg-slate-950 text-slate-200 p-8"><h1 className="text-2xl font-bold">方案生成</h1><p className="text-slate-400 mt-2">请使用工作台里的方案生成（solution_router），本页为入口占位。</p></div>; }`);
write("apps/web-console/app/leads/page.tsx", leadsPage);

write("apps/web-console/app/service/sessions/page.tsx", `"use client";
import React, { useEffect, useState } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function auth(){ return { Authorization: "Bearer " + (localStorage.getItem("token")||"") }; }
export default function SessionsPage() {
  const [items, setItems] = useState([]);
  const [cur, setCur] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const load = async () => {
    const res = await fetch(API+"/api/v1/service/sessions", { headers: auth() });
    const data = await res.json();
    setItems(data.items || []);
  };
  useEffect(()=>{ load(); const t=setInterval(load, 5000); return ()=>clearInterval(t); },[]);
  const open = async (uuid) => {
    setCur(uuid);
    const res = await fetch(API+"/api/v1/service/sessions/"+uuid, { headers: auth() });
    const data = await res.json();
    setMsgs(data.messages || []);
  };
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8 grid grid-cols-12 gap-6">
      <div className="col-span-5">
        <h1 className="text-2xl font-bold mb-4">实时会话监控</h1>
        {items.map(s=>(
          <button key={s.id} onClick={()=>open(s.session_uuid)} className="block w-full text-left p-3 mb-2 rounded border border-white/5 hover:border-indigo-500/40">
            <div className="text-sm">{s.visitor_email || s.visitor_name || s.visitor_id}</div>
            <div className="text-xs text-slate-500">{s.status} · {s.language || "-"} · {s.intent && s.intent.intent}</div>
          </button>
        ))}
        {!items.length && <p className="text-slate-500">暂无会话。用聊天插件测试页发起对话。</p>}
      </div>
      <div className="col-span-7 bg-[#141720] border border-white/5 rounded-xl p-4">
        <h2 className="font-semibold mb-3">会话详情 {cur||""}</h2>
        <div className="space-y-2 max-h-[70vh] overflow-auto">
          {msgs.map((m,i)=>(
            <div key={i} className={"p-2 rounded " + (m.role==="user"?"bg-indigo-500/10":"bg-white/5")}>
              <div className="text-[10px] text-slate-500">{m.role}</div>
              <div className="text-sm whitespace-pre-wrap">{m.content}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
`);

write("apps/web-console/app/service/history/page.tsx", `"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
export default function History(){ const r=useRouter(); useEffect(()=>{ r.replace("/service/sessions"); },[r]); return null; }
`);

write("apps/web-console/app/service/config/page.tsx", `"use client";
import React, { useEffect, useState } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function auth(){ return { Authorization: "Bearer " + (localStorage.getItem("token")||""), "Content-Type":"application/json" }; }
export default function BotConfig() {
  const [items, setItems] = useState([]);
  const [kbs, setKbs] = useState([]);
  const [form, setForm] = useState({ name:"Export Assistant", welcome_message:"Hello! How can I help you today?", system_prompt:"You are a professional B2B export sales assistant. Reply in the visitor language, prefer English.", kb_id:null });
  const load = async () => {
    const b = await fetch(API+"/api/v1/service/bots",{headers:auth()}).then(r=>r.json());
    setItems(b.items||[]);
    const k = await fetch(API+"/api/v1/kb/bases",{headers:auth()}).then(r=>r.json());
    setKbs(k.items||[]);
  };
  useEffect(()=>{ load(); },[]);
  const save = async () => {
    await fetch(API+"/api/v1/service/bots",{method:"POST", headers:auth(), body: JSON.stringify({...form, kb_id: form.kb_id? Number(form.kb_id): null})});
    load();
  };
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8">
      <h1 className="text-2xl font-bold mb-4">接待机器人</h1>
      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-3">
          <input className="w-full bg-black/40 border border-white/10 rounded px-3 py-2" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/>
          <textarea className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 h-24" value={form.welcome_message} onChange={e=>setForm({...form,welcome_message:e.target.value})}/>
          <textarea className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 h-40" value={form.system_prompt} onChange={e=>setForm({...form,system_prompt:e.target.value})}/>
          <select className="w-full bg-black/40 border border-white/10 rounded px-3 py-2" value={form.kb_id||""} onChange={e=>setForm({...form,kb_id:e.target.value})}>
            <option value="">不绑定知识库</option>
            {kbs.map(k=><option key={k.id} value={k.id}>{k.name}</option>)}
          </select>
          <button onClick={save} className="bg-indigo-600 px-4 py-2 rounded">创建 / 保存</button>
        </div>
        <div>
          {items.map(b=>(
            <div key={b.id} className="p-3 mb-2 border border-white/5 rounded">
              <div className="font-medium">{b.name}</div>
              <div className="text-xs text-slate-500">kb={b.kb_id || "-"} · {b.is_active ? "启用" : "停用"}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
`);

write("apps/web-console/app/service/rules/page.tsx", `"use client";
import React, { useEffect, useState } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function auth(){ return { Authorization: "Bearer " + (localStorage.getItem("token")||""), "Content-Type":"application/json" }; }
export default function Rules() {
  const [items, setItems] = useState([]);
  const [name, setName] = useState("SOP 规范性");
  const [description, setDescription] = useState("检查是否使用敬语、是否基于知识库回答、是否承诺无法兑现的交期");
  const load = async () => { const d = await fetch(API+"/api/v1/service/rules",{headers:auth()}).then(r=>r.json()); setItems(d.items||[]); };
  useEffect(()=>{ load(); },[]);
  const add = async () => { await fetch(API+"/api/v1/service/rules",{method:"POST", headers:auth(), body: JSON.stringify({name, description, weight:1})}); load(); };
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8">
      <h1 className="text-2xl font-bold mb-4">质检规则</h1>
      <div className="flex gap-2 mb-4">
        <input className="bg-black/40 border border-white/10 rounded px-3 py-2" value={name} onChange={e=>setName(e.target.value)}/>
        <button onClick={add} className="bg-indigo-600 px-3 rounded">添加</button>
      </div>
      <textarea className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 mb-4" value={description} onChange={e=>setDescription(e.target.value)}/>
      {items.map(r=>(<div key={r.id} className="p-3 border border-white/5 rounded mb-2"><div className="font-medium">{r.name}</div><div className="text-sm text-slate-400">{r.description}</div></div>))}
    </div>
  );
}
`);

write("apps/web-console/app/service/stats/page.tsx", `"use client";
import React, { useEffect, useState } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function auth(){ return { Authorization: "Bearer " + (localStorage.getItem("token")||"") }; }
export default function Stats() {
  const [s, setS] = useState(null);
  useEffect(()=>{ fetch(API+"/api/v1/service/stats",{headers:auth()}).then(r=>r.json()).then(setS); },[]);
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8">
      <h1 className="text-2xl font-bold mb-6">服务质量报表</h1>
      <div className="grid grid-cols-3 gap-4">
        {[["总会话", s && s.sessions],["进行中", s && s.active],["线索", s && s.leads]].map(([k,v])=>(
          <div key={k} className="p-5 rounded-xl border border-white/5 bg-white/[0.02]"><div className="text-xs text-slate-500">{k}</div><div className="text-3xl font-bold mt-2">{v ?? "-"}</div></div>
        ))}
      </div>
    </div>
  );
}
`);

write("apps/web-console/app/service/page.tsx", `"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
export default function ServiceHome(){ const r=useRouter(); useEffect(()=>{ r.replace("/service/sessions"); },[r]); return null; }
`);

write("apps/chat-widget/widget.js", `/* AutoForceAI chat widget. Embed:
<script src="http://localhost:8010/widget/autoforce-chat.js" data-api="http://localhost:8010"></script>
*/
(function(){
  var script = document.currentScript;
  var API = (script && script.getAttribute("data-api")) || "http://localhost:8010";
  var BOT = (script && script.getAttribute("data-bot-id")) || "";
  var KEY = "af_chat_sid";
  function el(tag, cls, html){ var n=document.createElement(tag); if(cls) n.className=cls; if(html) n.innerHTML=html; return n; }
  var btn = el("button");
  btn.textContent = "Chat";
  btn.style.cssText = "position:fixed;right:20px;bottom:20px;z-index:99999;background:#4f46e5;color:#fff;border:0;border-radius:999px;padding:12px 18px;cursor:pointer;font:14px/1 sans-serif;";
  var box = el("div");
  box.style.cssText = "display:none;position:fixed;right:20px;bottom:70px;width:340px;height:460px;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:12px;z-index:99999;flex-direction:column;overflow:hidden;font:13px/1.4 sans-serif;";
  box.innerHTML = '<div style="padding:10px 12px;background:#1e293b;font-weight:600">Sales Assistant</div><div id="af-msgs" style="flex:1;overflow:auto;padding:10px;height:350px"></div><form id="af-form" style="display:flex;border-top:1px solid #334155"><input id="af-input" style="flex:1;background:#0b1220;border:0;color:#fff;padding:10px" placeholder="Ask about MOQ / price..."/><button style="background:#4f46e5;border:0;color:#fff;padding:0 12px">Send</button></form>';
  document.body.appendChild(btn); document.body.appendChild(box);
  var msgs = box.querySelector("#af-msgs");
  function add(role, text){ var d=el("div"); d.style.margin="8px 0"; d.style.whiteSpace="pre-wrap"; d.textContent=(role==="user"?"You: ":"AI: ")+text; msgs.appendChild(d); msgs.scrollTop=msgs.scrollHeight; }
  var sid = localStorage.getItem(KEY);
  async function ensure(){
    if (sid) return sid;
    var res = await fetch(API+"/api/v1/service/widget/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({bot_id: BOT? Number(BOT): null})});
    var data = await res.json();
    sid = data.session_uuid; localStorage.setItem(KEY, sid);
    add("assistant", data.welcome || "Hello!");
    return sid;
  }
  btn.onclick = async function(){ box.style.display = box.style.display==="none" ? "flex" : "none"; if(box.style.display==="flex") await ensure(); };
  box.querySelector("#af-form").onsubmit = async function(e){
    e.preventDefault();
    var input = box.querySelector("#af-input");
    var text = input.value.trim(); if(!text) return;
    input.value=""; add("user", text);
    await ensure();
    var res = await fetch(API+"/api/v1/service/widget/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({session_uuid:sid,message:text})});
    var data = await res.json();
    add("assistant", data.reply || "");
  };
})();
`);

write("apps/chat-widget/demo.html", `<!doctype html>
<html><head><meta charset="utf-8"><title>Chat Widget Demo</title></head>
<body style="font-family:sans-serif;padding:40px">
<h1>Independent site demo</h1>
<p>Ask: What's the MOQ for product X?</p>
<script src="http://localhost:8010/widget/autoforce-chat.js" data-api="http://localhost:8010"></script>
</body></html>
`);

console.log("all pages written");
