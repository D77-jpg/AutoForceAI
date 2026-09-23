"use client";
import React, { useEffect, useState } from "react";
import { Database } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/ui/empty-state";

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
    <div className="min-h-screen bg-bg text-text p-8">
      <PageHeader title="知识库统计" description="各知识库的文档与分块规模概览。" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {[["知识库", kbs.length],["文档", docs],["分块数", chunks]].map(([k,v])=>(
          <div key={k} className="p-5 rounded-xl border border-separator bg-text/[0.02]">
            <div className="text-xs text-text-secondary">{k}</div>
            <div className="text-3xl font-bold mt-2 tabular-nums">{v}</div>
          </div>
        ))}
      </div>
      {kbs.length ? (
      <div className="space-y-2">
        {kbs.map(kb=>(
          <div key={kb.id} className="p-3 rounded-md border border-separator flex justify-between">
            <span>{kb.name}{kb.is_public ? " · 公开" : ""}</span>
            <span className="text-text-secondary text-sm tabular-nums">{kb.doc_count} 文档 · {kb.chunk_count} 分块</span>
          </div>
        ))}
      </div>
      ) : (
      <EmptyState
        icon={Database}
        title="暂无知识库"
        description="请先在「知识文档」创建知识库并上传资料，再回到这里查看统计。"
        size="sm"
      />
      )}
    </div>
  );
}
