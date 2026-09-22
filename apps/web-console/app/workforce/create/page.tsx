"use client";
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { User, Save, ArrowLeft, Bot, Wrench, FileText, Check, Sparkles, Brain, LayoutTemplate } from 'lucide-react';
import Link from 'next/link';
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
    { id: "web_search", name: "Web Search", desc: "Access real-time internet data (Google/Bing)" },
    { id: "rpa_action", name: "RPA Browser", desc: "Control browser to scrape or post on websites" },
    { id: "database_reader", name: "DB Analytics", desc: "Query internal business databases" },
    { id: "generate_content", name: "Content Gen", desc: "Generate articles, posts, and reports" },
    { id: "send_email", name: "Email Sender", desc: "Send notifications or outreach emails" },
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
    showToast(`Loaded template: ${preset.name}`, "success");
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
    if (!formData.name) return showToast("Name is required", "error");

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
        
        showToast("Digital Employee created successfully!", "success");
        router.push('/workforce');
    } catch (err: any) {
        console.error(err);
        showToast("Failed to create employee: " + (err.message || "Unknown error"), "error");
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-slate-200 p-6 flex justify-center selection:bg-[#0a84ff]/20">
      <div className="w-full max-w-6xl">
        
        {/* Header - More Compact & Action Oriented */}
        <div className="mb-6 flex items-center justify-between border-b border-white/8/60 pb-4">
             <div className="flex items-center gap-3">
                <Link href="/workforce" className="p-2 hover:bg-[#2c2c2e] rounded-lg transition-colors text-slate-400 hover:text-white group">
                    <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" />
                </Link>
                <div>
                    <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                        <Bot className="text-[#0a84ff]" size={24}/> 
                        设计新员工 (New Employee)
                    </h1>
                    <p className="text-slate-400 text-xs mt-0.5">配置数字员工的角色、性格与核心能力。</p>
                </div>
             </div>
             <div className="flex gap-3">
                 <Link href="/workforce" className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors flex items-center">
                    取消
                 </Link>
                 <button 
                    onClick={handleSubmit} 
                    disabled={loading}
                    className="flex items-center gap-2 bg-[#0071e3] hover:bg-[#0077ed] text-white px-5 py-2.5 rounded-full text-sm font-medium transition-all shadow-apple active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-apple"
                >
                    {loading ? '创建中...' : (
                        <>
                            <Save size={18} /> 保存配置
                        </>
                    )}
                </button>
             </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
             
             {/* Left: Main Configuration (8 cols) */}
             <div className="lg:col-span-8 flex flex-col gap-6">
                
                {/* Identity Section */}
                <div className="bg-[#1c1c1e] border border-white/8 rounded-xl p-5 shadow-sm hover:border-[#0a84ff]/30 transition-colors">
                    <h2 className="text-sm font-bold text-[#0a84ff] uppercase tracking-wider mb-5 flex items-center gap-2 border-b border-white/8 pb-2">
                        <User size={16}/> 基础身份 (Identity)
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <div className="md:col-span-1">
                            <label className="block text-xs font-semibold text-slate-300 mb-1.5 pl-1">员工姓名</label>
                            <input 
                                type="text" 
                                value={formData.name}
                                onChange={(e) => setFormData({...formData, name: e.target.value})}
                                className="w-full bg-black border border-white/10 rounded-lg px-3 py-2.5 text-white placeholder-slate-600 focus:border-[#0a84ff] focus:ring-1 focus:ring-[#0a84ff] outline-none transition-all text-sm font-medium"
                                placeholder="例如：Arthur"
                            />
                        </div>
                        <div className="md:col-span-1">
                            <label className="block text-xs font-semibold text-slate-300 mb-1.5 pl-1">职能角色</label>
                            <div className="relative">
                                <select
                                    value={formData.role}
                                    onChange={(e) => setFormData({...formData, role: e.target.value})}
                                    className="w-full bg-black border border-white/10 rounded-lg px-3 py-2.5 text-white focus:border-[#0a84ff] outline-none appearance-none text-sm font-medium cursor-pointer hover:border-white/20 transition-colors"
                                >
                                    <option value="strategist">Strategist (策略专家)</option>
                                    <option value="executor">Executor (执行专员)</option>
                                    <option value="archivist">Archivist (档案管理员)</option>
                                </select>
                                <div className="absolute right-3 top-3 pointer-events-none text-slate-500">
                                    <LayoutTemplate size={14} />
                                </div>
                            </div>
                        </div>
                        <div className="md:col-span-2">
                            <label className="block text-xs font-semibold text-slate-300 mb-1.5 pl-1">一句话描述</label>
                            <input 
                                type="text" 
                                value={formData.description}
                                onChange={(e) => setFormData({...formData, description: e.target.value})}
                                className="w-full bg-black border border-white/10 rounded-lg px-3 py-2.5 text-white placeholder-slate-600 focus:border-[#0a84ff] outline-none transition-all text-sm"
                                placeholder="描述该员工的主要职责..."
                            />
                        </div>
                    </div>
                </div>

                {/* Cognition Section */}
                <div className="bg-[#1c1c1e] border border-white/8 rounded-xl p-5 shadow-sm hover:border-[#0a84ff]/30 transition-colors">
                    <h2 className="text-sm font-bold text-[#0a84ff] uppercase tracking-wider mb-5 flex items-center gap-2 border-b border-white/8 pb-2">
                        <Brain size={16} /> 认知设定 (System Prompt)
                    </h2>
                    <div>
                        <div className="flex justify-between items-center mb-1.5 pl-1">
                            <label className="block text-xs font-semibold text-slate-300">角色指令 (Persona & Instructions)</label>
                            <span className="text-[10px] text-[#64d2ff] bg-[#0a84ff]/10 border border-[#0a84ff]/20 px-2 py-0.5 rounded font-mono">System Prompt</span>
                        </div>
                        <textarea 
                            value={formData.system_prompt}
                            onChange={(e) => setFormData({...formData, system_prompt: e.target.value})}
                            className="w-full bg-black border border-white/10 rounded-lg px-4 py-3 text-slate-200 text-sm font-mono h-[180px] focus:border-[#0a84ff] focus:ring-1 focus:ring-[#0a84ff] outline-none transition-all leading-relaxed resize-none placeholder-slate-700"
                            placeholder="你是一个经验丰富的商业分析师，擅长使用 SWOT 分析法..."
                        />
                    </div>
                </div>

                {/* Skills Section */}
                <div className="bg-[#1c1c1e] border border-white/8 rounded-xl p-5 shadow-sm hover:border-[#0a84ff]/30 transition-colors">
                    <h2 className="text-sm font-bold text-[#0a84ff] uppercase tracking-wider mb-5 flex items-center gap-2 border-b border-white/8 pb-2">
                        <Wrench size={16} /> 能力工具箱 (Skills)
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
                                        ? 'bg-[#0a84ff]/10 border-[#0a84ff]/50 shadow-none' 
                                        : 'bg-black border-white/8 hover:border-white/20 hover:bg-[#2c2c2e]'
                                    }`}
                                >
                                    <div className="flex justify-between items-start">
                                        <div className={`text-sm font-bold ${isSelected ? 'text-[#64d2ff]' : 'text-slate-300'}`}>
                                            {skill.name}
                                        </div>
                                        <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                                            isSelected ? 'bg-[#0a84ff] border-[#0a84ff]' : 'border-white/10 bg-[#1c1c1e]'
                                        }`}>
                                            {isSelected && <Check size={10} className="text-white" />}
                                        </div>
                                    </div>
                                    <div className={`text-xs leading-snug ${isSelected ? 'text-[#7dc1ff]/70' : 'text-slate-500'}`}>
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
                <div className="bg-[#1c1c1e] border border-white/8 rounded-xl p-5 sticky top-6">
                    <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                        <Sparkles size={16} className="text-yellow-500"/> 
                        快速模板 (Templates)
                    </h3>
                    <div className="space-y-3">
                        {PRESETS.map((preset, i) => (
                            <div 
                                key={i} 
                                onClick={() => loadPreset(preset)}
                                className="group relative bg-black border border-white/8 hover:border-[#0a84ff]/40 p-3 rounded-lg cursor-pointer transition-all hover:shadow-lg hover:shadow-apple"
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <div className="w-10 h-10 rounded-md bg-[#1c1c1e] border border-white/8 flex items-center justify-center text-[#0a84ff] group-hover:bg-[#0077ed] group-hover:text-white group-hover:border-[#0a84ff] transition-all">
                                        <Bot size={20} />
                                    </div>
                                    <div>
                                        <div className="font-bold text-slate-200 text-sm group-hover:text-white">{preset.name}</div>
                                        <div className="text-[10px] text-slate-500 uppercase font-semibold tracking-wider group-hover:text-[#64d2ff] transition-colors">{preset.role}</div>
                                    </div>
                                </div>
                                <p className="text-xs text-slate-400 leading-relaxed mb-2 line-clamp-2">
                                    {preset.description}
                                </p>
                                {/* Mini tags */}
                                <div className="flex flex-wrap gap-1">
                                    {preset.skills.slice(0, 3).map((s, idx) => (
                                        <span key={idx} className="text-[9px] bg-[#1c1c1e] text-slate-500 border-white/8 px-1.5 py-0.5 rounded border group-hover:border-white/16 group-hover:text-slate-400 transition-colors">
                                            {AVAILABLE_SKILLS.find(as => as.id === s)?.name || s}
                                        </span>
                                    ))}
                                    {preset.skills.length > 3 && (
                                        <span className="text-[9px] text-slate-600 px-1">+ {preset.skills.length - 3}</span>
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
