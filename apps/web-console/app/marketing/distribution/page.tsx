"use client";
import React, { useEffect, useState } from "react";
import { Share2, Globe, Linkedin, Send, FileText } from "lucide-react";
import api from "../../../lib/api";
import { useToast } from "../../../contexts/ToastContext";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";

const CHANNELS = [
  { id: "linkedin", label: "LinkedIn", desc: "RPA 填草稿，建议人工点发布", icon: Linkedin },
  { id: "wordpress", label: "WordPress", desc: "REST API 直发独立站（可降级草稿）", icon: Globe },
  { id: "x", label: "X / Twitter", desc: "打开作曲器填文，人工点 Post", icon: Share2 },
];

export default function DistributionPage() {
  const { showToast } = useToast();
  const router = useRouter();
  const [platform, setPlatform] = useState("linkedin");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [contentId, setContentId] = useState<number | null>(null);
  const [library, setLibrary] = useState<any[]>([]);
  const [wp, setWp] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("af_publish_draft");
    if (raw) {
      try {
        const d = JSON.parse(raw);
        if (d.platform) setPlatform(d.platform);
        if (d.title) setTitle(d.title);
        if (d.content) setContent(d.content);
        if (d.content_id) setContentId(d.content_id);
      } catch {}
      sessionStorage.removeItem("af_publish_draft");
    }
    api.get("/api/v1/marketing/text?limit=20").then((r) => setLibrary(r.data.items || [])).catch(() => {});
    api.get("/api/v1/marketing/wordpress/status").then((r) => setWp(r.data)).catch(() => {});
  }, []);

  const publish = async () => {
    if (!title.trim() || !content.trim()) return showToast("标题和正文不能为空", "error");
    setSubmitting(true);
    try {
      const res = await api.post("/api/v1/marketing/publish", {
        platform,
        title,
        content,
        content_id: contentId,
      });
      showToast(res.data.msg || "已提交", "success");
      if (platform !== "wordpress") {
        const iframe = document.createElement("iframe");
        iframe.style.display = "none";
        iframe.src = "digitalemployee://wake";
        document.body.appendChild(iframe);
        setTimeout(() => document.body.removeChild(iframe), 2000);
      }
      setTimeout(() => router.push(`/distribution?expandJobId=${res.data.job_id || ""}`), 800);
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "发布失败", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="h-full w-full p-6 text-text flex flex-col gap-4 overflow-hidden">
      <PageHeader
        title="海外投放"
        description="LinkedIn / WordPress / X。任务进入 RPA 队列，结果在营销矩阵可追踪。"
        className="mb-0"
        actions={
          <Button onClick={publish} disabled={submitting}>
            <Send size={16} className="mr-2" /> {submitting ? "提交中..." : "创建发布任务"}
          </Button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4 flex-1 min-h-0">
        <div className="space-y-3 overflow-y-auto">
          {CHANNELS.map((c) => {
            const Icon = c.icon;
            return (
              <button
                key={c.id}
                onClick={() => setPlatform(c.id)}
                className={`w-full text-left p-4 rounded-xl border ${
                  platform === c.id ? "border-accent bg-accent/10" : "border-separator bg-text/5"
                }`}
              >
                <div className="flex items-center gap-2 font-bold text-sm">
                  <Icon size={16} /> {c.label}
                </div>
                <p className="text-[11px] text-text-secondary mt-1">{c.desc}</p>
              </button>
            );
          })}
          <div className="text-[11px] text-text-secondary p-3 rounded-lg bg-text/5">
            WordPress：{wp?.configured ? `已配置 ${wp.base_url}` : "未配置 WP_API_URL，将走 dry-run 预览链接"}
          </div>
          <div>
            <div className="text-xs text-text-secondary mb-1">从内容库填入</div>
            {library.length === 0 && (
              <EmptyState size="sm" icon={FileText} title="内容库为空" description="先在「文生文」生成英文内容" />
            )}
            {library.slice(0, 8).map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  setTitle(item.title || "");
                  setContent(item.body || "");
                  setContentId(item.id);
                }}
                className="block w-full text-left text-xs p-2 rounded hover:bg-text/10 truncate text-text"
              >
                {item.title}
              </button>
            ))}
          </div>
        </div>
        <div className="glass-panel p-4 flex flex-col gap-3 min-h-0">
          <Input
            placeholder="标题"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <textarea
            className="flex-1 min-h-0 bg-bg/30 border border-separator rounded p-3 text-sm font-mono resize-none"
            placeholder="英文正文"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>
      </div>
    </div>
  );
}
