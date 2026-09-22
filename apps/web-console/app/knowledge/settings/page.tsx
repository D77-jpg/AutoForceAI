"use client";
import React, { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
function auth(){ return { Authorization: "Bearer " + (localStorage.getItem("token")||""), "Content-Type":"application/json" }; }

const FIELD_LABELS: Record<string, string> = {
  top_k: "召回条数",
  score_threshold: "相似度阈值",
  chunk_size: "分块大小",
  chunk_overlap: "分块重叠",
};

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
      <div className="max-w-xl">
        <PageHeader title="知识库参数" description="调整检索召回与文档分块的默认参数，保存后即时生效。" />
        <div className="space-y-4">
          {["top_k","score_threshold","chunk_size","chunk_overlap"].map(k=>(
            <label key={k} className="block text-sm text-text-secondary">{FIELD_LABELS[k] ?? k}
              <Input className="mt-1.5 tabular-nums" value={cfg[k]??""} onChange={e=>setCfg({...cfg,[k]: Number(e.target.value)})}/>
            </label>
          ))}
          <div className="flex items-center gap-2">
            <Button onClick={save}>保存</Button>
            {msg && <span className="text-success text-sm">{msg}</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
