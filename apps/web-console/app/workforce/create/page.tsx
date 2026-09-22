"use client";
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { User, Save, ArrowLeft, Bot, Wrench, Check, Sparkles, Brain, LayoutTemplate } from 'lucide-react';
import Link from 'next/link';
import { PageHeader } from '@/components/PageHeader';
import api from '../../../lib/api';
import { useToast } from '../../../contexts/ToastContext';

const PRESETS = [
  {
    name: "Arthur",
    role: "strategist",
    description: "Expert in market analysis and strategic planning.",
    system_prompt: "You are Arthur, a senior business strategist. Your goal is to analyze market trends and provide actionable insights. You think in frameworks (SWOT, PESTEL).",
    skills: ["web_search", "database_reader"]
  },
  {
    name: "Leo",
    role: "executor",
    description: "Creative content generator and social media operator.",
    system_prompt: "You are Leo, a creative copywriter and social media manager. You write engaging, viral-worthy content. You are informal but professional.",
    skills: ["web_search", "generate_content", "rpa_action"]
  },
  {
    name: "Doc",
    role: "archivist",
    description: "Knowledge manager responsible for organizing assets.",
    system_prompt: "You are Doc, a meticulous archivist. You organize information logically and verify facts before recording them.",
    skills: ["database_reader", "file_manager"]
  }
];

const AVAILABLE_SKILLS = [
    { id: "web_search", name: "联网搜索", desc: "访问实时互联网数据（Google/Bing）" },
    { id: "rpa_action", name: "浏览器自动化", desc: "控制浏览器抓取或在网站上发布内容" },
    { id: "database_reader", name: "数据库分析", desc: "查询内部业务数据库" },
    { id: "generate_content", name: "内容生成", desc: "生成文章、帖子与报告" },
    { id: "send_email", name: "邮件发送", desc: "发送通知或外联邮件" },
];

