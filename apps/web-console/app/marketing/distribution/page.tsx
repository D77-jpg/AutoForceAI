"use client";
import React, { useEffect, useState } from "react";
import { Share2, Globe, Linkedin, Send } from "lucide-react";
import api from "../../../lib/api";
import { useToast } from "../../../contexts/ToastContext";
import { useRouter } from "next/navigation";

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
    <div className="h-full w-full p-6 text-slate-100 flex flex-col gap-4 overflow-hidden">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">海外投放</h1>
          <p className="text-sm text-slate-400">LinkedIn / WordPress / X。任务进入 RPA 队列，结果在营销矩阵可追踪。</p>
        </div>
        <button
          onClick={publish}
          disabled={submitting}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-sm flex items-center gap-2"
        >
          <Send size={16} /> {submitting ? "提交中..." : "创建发布任务"}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4 flex-1 min-h-0">
        <div className="space-y-3 overflow-y-auto">
          {CHANNELS.map((c) => {
            const Icon = c.icon;
            return (
              <button
                key={c.id}
                onClick={() => setPlatform(c.id)}
                className={`w-full text-left p-4 rounded-xl border ${
                  platform === c.id ? "border-blue-500 bg-blue-500/10" : "border-white/10 bg-white/5"
                }`}
              >
                <div className="flex items-center gap-2 font-bold text-sm">
                  <Icon size={16} /> {c.label}
                </div>
                <p className="text-[11px] text-slate-400 mt-1">{c.desc}</p>
              </button>
            );
          })}
          <div className="text-[11px] text-slate-500 p-3 rounded-lg bg-white/5">
            WordPress：{wp?.configured ? `已配置 ${wp.base_url}` : "未配置 WP_API_URL，将走 dry-run 预览链接"}
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">从内容库填入</div>
            {library.slice(0, 8).map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  setTitle(item.title || "");
                  setContent(item.body || "");
                  setContentId(item.id);
                }}
                className="block w-full text-left text-xs p-2 rounded hover:bg-white/10 truncate text-slate-300"
              >
                {item.title}
              </button>
            ))}
          </div>
        </div>
        <div className="glass-panel p-4 flex flex-col gap-3 min-h-0">
          <input
            className="w-full bg-black/30 border border-white/10 rounded p-2 text-sm"
            placeholder="标题"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <textarea
            className="flex-1 min-h-0 bg-black/30 border border-white/10 rounded p-3 text-sm font-mono resize-none"
            placeholder="英文正文"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>
      </div>
    </div>
  );
}
