"use client";
import React, { useEffect, useState } from "react";
import { Image as ImageIcon, Wand2, RefreshCw } from "lucide-react";
import api from "../../../lib/api";
import { useToast } from "../../../contexts/ToastContext";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";

const PRESETS = [
  { id: "product_scene", label: "产品场景图" },
  { id: "banner", label: "独立站 Banner" },
  { id: "social", label: "社媒配图" },
];

function SavedImage({ image }: { image: any }) {
  const [source, setSource] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    let objectUrl = "";
    const url = image.url || image.image_url;
    setSource("");
    setError("");
    if (!url) {
      setError("该历史记录没有图片文件，请重新生成");
      return;
    }
    if (!url.startsWith("/api/v1/marketing/images/")) {
      setSource(url);
      return;
    }
    api.get(url, { responseType: "blob" }).then((response) => {
      if (active) {
        objectUrl = URL.createObjectURL(response.data);
        setSource(objectUrl);
      }
    }).catch(() => { if (active) setError("图片读取失败，请刷新或重新生成"); });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [image.url, image.image_url]);
  return <>
    {source ? <img src={source} alt={image.title || "生成图片"} className="w-full h-40 object-cover" /> :
      <div className="h-40 flex items-center justify-center p-3 text-xs text-text-secondary text-center" role="status">{error || "正在读取图片..."}</div>}
    {source && <a href={source} download={`marketing-${image.id || "image"}.png`} className="block px-3 py-2 text-xs text-accent">下载图片</a>}
  </>;
}

export default function ImageGenPage() {
  const { showToast } = useToast();
  const [preset, setPreset] = useState("product_scene");
  const [productName, setProductName] = useState("Hydraulic Pump HP-200");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<any[]>([]);
  const [latest, setLatest] = useState<any>(null);

  const load = async () => {
    try {
      const res = await api.get("/api/v1/marketing/images?limit=24");
      setItems(res.data.items || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await api.post("/api/v1/marketing/images/generate", {
        product_name: productName,
        prompt: prompt || undefined,
        preset,
      }, { timeout: 240000 });
      setLatest(res.data);
      showToast("图片已生成并保存", "success");
      load();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "生成失败", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full w-full p-6 text-text flex flex-col gap-4 overflow-hidden">
      <PageHeader
        title="文生图 · 获客视觉"
        description="生成产品场景图、Banner 和社媒配图，保存后可在历史中查看和下载。"
        className="mb-0 shrink-0"
        actions={
          <Button onClick={generate} disabled={loading}>
            {loading ? <RefreshCw size={16} strokeWidth={1.75} className="animate-spin mr-2" /> : <Wand2 size={16} strokeWidth={1.75} className="mr-2" />}
            生成图片
          </Button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4 flex-1 min-h-0">
        <div className="glass-panel p-4 flex flex-col gap-3">
          <div className="flex gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                onClick={() => setPreset(p.id)}
                className={`flex-1 text-xs py-2 rounded-md border transition-colors ${
                  preset === p.id
                    ? "border-accent/40 bg-accent/10 text-accent"
                    : "border-separator text-text-secondary hover:bg-text/5"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <Input
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            placeholder="产品名"
          />
          <textarea
            className="w-full flex-1 min-h-[120px] bg-bg/30 border border-separator rounded-md p-2 text-sm resize-none"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="可选：自定义英文提示词。留空则按预设自动生成。"
          />
          {latest?.prompt && (
            <p className="text-[11px] text-text-secondary leading-relaxed">提示词：{latest.prompt}</p>
          )}
        </div>

        <div className="glass-panel p-4 overflow-y-auto">
          {items.length === 0 && !latest ? (
            <div className="h-full flex items-center justify-center">
              <EmptyState
                size="lg"
                icon={ImageIcon}
                title="还没有图片"
                description="选择预设并填写产品名，生成获客视觉素材"
                actionLabel="生成图片"
                onAction={generate}
              />
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {(latest ? [latest, ...items.filter((i) => i.id !== latest.id)] : items).map((img, idx) => (
                <div key={img.id || idx} className="rounded-lg border border-separator bg-surface-2 overflow-hidden">
                  <SavedImage image={img} />
                  <div className="p-2 text-[11px] text-text-secondary truncate">{img.title || img.preset}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
