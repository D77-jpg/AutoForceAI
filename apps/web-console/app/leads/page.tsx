"use client";
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
    <div className="min-h-screen bg-bg text-text p-8">
      <div className="flex justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">本地线索池</h1>
          <p className="text-sm text-text-secondary">AI 客服识别的询盘先落在这里。CRM 就绪后由投递器同步，无需返工。</p>
        </div>
        <button onClick={exportCsv} className="bg-text/10 px-3 py-2 rounded-full text-sm">导出 CSV</button>
      </div>
      <div className="flex gap-2 mb-4">
        <input value={q} onChange={e=>setQ(e.target.value)} placeholder="搜索邮箱/公司/产品" className="bg-bg/40 border border-separator rounded px-3 py-2 text-sm"/>
        <button onClick={load} className="bg-accent px-3 rounded text-sm">搜索</button>
        <select value={status} onChange={e=>setStatus(e.target.value)} className="bg-bg/40 border border-separator rounded px-2 text-sm">
          <option value="">全部状态</option>
          <option value="new">new</option>
          <option value="contacted">contacted</option>
          <option value="converted">converted</option>
          <option value="dropped">dropped</option>
        </select>
      </div>
      <table className="w-full text-sm">
        <thead className="text-text-secondary"><tr><th className="text-left py-2">公司/联系人</th><th>邮箱</th><th>产品</th><th>来源</th><th>状态</th><th></th></tr></thead>
        <tbody>
          {items.map(it=>(
            <tr key={it.id} className="border-t border-separator">
              <td className="py-2">{it.company || "-"} / {it.name || "-"}</td>
              <td>{it.email || "-"}</td>
              <td>{it.products || (it.intent_json && it.intent_json.intent) || "-"}</td>
              <td>{it.source}</td>
              <td>{it.status}</td>
              <td className="text-right space-x-1">
                {["contacted","converted","dropped"].map(s=>(
                  <button key={s} onClick={()=>setSt(it.id,s)} className="text-xs px-2 py-1 bg-text/5 rounded">{s}</button>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!items.length && <p className="text-text-secondary mt-8">暂无线索。嵌入独立站聊天插件或在检索测试后产生询盘即可入库。</p>}
    </div>
  );
}
