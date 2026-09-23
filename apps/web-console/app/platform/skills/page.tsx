"use client";

import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Save, Search, Server, FileText, Terminal, Loader2, RefreshCw } from 'lucide-react';
import { useToast } from "@/contexts/ToastContext";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/ui/empty-state";

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
      <PageHeader
          title="技能工具箱"
          description="管理数字员工可调用的核心能力模块。既包括基础服务的连接配置，也包含业务层面的具体技能定义。"
          actions={
              <Button onClick={handleSave} disabled={loading} className="gap-2">
                  <Save size={16} /> {loading ? "保存中..." : "保存全局配置"}
              </Button>
          }
      />

      <Tabs defaultValue="library" className="w-full">
        <TabsList className="mb-6 bg-surface border border-separator">
           <TabsTrigger value="library" className="px-6 data-[state=active]:bg-accent data-[state=active]:text-on-accent">
             <Terminal className="w-4 h-4 mr-2" />
             业务技能
           </TabsTrigger>
           <TabsTrigger value="config" className="px-6 data-[state=active]:bg-accent data-[state=active]:text-on-accent">
             <Server className="w-4 h-4 mr-2" />
             基础技能
           </TabsTrigger>
        </TabsList>

        {/* Tab 1: 业务技能 (原 Registry) */}
        <TabsContent value="library" className="animate-in fade-in slide-in-from-left-4">
             {skillsLoading ? (
                 <EmptyState
                     icon={Loader2}
                     size="sm"
                     title="正在加载技能清单…"
                     className="h-60"
                 />
             ) : skillsError ? (
                 <EmptyState
                     icon={RefreshCw}
                     size="sm"
                     title="技能清单加载失败"
                     description={skillsError}
                     actionLabel="重试"
                     onAction={fetchSkills}
                     className="h-60"
                 />
             ) : skills.length === 0 ? (
             <EmptyState
                 icon={Terminal}
                 size="lg"
                 title="暂无可用技能"
                 description="后端尚未注册任何技能，请确认技能注册服务已启动。"
             />
             ) : (
             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {skills.map((skill) => (
                <div key={skill.name} className="glass-card p-6 relative group hover:bg-surface-2/60 transition-all border-0">
                    <div className={"w-10 h-10 rounded-lg flex items-center justify-center mb-4 border " + (skill.category === "system" ? "bg-accent/10 text-accent border-accent/20" : "bg-success/10 text-success border-success/20")}>
                        <Terminal size={20} />
                    </div>
                    <div className="mb-1">
                        <h3 className="font-semibold text-lg text-text">{skill.name}</h3>
                    </div>
                    <code className="text-xs bg-surface-2 px-1 py-0.5 rounded text-text-secondary border border-separator">{skill.name}</code>
                    <p className="text-sm text-text-secondary mt-3 line-clamp-2">{skill.description || "暂无描述"}</p>
                    {skill.parameters.length > 0 && (
                        <div className="mt-3 space-y-1">
                            {skill.parameters.map((p) => (
                                <div key={p.name} className="text-xs text-text-secondary font-mono">
                                    <span className="text-text">{p.name}</span>
                                    <span className="text-text-tertiary">: {p.type}{p.required ? " *" : ""}</span>
                                </div>
                            ))}
                        </div>
                    )}
                    <div className="mt-4 pt-4 border-t border-separator flex gap-2">
                        {skill.tags.map((tag) => (
                            <span key={tag} className={"px-2 py-0.5 text-xs rounded border " + (tag === "System" ? "bg-surface-2 text-text-secondary border-separator" : tag === "Business" ? "bg-accent/10 text-accent border-accent/20" : "bg-surface-2 text-text border-separator")}>{tag === "System" ? "系统" : tag === "Business" ? "业务" : tag}</span>
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
                    <div className="w-12 h-12 bg-accent/10 rounded-xl flex items-center justify-center text-accent border border-accent/20">
                    <Search size={24} />
                    </div>
                    <div className="flex-1">
                    <h3 className="text-lg font-semibold text-text">联网深度调研</h3>
                    <p className="text-sm text-text-secondary">配置 Google/Bing 搜索接口，赋予员工实时联网获取信息的能力。</p>
                    </div>
                    <Switch checked={config.web_search_enabled} onCheckedChange={(v) => setConfig({...config, web_search_enabled: v})} />
                </div>
                
                {config.web_search_enabled && (
                    <div className="pl-16 grid gap-4 animate-in fade-in slide-in-from-top-2">
                    <div className="grid gap-2">
                        <Label htmlFor="api_key" className="text-text">SerpApi Key / Bing API Key</Label>
                        <div className="flex gap-2">
                        <Input 
                            id="api_key" 
                            type="password" 
                            value={config.serp_api_key} 
                            className="bg-bg/30 border-separator text-text"
                            onChange={(e) => setConfig({...config, serp_api_key: e.target.value})}
                        />
                        <Button variant="outline" className="border-separator">验证连接</Button>
                        </div>
                        <p className="text-xs text-text-secondary">用于 <code className="bg-surface-2 px-1 py-0.5 rounded text-accent">web_search</code> 技能调用外部搜索引擎。</p>
                    </div>
                    </div>
                )}
                </div>

                {/* RPA Config */}
                <div className="glass-card p-6 border-0">
                <div className="flex flex-row items-center gap-4 mb-6">
                    <div className="w-12 h-12 bg-accent/10 rounded-xl flex items-center justify-center text-accent border border-accent/20">
                    <Server size={24} />
                    </div>
                    <div className="flex-1">
                    <h3 className="text-lg font-semibold text-text">RPA 浏览器自动化</h3>
                    <p className="text-sm text-text-secondary">配置 RPA Worker 集群地址，用于执行网页操作、截图与模拟登录任务。</p>
                    </div>
                    <Switch checked={config.rpa_enabled} onCheckedChange={(v) => setConfig({...config, rpa_enabled: v})} />
                </div>
                
                {config.rpa_enabled && (
                    <div className="pl-16 grid gap-4 animate-in fade-in slide-in-from-top-2">
                    <div className="grid gap-2">
                        <Label htmlFor="rpa_url" className="text-text">RPA Worker URL</Label>
                        <Input 
                        id="rpa_url" 
                        value={config.rpa_worker_url}
                        className="bg-bg/30 border-separator text-text"
                        onChange={(e) => setConfig({...config, rpa_worker_url: e.target.value})} 
                        />
                        <p className="text-xs text-text-secondary">指向 <code className="bg-surface-2 px-1 py-0.5 rounded text-accent">rpa-worker</code> 服务的内部地址。</p>
                    </div>
                    </div>
                )}
                </div>

                {/* PPT Config */}
                <div className="glass-card p-6 border-0">
                <div className="flex flex-row items-center gap-4 mb-6">
                    <div className="w-12 h-12 bg-warning/10 rounded-xl flex items-center justify-center text-warning border border-warning/20">
                    <FileText size={24} />
                    </div>
                    <div className="flex-1">
                    <h3 className="text-lg font-semibold text-text">文档/PPT 生成引擎</h3>
                    <p className="text-sm text-text-secondary">管理输出文档的模板库与样式规范。</p>
                    </div>
                    <Switch checked={config.ppt_enabled} onCheckedChange={(v) => setConfig({...config, ppt_enabled: v})} />
                </div>
                
                {config.ppt_enabled && (
                    <div className="pl-16 grid gap-4 animate-in fade-in slide-in-from-top-2">
                    <div className="grid gap-2">
                        <Label htmlFor="ppt_template" className="text-text">默认 PPT 模板路径</Label>
                        <Input 
                        id="ppt_template" 
                        value={config.ppt_template_path}
                        className="bg-bg/30 border-separator text-text"
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
