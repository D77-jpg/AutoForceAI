"use client";
import React, { useEffect, useState } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function auth(){ return { Authorization: "Bearer " + (localStorage.getItem("token")||"") }; }
export default function KnowledgeStats() {
  const [kbs, setKbs] = useState([]);
  useEffect(()=>{
    fetch(API+"/api/v1/kb/bases",{headers:auth()}).then(r=>r.json()).then(d=>setKbs(d.items||[]));
  },[]);
  const docs = kbs.reduce((n,k)=>n+(k.doc_count||0),0);
  const chunks = kbs.reduce((n,k)=>n+(k.chunk_count||0),0);
  return (
    <div className="min-h-screen bg-black text-slate-200 p-8">
      <h1 className="text-2xl font-bold mb-6">知识库统计</h1>
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[["知识库", kbs.length],["文档", docs],["切片", chunks]].map(([k,v])=>(
          <div key={k} className="p-5 rounded-xl border border-white/5 bg-white/[0.02]">
            <div className="text-xs text-slate-500">{k}</div>
            <div className="text-3xl font-bold mt-2">{v}</div>
          </div>
        ))}
      </div>
      <div className="space-y-2">
        {kbs.map(kb=>(
          <div key={kb.id} className="p-3 rounded border border-white/5 flex justify-between">
            <span>{kb.name}{kb.is_public ? " · 公开" : ""}</span>
            <span className="text-slate-400 text-sm">{kb.doc_count} 文档 · {kb.chunk_count} 切片</span>
          </div>
        ))}
        {!kbs.length && <p className="text-slate-500">暂无知识库。请先在「知识文档」创建并上传资料。</p>}
      </div>
    </div>
  );
}