export default function CreateEmployeePage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    role: 'strategist',
    description: '',
    system_prompt: '',
    skills: [] as string[]
  });

  const loadPreset = (preset: any) => {
    setFormData({
        name: preset.name,
        role: preset.role,
        description: preset.description,
        system_prompt: preset.system_prompt,
        skills: preset.skills
    });
    showToast(`已加载模板：${preset.name}`, "success");
  };

  const toggleSkill = (skillId: string) => {
    setFormData(prev => {
        const newSkills = prev.skills.includes(skillId)
            ? prev.skills.filter(s => s !== skillId)
            : [...prev.skills, skillId];
        return { ...prev, skills: newSkills };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name) return showToast("请填写员工姓名", "error");

    setLoading(true);
    try {
        // Construct payload matching AgentCreate schema
        const payload = {
            name: formData.name,
            role: formData.role,
            description: formData.description,
            system_prompt: formData.system_prompt,
            capabilities: formData.skills, // Legacy/Display
            skills: formData.skills.map(skillId => ({
                tool_name: skillId,
                config: {} // Default config
            }))
        };
        
        // Assuming Project ID 1 for now
        await api.post(`/agents/1/employees`, payload);
        
        showToast("数字员工创建成功！", "success");
        router.push('/workforce');
    } catch (err: any) {
        console.error(err);
        showToast("创建数字员工失败：" + (err.message || "未知错误"), "error");
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg text-text p-6 flex justify-center selection:bg-accent/20">
      <div className="w-full max-w-6xl">
        
        {/* Header - More Compact & Action Oriented */}
        <div className="mb-6 border-b border-separator pb-4">
             <Link href="/workforce" className="inline-flex p-2 hover:bg-surface-2 rounded-lg transition-colors text-text-secondary hover:text-text group mb-2">
                 <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" />
             </Link>
             <PageHeader
                title="设计新员工"
                description="配置数字员工的角色、性格与核心能力。"
                className="mb-0"
                actions={
                    <>
                        <Link href="/workforce" className="h-10 px-4 text-sm text-text-secondary hover:text-text transition-colors flex items-center">
                            取消
                        </Link>
                        <button
                            onClick={handleSubmit}
                            disabled={loading}
                            className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-on-accent h-10 px-5 rounded-md text-sm font-medium transition-all shadow-card active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? '创建中...' : (
                                <>
                                    <Save size={18} /> 保存配置
                                </>
                            )}
                        </button>
                    </>
                }
             />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
             
             {/* Left: Main Configuration (8 cols) */}
             <div className="lg:col-span-8 flex flex-col gap-6">
                
                {/* Identity Section */}
                <div className="bg-surface border border-separator rounded-xl p-5 shadow-sm hover:border-accent/30 transition-colors">
                    <h2 className="text-sm font-bold text-accent uppercase tracking-wider mb-5 flex items-center gap-2 border-b border-separator pb-2">
                        <User size={16}/> 基础身份
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <div className="md:col-span-1">
                            <label className="block text-xs font-semibold text-text mb-1.5 pl-1">员工姓名</label>
                            <input 
                                type="text" 
                                value={formData.name}
                                onChange={(e) => setFormData({...formData, name: e.target.value})}
                                className="w-full bg-bg border border-separator rounded-lg px-3 py-2.5 text-text placeholder-text-tertiary focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all text-sm font-medium"
                                placeholder="例如：Arthur"
                            />
                        </div>
                        <div className="md:col-span-1">
                            <label className="block text-xs font-semibold text-text mb-1.5 pl-1">职能角色</label>
                            <div className="relative">
                                <select
                                    value={formData.role}
                                    onChange={(e) => setFormData({...formData, role: e.target.value})}
                                    className="w-full bg-bg border border-separator rounded-lg px-3 py-2.5 text-text focus:border-accent outline-none appearance-none text-sm font-medium cursor-pointer hover:border-separator transition-colors"
                                >
                                    <option value="strategist">策略专家</option>
                                    <option value="executor">执行专员</option>
                                    <option value="archivist">档案管理员</option>
                                </select>
                                <div className="absolute right-3 top-3 pointer-events-none text-text-secondary">
                                    <LayoutTemplate size={14} />
                                </div>
                            </div>
                        </div>
                        <div className="md:col-span-2">
                            <label className="block text-xs font-semibold text-text mb-1.5 pl-1">一句话描述</label>
                            <input 
                                type="text" 
                                value={formData.description}
                                onChange={(e) => setFormData({...formData, description: e.target.value})}
                                className="w-full bg-bg border border-separator rounded-lg px-3 py-2.5 text-text placeholder-text-tertiary focus:border-accent outline-none transition-all text-sm"
                                placeholder="描述该员工的主要职责..."
                            />
                        </div>
                    </div>
                </div>

                {/* Cognition Section */}
                <div className="bg-surface border border-separator rounded-xl p-5 shadow-sm hover:border-accent/30 transition-colors">
                    <h2 className="text-sm font-bold text-accent uppercase tracking-wider mb-5 flex items-center gap-2 border-b border-separator pb-2">
                        <Brain size={16} /> 认知设定
                    </h2>
                    <div>
                        <div className="flex justify-between items-center mb-1.5 pl-1">
                            <label className="block text-xs font-semibold text-text">角色指令</label>
                            <span className="text-[10px] text-accent bg-accent/10 border border-accent/20 px-2 py-0.5 rounded font-mono">System Prompt</span>
                        </div>
                        <textarea 
                            value={formData.system_prompt}
                            onChange={(e) => setFormData({...formData, system_prompt: e.target.value})}
                            className="w-full bg-bg border border-separator rounded-lg px-4 py-3 text-text text-sm font-mono h-[180px] focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all leading-relaxed resize-none placeholder-text-tertiary"
                            placeholder="你是一个经验丰富的商业分析师，擅长使用 SWOT 分析法..."
                        />
                    </div>
                </div>

                {/* Skills Section */}
                <div className="bg-surface border border-separator rounded-xl p-5 shadow-sm hover:border-accent/30 transition-colors">
                    <h2 className="text-sm font-bold text-accent uppercase tracking-wider mb-5 flex items-center gap-2 border-b border-separator pb-2">
                        <Wrench size={16} /> 能力工具箱
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {AVAILABLE_SKILLS.map(skill => {
                            const isSelected = formData.skills.includes(skill.id);
                            return (
                                <div 
                                    key={skill.id}
                                    onClick={() => toggleSkill(skill.id)}
                                    className={`relative p-3 rounded-lg border cursor-pointer transition-all flex flex-col gap-2 group select-none ${
                                        isSelected 
                                        ? 'bg-accent/10 border-accent/50 shadow-none' 
                                        : 'bg-bg border-separator hover:border-separator hover:bg-surface-2'
                                    }`}
                                >
                                    <div className="flex justify-between items-start">
                                        <div className={`text-sm font-bold ${isSelected ? 'text-accent' : 'text-text'}`}>
                                            {skill.name}
                                        </div>
                                        <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                                            isSelected ? 'bg-accent border-accent' : 'border-separator bg-surface'
                                        }`}>
                                            {isSelected && <Check size={10} className="text-on-accent" />}
                                        </div>
                                    </div>
                                    <div className={`text-xs leading-snug ${isSelected ? 'text-accent/70' : 'text-text-secondary'}`}>
                                        {skill.desc}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

             </div>

             {/* Right: Templates Sidebar (4 cols) */}
             <div className="lg:col-span-4 space-y-4">
                <div className="bg-surface border border-separator rounded-xl p-5 sticky top-6">
                    <h3 className="text-sm font-bold text-text mb-4 flex items-center gap-2">
                        <Sparkles size={16} className="text-warning"/> 
                        快速模板
                    </h3>
                    <div className="space-y-3">
                        {PRESETS.map((preset, i) => (
                            <div 
                                key={i} 
                                onClick={() => loadPreset(preset)}
                                className="group relative bg-bg border border-separator hover:border-accent/40 p-3 rounded-lg cursor-pointer transition-all hover:shadow-lg hover:shadow-card"
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <div className="w-10 h-10 rounded-md bg-surface border border-separator flex items-center justify-center text-accent group-hover:bg-accent-hover group-hover:text-on-accent group-hover:border-accent transition-all">
                                        <Bot size={20} />
                                    </div>
                                    <div>
                                        <div className="font-bold text-text text-sm group-hover:text-accent">{preset.name}</div>
                                        <div className="text-[10px] text-text-secondary uppercase font-semibold tracking-wider group-hover:text-accent transition-colors">{preset.role}</div>
                                    </div>
                                </div>
                                <p className="text-xs text-text-secondary leading-relaxed mb-2 line-clamp-2">
                                    {preset.description}
                                </p>
                                {/* Mini tags */}
                                <div className="flex flex-wrap gap-1">
                                    {preset.skills.slice(0, 3).map((s, idx) => (
                                        <span key={idx} className="text-[9px] bg-surface text-text-secondary border-separator px-1.5 py-0.5 rounded border group-hover:border-separator group-hover:text-text-secondary transition-colors">
                                            {AVAILABLE_SKILLS.find(as => as.id === s)?.name || s}
                                        </span>
                                    ))}
                                    {preset.skills.length > 3 && (
                                        <span className="text-[9px] text-text-tertiary px-1">+ {preset.skills.length - 3}</span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
             </div>
        </div>

      </div>
    </div>
  );
}

function BrainCircuitIcon() {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />
            <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" />
            <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4" />
            <path d="M17.599 6.5a3 3 0 0 0 .399-1.375" />
            <path d="M6.003 5.125A3 3 0 0 0 6.401 6.5" />
            <path d="M3.477 10.896a4 4 0 0 1 .585-.396" />
            <path d="M19.938 10.5a4 4 0 0 1 .585.396" />
            <path d="M6 18a4 4 0 0 1-1.97-3.284" />
            <path d="M17.97 14.716A4 4 0 0 1 16 18" />
        </svg>
    )
}
