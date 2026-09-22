"use client";
import React, { useEffect, useState } from "react";
import { PenTool, Wand2, Copy, Share2, RefreshCw, Check } from "lucide-react";
import api from "../../../lib/api";
import { useToast } from "../../../contexts/ToastContext";
import { useRouter } from "next/navigation";

const TYPES = [
  { id: "product_article", label: "产品软文", hint: "500–700 词英文产品文" },
  { id: "linkedin_post", label: "LinkedIn 帖", hint: "180–280 词专业帖" },
  { id: "seo_blog", label: "SEO 博客", hint: "800+ 词可发布长文" },
  { id: "outreach_email", label: "开发信", hint: "短开发信 + 主题行" },
];

export default function TextGenPage() {
  const { showToast } = useToast();
  const router = useRouter();
  const [contentType, setContentType] = useState("seo_blog");
  const [productName, setProductName] = useState("Hydraulic Pump HP-200");
  const [sellingPoints, setSellingPoints] = useState("MOQ 50 units\nLead time 25 days\nFOB Ningbo\nISO 9001 / CE\n18-month warranty");
  const [audience, setAudience] = useState("overseas B2B importers and OEM buyers");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [copied, setCopied] = useState(false);

  const loadHistory = async () => {
    try {
      const res = await api.get("/api/v1/marketing/text?limit=12");
      setHistory(res.data.items || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const generate = async () => {
    if (!productName.trim()) return showToast("请填写产品名", "error");
    setLoading(true);
    try {
      const res = await api.post("/api/v1/marketing/text/generate", {
        content_type: contentType,
        product_name: productName,
        selling_points: sellingPoints,
        audience,
        language: "en",
      });
      setResult(res.data);
      showToast(res.data.mock ? "已生成（模型未配置，使用可发布模板）" : "英文内容已生成", "success");
      loadHistory();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "生成失败", "error");
    } finally {
      setLoading(false);
    }
  };

  const copyBody = async () => {
    if (!result?.body) return;
    await navigator.clipboard.writeText(
      (result.subject ? `Subject: ${result.subject}\n\n` : "") + `# ${result.title}\n\n${result.body}`
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const sendTo = (platform: string) => {
    if (!result) return;
    sessionStorage.setItem(
      "af_publish_draft",
      JSON.stringify({
        platform,
        title: result.title,
        content: result.body,
        content_id: result.id,
      })
    );
    router.push("/marketing/distribution");
  };

  return (
    <div className="h-full w-full p-6 text-text flex flex-col gap-4 overflow-hidden">
      <div className="flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white">文生文 · 外贸获客</h1>
          <p className="text-sm text-text-secondary">英文产品软文 / LinkedIn / SEO 博客 / 开发信，接入企业大脑默认模型。</p>
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="px-4 py-2 bg-warning hover:bg-warning disabled:opacity-50 text-white rounded-full text-sm font-medium flex items-center gap-2"
        >
          {loading ? <RefreshCw size={16} className="animate-spin" /> : <Wand2 size={16} />}
          {loading ? "生成中..." : "开始创作"}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-4 flex-1 min-h-0">
        <div className="glass-panel p-4 flex flex-col gap-4 overflow-y-auto">
          <div className="grid grid-cols-2 gap-2">
            {TYPES.map((t) => (
              <button
                key={t.id}
                onClick={() => setContentType(t.id)}
                className={`text-left p-3 rounded-lg border text-xs ${
                  contentType === t.id
                    ? "border-warning bg-warning/10 text-white"
                    : "border-separator text-text-secondary hover:bg-text/5"
                }`}
              >
                <div className="font-bold mb-1">{t.label}</div>
                <div className="text-[10px] opacity-70">{t.hint}</div>
              </button>
            ))}
          </div>
          <label className="text-xs text-text-secondary">
            产品名
            <input
              className="mt-1 w-full bg-bg/30 border border-separator rounded p-2 text-sm text-white"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
            />
          </label>
          <label className="text-xs text-text-secondary">
            目标受众
            <input
              className="mt-1 w-full bg-bg/30 border border-separator rounded p-2 text-sm text-white"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
            />
          </label>
          <label className="text-xs text-text-secondary flex-1">
            卖点 / 规格
            <textarea
              className="mt-1 w-full h-32 bg-bg/30 border border-separator rounded p-2 text-sm text-white resize-none"
              value={sellingPoints}
              onChange={(e) => setSellingPoints(e.target.value)}
            />
          </label>
          <div>
            <div className="text-xs text-text-secondary mb-2">最近生成</div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {history.map((h) => (
                <button
                  key={h.id}
                  onClick={() => setResult(h)}
                  className="w-full text-left text-xs p-2 rounded bg-text/5 hover:bg-text/10 truncate"
                >
                  <span className="text-text-secondary mr-2">{h.content_type}</span>
                  {h.title}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="glass-panel p-5 flex flex-col min-h-0">
          {!result ? (
            <div className="flex-1 flex items-center justify-center text-text-secondary">
              <div className="text-center">
                <PenTool size={48} className="mx-auto mb-4 opacity-40" />
                <p>填写产品与卖点，生成可直接发布的英文内容</p>
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-start justify-between gap-3 mb-3 shrink-0">
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-warning mb-1">
                    {result.content_type} · {result.word_count || 0} words
                    {result.mock ? " · template fallback" : ""}
                  </div>
                  <h2 className="text-xl font-bold text-white">{result.title}</h2>
                  {result.subject && (
                    <p className="text-sm text-text-secondary mt-1">Subject: {result.subject}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button onClick={copyBody} className="px-3 py-1.5 text-xs rounded bg-text/10 hover:bg-text/15 flex items-center gap-1">
                    {copied ? <Check size={12} /> : <Copy size={12} />} 复制
                  </button>
                  <button onClick={() => sendTo("linkedin")} className="px-3 py-1.5 text-xs rounded bg-accent hover:bg-accent flex items-center gap-1">
                    <Share2 size={12} /> LinkedIn
                  </button>
                  <button onClick={() => sendTo("wordpress")} className="px-3 py-1.5 text-xs rounded bg-accent hover:bg-accent-hover flex items-center gap-1">
                    WordPress
                  </button>
                  <button onClick={() => sendTo("x")} className="px-3 py-1.5 text-xs rounded bg-surface-2 hover:bg-text/10 flex items-center gap-1">
                    X
                  </button>
                </div>
              </div>
              <pre className="flex-1 overflow-y-auto whitespace-pre-wrap text-sm text-text leading-relaxed font-sans bg-bg/20 rounded-lg p-4 border border-separator">
                {result.body}
              </pre>
              {result.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-3 shrink-0">
                  {result.tags.map((t: string, i: number) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-warning/15 text-warning">
                      #{t}
                    </span>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
