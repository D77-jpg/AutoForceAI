"use client";

import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Save, Search, Server, FileText, Sparkles, Terminal, Loader2, RefreshCw } from 'lucide-react';
import { useToast } from "@/contexts/ToastContext";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

interface SkillParam { name: string; type: string; description: string; required: boolean; }
interface Skill { name: string; description: string; category: string; tags: string[]; parameters: SkillParam[]; }

export default function SkillSettingsPage() {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);

  // Live skills from the backend ToolRegistry
  const [skills, setSkills] = useState<Skill[]>([]);
  const [skillsLoading, setSkillsLoading] = useState(true);
  const [skillsError, setSkillsError] = useState<string | null>(null);

  const fetchSkills = async () => {
    setSkillsLoading(true);
    setSkillsError(null);
    try {
      const res = await fetch(API_URL + "/api/v1/platform/skills");
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      setSkills(data.skills || []);
    } catch (e) {
      setSkillsError(e.message || "无法连接后端服务");
    } finally {
      setSkillsLoading(false);
    }
  };

  useEffect(() => { fetchSkills(); }, []);

  // Base capability config — local until backend config API lands (Phase 5)
  const [config, setConfig] = useState({
    web_search_enabled: true,
    serp_api_key: "",
    rpa_enabled: true,
    rpa_worker_url: "http://localhost:8010",
    ppt_enabled: true,
    ppt_template_path: "/storage/ppt_templates/default.pptx"
  });

  const handleSave = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      showToast("配置已保存（本地暂存）", "success");
    }, 500);
  };

  return (
    <div className="p-8">
      {/* Header aligned with Service/Skills */}
      <div className="flex justify-between items-center mb-6">
           <h1 className="text-2xl font-bold flex items-center gap-2 text-white">
              <Sparkles className="text-violet-500" />
              技能工具箱 (Skills Capability Center)
          </h1>
          <Button onClick={handleSave} disabled={loading} className="bg-violet-600 hover:bg-violet-700 text-white gap-2 shadow-lg shadow-violet-500/20">
              <Save size={16} /> {loading ? "保存中..." : "保存全局配置"}
          </Button>
      </div>
      
      <p className="text-slate-400 mb-8 max-w-3xl">
          管理数字员工可调用的核心能力模块。既包括基础服务的连接配置，也包含业务层面的具体技能定义。
      </p>

      <Tabs defaultValue="library" className="w-full">
        <TabsList className="mb-6 bg-[#1c1c1e] border border-white/8">
           <TabsTrigger value="library" className="px-6 data-[state=active]:bg-violet-600">
             <Terminal className="w-4 h-4 mr-2" />
             业务技能 (Business Skills)
           </TabsTrigger>
           <TabsTrigger value="config" className="px-6 data-[state=active]:bg-violet-600">
             <Server className="w-4 h-4 mr-2" />
             基础技能 (Base Skills)
           </TabsTrigger>
        </TabsList>

        {/* Tab 1: 业务技能 (原 Registry) */}
        <TabsContent value="library" className="animate-in fade-in slide-in-from-left-4">
             {skillsLoading ? (
                 <div className="flex items-center justify-center h-60 text-slate-500 gap-2">
                     <Loader2 className="animate-spin" size={20} /> 正在从后端加载技能清单...
                 </div>
             ) : skillsError ? (
                 <div className="flex flex-col items-center justify-center h-60 text-slate-500 gap-3">
                     <p>加载失败：{skillsError}</p>
                     <Button variant="outline" onClick={fetchSkills} className="gap-2 border-white/10 text-slate-300 hover:bg-white/5">
                         <RefreshCw size={14} /> 重试
                     </Button>
                 </div>
             ) : (
             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {skills.map((skill) => (
                <div key={skill.name} className="glass-card p-6 relative group hover:bg-[#2c2c2e]/60 transition-all border-0">
                    <div className={"w-10 h-10 rounded-lg flex items-center justify-center mb-4 border " + (skill.category === "system" ? "bg-blue-500/10 text-blue-400 border-blue-500/20" : "bg-green-500/10 text-green-400 border-green-500/20")}>
                        <Terminal size={20} />
                    </div>
                    <div className="mb-1">
                        <h3 className="font-semibold text-lg text-white">{skill.name}</h3>
                    </div>
                    <code className="text-xs bg-[#2c2c2e] px-1 py-0.5 rounded text-slate-400 border border-white/10">{skill.name}</code>
                    <p className="text-sm text-slate-400 mt-3 line-clamp-2">{skill.description || "暂无描述"}</p>
                    {skill.parameters.length > 0 && (
                        <div className="mt-3 space-y-1">
                            {skill.parameters.map((p) => (
                                <div key={p.name} className="text-xs text-slate-500 font-mono">
                                    <span className="text-slate-300">{p.name}</span>
                                    <span className="text-slate-600">: {p.type}{p.required ? " *" : ""}</span>
                                </div>
                            ))}
                        </div>
                    )}
                    <div className="mt-4 pt-4 border-t border-white/8 flex gap-2">
                        {skill.tags.map((tag) => (
                            <span key={tag} className={"px-2 py-0.5 text-xs rounded border " + (tag === "System" ? "bg-slate-500/10 text-slate-400 border-slate-500/20" : tag === "Business" ? "bg-violet-500/10 text-violet-400 border-violet-500/20" : "bg-slate-700 text-slate-300 border-white/12")}>{tag}</span>
                        ))}
                    </div>
                </div>
                ))}
            </div>
            )}
        </TabsContent>

        {/* Tab 2: 基础设施配置 (原 Config 内容) */}
        <TabsContent value="config" className="animate-in fade-in slide-in-from-right-4">
             <div className="grid gap-6 max-w-5xl">
                {/* Web Search Config */}
                <div className="glass-card p-6 border-0">
                <div className="flex flex-row items-center gap-4 mb-6">
                    <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center text-blue-400 border border-blue-500/20">
                    <Search size={24} />
                    </div>
                    <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white">联网深度调研 (Deep Research)</h3>
                    <p className="text-sm text-slate-400">配置 Google/Bing 搜索接口，赋予员工实时联网获取信息的能力。</p>
                    </div>
                    <Switch checked={config.web_search_enabled} onCheckedChange={(v) => setConfig({...config, web_search_enabled: v})} />
                </div>
                
                {config.web_search_enabled && (
                    <div className="pl-16 grid gap-4 animate-in fade-in slide-in-from-top-2">
                    <div className="grid gap-2">
                        <Label htmlFor="api_key" className="text-slate-300">SerpApi Key / Bing API Key</Label>
                        <div className="flex gap-2">
                        <Input 
                            id="api_key" 
                            type="password" 
                            value={config.serp_api_key} 
                            className="bg-black/30 border-white/10 text-white"
                            onChange={(e) => setConfig({...config, serp_api_key: e.target.value})}
                        />
                        <Button variant="outline" className="border-white/10 text-slate-300 hover:bg-white/5 hover:text-white">验证连接</Button>
                        </div>
                        <p className="text-xs text-slate-500">用于 <code className="bg-[#2c2c2e] px-1 py-0.5 rounded text-blue-300">web_search</code> 技能调用外部搜索引擎。</p>
                    </div>
                    </div>
                )}
                </div>

                {/* RPA Config */}
                <div className="glass-card p-6 border-0">
                <div className="flex flex-row items-center gap-4 mb-6">
                    <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center text-purple-400 border border-purple-500/20">
                    <Server size={24} />
                    </div>
                    <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white">RPA 浏览器自动化 (Browser Automation)</h3>
                    <p className="text-sm text-slate-400">配置 RPA Worker 集群地址，用于执行网页操作、截图与模拟登录任务。</p>
                    </div>
                    <Switch checked={config.rpa_enabled} onCheckedChange={(v) => setConfig({...config, rpa_enabled: v})} />
                </div>
                
                {config.rpa_enabled && (
                    <div className="pl-16 grid gap-4 animate-in fade-in slide-in-from-top-2">
                    <div className="grid gap-2">
                        <Label htmlFor="rpa_url" className="text-slate-300">RPA Worker URL</Label>
                        <Input 
                        id="rpa_url" 
                        value={config.rpa_worker_url}
                        className="bg-black/30 border-white/10 text-white"
                        onChange={(e) => setConfig({...config, rpa_worker_url: e.target.value})} 
                        />
                        <p className="text-xs text-slate-500">指向 <code className="bg-[#2c2c2e] px-1 py-0.5 rounded text-purple-300">rpa-worker</code> 服务的内部地址。</p>
                    </div>
                    </div>
                )}
                </div>

                {/* PPT Config */}
                <div className="glass-card p-6 border-0">
                <div className="flex flex-row items-center gap-4 mb-6">
                    <div className="w-12 h-12 bg-orange-500/10 rounded-xl flex items-center justify-center text-orange-400 border border-orange-500/20">
                    <FileText size={24} />
                    </div>
                    <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white">文档/PPT 生成引擎 (Deliverables)</h3>
                    <p className="text-sm text-slate-400">管理输出文档的模板库与样式规范。</p>
                    </div>
                    <Switch checked={config.ppt_enabled} onCheckedChange={(v) => setConfig({...config, ppt_enabled: v})} />
                </div>
                
                {config.ppt_enabled && (
                    <div className="pl-16 grid gap-4 animate-in fade-in slide-in-from-top-2">
                    <div className="grid gap-2">
                        <Label htmlFor="ppt_template" className="text-slate-300">默认 PPT 模板路径</Label>
                        <Input 
                        id="ppt_template" 
                        value={config.ppt_template_path}
                        className="bg-black/30 border-white/10 text-white"
                        onChange={(e) => setConfig({...config, ppt_template_path: e.target.value})} 
                        />
                    </div>
                    </div>
                )}
                </div>
            </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
