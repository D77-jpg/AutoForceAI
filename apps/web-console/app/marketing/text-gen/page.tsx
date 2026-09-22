"use client";
import React, { useEffect, useState } from "react";
import { PenTool, Wand2, Copy, Share2, RefreshCw, Check } from "lucide-react";
import api from "../../../lib/api";
import { useToast } from "../../../contexts/ToastContext";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";

const TYPES = [
  { id: "product_article", label: "产品软文", hint: "500–700 词英文产品文" },
  { id: "linkedin_post", label: "LinkedIn 帖", hint: "180–280 词专业帖" },
  { id: "seo_blog", label: "SEO 博客", hint: "800+ 词可发布长文" },
  { id: "outreach_email", label: "开发信", hint: "短开发信 + 主题行" },
];

const typeLabel = (id: string) => TYPES.find((t) => t.id === id)?.label || id;

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
      <PageHeader
        title="文生文 · 外贸获客"
        description="英文产品软文 / LinkedIn / SEO 博客 / 开发信，接入企业大脑默认模型。"
        className="mb-0 shrink-0"
        actions={
          <Button onClick={generate} disabled={loading}>
            {loading ? <RefreshCw size={16} strokeWidth={1.75} className="animate-spin mr-2" /> : <Wand2 size={16} strokeWidth={1.75} className="mr-2" />}
            {loading ? "生成中..." : "开始创作"}
          </Button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-4 flex-1 min-h-0">
        <div className="glass-panel p-4 flex flex-col gap-4 overflow-y-auto">
          <div className="grid grid-cols-2 gap-2">
            {TYPES.map((t) => (
              <button
                key={t.id}
                onClick={() => setContentType(t.id)}
                className={`text-left p-3 rounded-lg border text-xs transition-colors ${
                  contentType === t.id
                    ? "border-accent/40 bg-accent/10 text-accent"
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
            <Input
              className="mt-1"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
            />
          </label>
          <label className="text-xs text-text-secondary">
            目标受众
            <Input
              className="mt-1"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
            />
          </label>
          <label className="text-xs text-text-secondary flex-1">
            卖点 / 规格
            <textarea
              className="mt-1 w-full h-32 bg-surface-2 border border-transparent rounded-md p-2 text-sm text-text resize-none focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-accent/30"
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
                  className="w-full text-left text-xs p-2 rounded-md bg-text/5 hover:bg-text/10 truncate"
                >
                  <span className="text-text-secondary mr-2">{typeLabel(h.content_type)}</span>
                  {h.title}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="glass-panel p-5 flex flex-col min-h-0">
          {!result ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState
                size="lg"
                icon={PenTool}
                title="尚未生成内容"
                description="填写产品与卖点，生成可直接发布的英文内容"
                actionLabel="开始创作"
                onAction={generate}
              />
            </div>
          ) : (
            <>
              <div className="flex items-start justify-between gap-3 mb-3 shrink-0">
                <div>
                  <div className="text-[10px] text-text-secondary mb-1">
                    {typeLabel(result.content_type)} · <span className="tabular-nums">{result.word_count || 0}</span> 词
                    {result.mock ? " · 模板回退" : ""}
                  </div>
                  <h2 className="text-xl font-bold text-text">{result.title}</h2>
                  {result.subject && (
                    <p className="text-sm text-text-secondary mt-1">主题：{result.subject}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={copyBody}>
                    {copied ? <Check size={12} strokeWidth={1.75} className="mr-1" /> : <Copy size={12} strokeWidth={1.75} className="mr-1" />} 复制
                  </Button>
                  <Button size="sm" onClick={() => sendTo("linkedin")}>
                    <Share2 size={12} strokeWidth={1.75} className="mr-1" /> LinkedIn
                  </Button>
                  <Button size="sm" onClick={() => sendTo("wordpress")}>
                    WordPress
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => sendTo("x")}>
                    X
                  </Button>
                </div>
              </div>
              <pre className="flex-1 overflow-y-auto whitespace-pre-wrap text-sm text-text leading-relaxed font-sans bg-bg/20 rounded-lg p-4 border border-separator">
                {result.body}
              </pre>
              {result.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-3 shrink-0">
                  {result.tags.map((t: string, i: number) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded-pill bg-surface-2 text-text-secondary">
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
