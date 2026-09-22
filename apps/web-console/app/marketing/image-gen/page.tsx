"use client";
import React, { useEffect, useState } from "react";
import { Image as ImageIcon, Wand2, RefreshCw } from "lucide-react";
import api from "../../../lib/api";
import { useToast } from "../../../contexts/ToastContext";

const PRESETS = [
  { id: "product_scene", label: "产品场景图" },
  { id: "banner", label: "独立站 Banner" },
  { id: "social", label: "社媒配图" },
];

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
      });
      setLatest(res.data);
      showToast(res.data.mock ? "已保存提示词（未配置文生图 Key）" : "图片已生成", "success");
      load();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "生成失败", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full w-full p-6 text-slate-100 flex flex-col gap-4 overflow-hidden">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">文生图 · 获客视觉</h1>
          <p className="text-sm text-slate-400">产品场景图 / Banner / 社媒配图。接入 DashScope Wanx，无 Key 时保存提示词。</p>
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="px-4 py-2 bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white rounded-full text-sm font-medium flex items-center gap-2"
        >
          {loading ? <RefreshCw size={16} className="animate-spin" /> : <Wand2 size={16} />}
          生成图片
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4 flex-1 min-h-0">
        <div className="glass-panel p-4 flex flex-col gap-3">
          <div className="flex gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                onClick={() => setPreset(p.id)}
                className={`flex-1 text-xs py-2 rounded border ${
                  preset === p.id ? "border-pink-500 bg-pink-500/15 text-white" : "border-white/10 text-slate-400"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <input
            className="w-full bg-black/30 border border-white/10 rounded p-2 text-sm"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            placeholder="产品名"
          />
          <textarea
            className="w-full flex-1 min-h-[120px] bg-black/30 border border-white/10 rounded p-2 text-sm resize-none"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="可选：自定义英文提示词。留空则按预设自动生成。"
          />
          {latest?.prompt && (
            <p className="text-[11px] text-slate-500 leading-relaxed">Prompt: {latest.prompt}</p>
          )}
        </div>

        <div className="overflow-y-auto">
          {items.length === 0 && !latest ? (
            <div className="h-full flex items-center justify-center border border-dashed border-white/10 rounded-xl text-slate-500">
              <div className="text-center">
                <ImageIcon size={48} className="mx-auto mb-4 opacity-40" />
                <p>还没有图片，点击生成</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {(latest ? [latest, ...items.filter((i) => i.id !== latest.id)] : items).map((img, idx) => (
                <div key={img.id || idx} className="glass-panel overflow-hidden">
                  {img.url || img.image_url ? (
                    <img src={img.url || img.image_url} alt={img.title} className="w-full h-40 object-cover" />
                  ) : (
                    <div className="h-40 flex items-center justify-center bg-white/5 text-xs text-slate-500 p-3 text-center">
                      {img.mock ? "待配置 DASHSCOPE_API_KEY" : "无预览"}
                    </div>
                  )}
                  <div className="p-2 text-[11px] text-slate-400 truncate">{img.title || img.preset}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
