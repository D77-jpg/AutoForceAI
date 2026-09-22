"use client";
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
    <div className="min-h-screen bg-bg text-text p-8">
      <div className="max-w-xl space-y-4">
        <h1 className="text-2xl font-bold">知识库参数</h1>
        {["top_k","score_threshold","chunk_size","chunk_overlap"].map(k=>(
          <label key={k} className="block text-sm">{k}
            <input className="mt-1 w-full bg-bg/40 border border-separator rounded px-3 py-2" value={cfg[k]??""} onChange={e=>setCfg({...cfg,[k]: Number(e.target.value)})}/>
          </label>
        ))}
        <button onClick={save} className="bg-accent px-4 py-2 rounded">保存</button>
        {msg && <span className="ml-3 text-success text-sm">{msg}</span>}
      </div>
    </div>
  );
}
