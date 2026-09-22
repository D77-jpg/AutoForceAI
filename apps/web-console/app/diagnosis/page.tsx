"use client";

import React, { useState, useEffect } from 'react';
import { 
  Search, TrendingUp, AlertTriangle, ShieldCheck, 
  BarChart2, Map, Globe, Share2, Eye, BrainCircuit, ArrowRightCircle, Copy, Check,
  Cpu, Terminal, CheckCircle2, MessageSquare, RotateCcw
} from 'lucide-react';
import { useGlobalState } from '../../contexts/GlobalStateContext';
import { useToast } from '../../contexts/ToastContext';
import api from '../../lib/api';
// import { Radar, Pie, Line } from 'react-chartjs-2'; // Mocking charts for now
import { 
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend
} from 'recharts';

import { useRouter, useSearchParams } from 'next/navigation';

interface Model {
    id: number;
    name: string;
    display_name: string;
    supports_geo: boolean;
}

const defaultRadarData = [
  { subject: '品牌可见性', A: 0, B: 0, fullMark: 150 },
  { subject: '情感倾向', A: 0, B: 0, fullMark: 150 },
  { subject: '引用质量', A: 0, B: 0, fullMark: 150 },
  { subject: '功能推荐', A: 0, B: 0, fullMark: 150 },
  { subject: '成本感知', A: 0, B: 0, fullMark: 150 },
  { subject: '创新程度', A: 0, B: 0, fullMark: 150 },
];

// Simple Typewriter Component
const TypewriterEffect = ({ text }: { text: string }) => {
    const [displayedText, setDisplayedText] = useState("");
    
    useEffect(() => {
        let index = 0;
        setDisplayedText(""); // Reset on text change
        
        if (!text) return;

        const intervalId = setInterval(() => {
            setDisplayedText((prev) => prev + text.charAt(index));
            index++;
            if (index >= text.length) {
                clearInterval(intervalId);
            }
        }, 30); // Speed: 30ms per char

        return () => clearInterval(intervalId);
    }, [text]);

    return (
        <p dangerouslySetInnerHTML={{ 
            __html: displayedText.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white bg-[#0a84ff]/16 px-1 rounded">$1</strong>').replace(/\n/g, '<br/>') 
        }} />
    );
};

export default function Diagnosis() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Persistence via Global State
  const { 
    diagBrand: brand, setDiagBrand: setBrand,
    diagCompetitor: competitor, setDiagCompetitor: setCompetitor,
    diagUserQueries: userQueries, setDiagUserQueries: setUserQueries,
    diagSelectedModel: selectedModel, setDiagSelectedModel: setSelectedModel,
    diagResult: result, setDiagResult: setResult
  } = useGlobalState();
  
  const { showToast } = useToast(); // Add toast hook

  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0); 
  const [progressText, setProgressText] = useState("正在初始化...");
  const [geoModels, setGeoModels] = useState<Model[]>([]);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  
  // New state for streaming
  const [streamingSnippet, setStreamingSnippet] = useState<string | null>(null);

  useEffect(() => {
    const fetchGeoModels = async () => {
        try {
            const res = await api.get('/api/v1/platform/models?geo_only=true');
            setGeoModels(res.data);
        } catch (e) {
            console.error("Failed to load GEO models", e);
        }
    };
    fetchGeoModels();
    const hydrateRadar = async () => {
        if (result) return;
        try {
            const res = await api.get(`/api/v1/branding/diagnosis-summary${brand ? `?brand=${encodeURIComponent(brand)}` : ''}`);
            const s = res.data;
            if (!s || !s.sample_size) return;
            setResult({
                bestRank: s.best_rank,
                sov: (s.radar || []).map((row: any) => ({ ...row, B: 0 })),
                pieData: s.pie,
                insights: [
                    s.mentioned
                        ? `✅ 基于 ${s.sample_size} 条真实监测：品牌被提及 ${s.mentioned} 次（${s.mention_rate}%）。`
                        : `⚠️ 近 ${s.sample_size} 条监测尚未提及该品牌。`,
                    `情感均分 ${s.avg_sentiment}；最佳排名 ${s.best_rank > 0 ? s.best_rank : '未上榜'}。`,
                    s.engine_configured?.perplexity ? 'Perplexity Key 已配置。' : 'Perplexity 走 mock（配置 PERPLEXITY_API_KEY 后为真实英文检索）。',
                ],
                queryAnalysis: (s.recent || []).map((t: any) => ({
                    question: t.query,
                    mentioned: t.is_mentioned,
                    sentiment: (t.sentiment_score || 0) > 5 ? '正面 (Positive)' : '中性 (Neutral)',
                    snippet: '',
                    snippet_raw: '',
                    rank: t.rank_position || -1,
                })),
            });
        } catch (e) {
            console.error('diagnosis-summary', e);
        }
    };
    hydrateRadar();
  }, [])

  const handleAnalyze = async () => {
    // 1. Validation
    const queries = userQueries.split('\n').filter(q => q.trim());
    if (queries.length === 0) {
        showToast("请输入至少一个测试问题", "error");
        return;
    }
    if (!brand) {
        showToast("请输入品牌名称", "error");
        return;
    }

    setAnalyzing(true);
    setProgress(5);
    setProgressText("正在初始化分析任务 (Initializing)...");
    setResult(null);
    setStreamingSnippet(null); // Reset streaming

    try {
        // 2. Submit Tasks
        const taskIds: number[] = [];
        for (const q of queries) {
             try {
                const res = await api.post('/api/v1/branding/analyze', {
                    target_brand: brand,
                    query: q,
                    engine_name: selectedModel === 'auto' ? 'perplexity' : selectedModel
                });
                if (res.data && res.data.id) {
                    taskIds.push(res.data.id);
                }
             } catch (e) {
                 console.error(e);
             }
        }

        if (taskIds.length === 0) {
            setAnalyzing(false);
            showToast("此时无法启动分析任务", "error");
            return;
        }
        
        setProgress(20);
        setProgressText("正在全网搜索品牌相关信息 (Searching)...");

        // 3. Polling Logic
        const maxRetries = 120; 
        let attempts = 0;

        const checkLoop = setInterval(async () => {
             attempts++;
             if (attempts > maxRetries) {
                 clearInterval(checkLoop);
                 setAnalyzing(false);
                 showToast("分析耗时过长，请稍后在历史记录中查看", "warning");
                 return;
             }

             let pending = 0;
             const currentResults: any[] = [];

             for (const tid of taskIds) {
                 try {
                     const tRes = await api.get(`/api/v1/branding/tasks/${tid}`);
                     const task = tRes.data;
                     if (task.status === 'completed' || task.status === 'failed') {
                         currentResults.push(task);
                         
                         // Immediate Streaming: If we have a completed task and no text displayed yet, capture it
                         if (!streamingSnippet && task.raw_response) {
                             try {
                                 const data = JSON.parse(task.raw_response);
                                 const snippet = data.snippet || task.reasoning || "";
                                 if (snippet) {
                                     setStreamingSnippet(snippet);
                                 }
                             } catch (e) {}
                         }

                     } else {
                         pending++;
                     }
                 } catch(e) { console.error(e); pending++; }
             }
             
             // Update progress
             const total = taskIds.length;
             const percent = 20 + ((total - pending) / total) * 80;
             setProgress(Math.floor(percent));

             if (percent < 50) {
                 setProgressText("正在获取搜索引擎反馈 (Fetching)...");
             } else if (percent < 80) {
                 setProgressText("正在进行语义分析及情感计算 (Analyzing)...");
             } else {
                 setProgressText("正在生成最终诊断报告 (Generating)...");
             }

             if (pending === 0) {
                 clearInterval(checkLoop);
                 processFinalResults(currentResults, queries);
             }
        }, 2000); // Check every 2s

    } catch (e) {
        console.error(e);
        setAnalyzing(false);
        showToast("启动分析失败", "error");
    }
  };

  const processFinalResults = (tasks: any[], originalQueries: string[]) => {
      setAnalyzing(false);
      setProgress(100);
      setProgressText("分析完成 (Completed)");
      
      const analysisItems = tasks.map((t, idx) => {
          // Parse snippet from raw_response if available
          let snippet = "";
          try {
              if (t.raw_response) {
                  const data = JSON.parse(t.raw_response);
                  snippet = data.snippet || t.reasoning || "";
              }
          } catch (e) {
              snippet = t.reasoning || "";
          }

          if (!snippet && t.status === 'failed') {
             snippet = `(分析失败) ${t.reasoning || '未知错误'}`;
          }

          // Robust isMentioned Check (Matches GEO Dashboard Logic)
          const isMentioned = 
              t.is_mentioned === true || 
              String(t.is_mentioned).toLowerCase() === 'true' || 
              t.is_mentioned === 1 || 
              String(t.is_mentioned) === '1' ||
              (t.rank_position && Number(t.rank_position) > 0);

          return {
             question: t.query,
             mentioned: isMentioned,
             sentiment: t.sentiment_score > 5 ? "正面 (Positive)" : (t.sentiment_score < 5 ? "负面 (Negative)" : "中性 (Neutral)"),
             snippet: snippet,
             snippet_raw: snippet, // Keep raw for display
             rank: t.rank_position || -1
          };
      });

      // Clear streaming snippet as result takes over
      setStreamingSnippet(null); 

      const mentionCount = analysisItems.filter(i => i.mentioned).length;
      const queriesCount = analysisItems.length;
      const validRanks = analysisItems.filter(i => i.mentioned && i.rank > 0).map(i => i.rank);
      const bestRank = validRanks.length > 0 ? Math.min(...validRanks) : -1;

      // Calculate Stats
      const sovScore = queriesCount > 0 ? (mentionCount / queriesCount) * 100 : 0;
      const avgSent = tasks.reduce((a, t) => a + (Number(t.sentiment_score) || 0), 0) / Math.max(queriesCount, 1);
      const citationN = tasks.reduce((a, t) => a + (Array.isArray(t.citations) ? t.citations.length : 0), 0);

      setResult({
          bestRank: bestRank,
          sov: [
              { subject: '品牌可见性', A: Math.min(150, sovScore * 1.5), B: competitor ? 110 : 0, fullMark: 150 },
              { subject: '情感倾向', A: Math.min(150, (avgSent / 10) * 150), B: competitor ? 90 : 0, fullMark: 150 },
              { subject: '引用质量', A: mentionCount > 0 ? Math.min(150, 40 + citationN * 8) : 0, B: competitor ? 60 : 0, fullMark: 150 },
              { subject: '功能推荐', A: mentionCount > 0 ? Math.min(150, 50 + mentionCount * 12) : 0, B: competitor ? 70 : 0, fullMark: 150 },
              { subject: '成本感知', A: mentionCount > 0 ? Math.min(150, 70 + sovScore * 0.4) : 0, B: competitor ? 80 : 0, fullMark: 150 },
              { subject: '创新程度', A: mentionCount > 0 ? Math.min(150, 45 + sovScore * 0.6) : 0, B: competitor ? 75 : 0, fullMark: 150 },
          ],
          pieData: [
              { name: '品牌提及 (Mentioned)', value: mentionCount },
              { name: '未被提及 (Missed)', value: queriesCount - mentionCount },
          ],
          insights: [
              mentionCount < queriesCount 
                  ? `⚠️ **${analysisItems.find(a => !a.mentioned)?.question || '问答测试'}** 结果显示品牌未被提及。` 
                  : `✅ 祝贺！您的品牌 **${brand}** 在所有测试问题中均获得推荐。`,
              
              mentionCount === 0
                  ? `❌ 在当前的回答中，模型未收录关于 **${brand}** 的信息。`
                  : `✅ 在 ${queriesCount} 个测试问题中，模型推荐了 **${brand}** (${mentionCount}次)。`,

              competitor 
                  ? `💡 机会点：需重点关注与 **${competitor}** 的差异化对比。` 
                  : (mentionCount === 0 ? `💡 建议：这是"冷启动"信号。请点击下方"优化"按钮，针对缺失的场景生成内容。` : `💡 建议：继续保持，并尝试扩展更多长尾问题场景。`)
          ],
          queryAnalysis: analysisItems
      });
  };

  const COLORS = ['#10b981', '#ef4444', '#334155'];

  const handleTestModel = () => {
    // Official Model URLs
    const MODEL_URLS: Record<string, string> = {
        'zhipu': 'https://chatglm.cn/',
        'qwen': 'https://tongyi.aliyun.com/',
        'kimi': 'https://kimi.moonshot.cn/',
        'doubao': 'https://www.doubao.com/',
        'gpt': 'https://chat.openai.com/'
    };

    let url = 'https://chatglm.cn/'; // Default
    const current = selectedModel.toLowerCase();

    if (current.includes('qwen') || current.includes('ali')) url = MODEL_URLS['qwen'];
    else if (current.includes('kimi') || current.includes('moonshot')) url = MODEL_URLS['kimi'];
    else if (current.includes('doubao')) url = MODEL_URLS['doubao'];
    else if (current.includes('gpt') || current.includes('openai')) url = MODEL_URLS['gpt'];
    else url = MODEL_URLS['zhipu'];

    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const getModelDisplayName = () => {
      if (selectedModel === 'auto') return '智谱 GLM-4 (Auto)';
      const m = geoModels.find(x => x.name === selectedModel);
      return m ? m.display_name : selectedModel;
  }

  const handleCopyQuestion = (text: string, idx: number) => {
      navigator.clipboard.writeText(text);
      setCopiedId(idx);
      setTimeout(() => setCopiedId(null), 2000);
  }

  // Auto-start diagnosis if requested via URL param (e.g. from GEO page)
  useEffect(() => {
    const auto = searchParams.get('auto');
    if (auto === 'true' && brand && userQueries && !analyzing && !result) {
        // Use a small timeout to ensure state is ready and avoid hydration mismatch if any
        const timer = setTimeout(() => {
            handleAnalyze();
        }, 500);
        return () => clearTimeout(timer);
    }
  }, [searchParams]); // Only run on mount/params change to avoid loops

  return (
    <div className="min-h-screen bg-[#020408] text-slate-200 font-sans p-6 overflow-y-auto w-full custom-scrollbar">
      
      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-60px)]">
        
        {/* Left: Configuration (3 Cols) */}
        <div className="col-span-3 bg-[#1c1c1e]/60 rounded-2xl border border-white/5 flex flex-col h-full overflow-hidden">
            {/* Header */}
            <div className="p-5 border-b border-white/5 bg-white/5 shrink-0">
                 <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                    <Search size={16} className="text-[#0a84ff]" />
                    诊断目标配置
                </h3>
            </div>

            {/* Form Content */}
            <div className="p-5 overflow-y-auto custom-scrollbar flex-1 space-y-4">
                <div>
                     <label className="block text-[10px] uppercase tracking-wider text-[#64d2ff] font-bold mb-1.5">您的品牌 (Your Brand)</label>
                     <div className="relative group">
                        <input 
                            value={brand}
                            onChange={e => setBrand(e.target.value)}
                            className="w-full bg-black border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:border-[#0a84ff] outline-none transition-all group-hover:border-white/20"
                            placeholder="输入您的品牌名称"
                        />
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-600">
                             <ShieldCheck size={14} />
                        </div>
                     </div>
                </div>

                <div className="relative py-1 flex items-center justify-center">
                    <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
                    <span className="relative bg-[#0b101a] px-2 text-[10px] text-slate-500 font-mono">VS</span>
                </div>

                <div>
                    <label className="block text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1.5">竞品品牌 (Competitor)</label>
                    <input 
                        placeholder="例如: 特斯拉 (选填)"
                        value={competitor}
                        onChange={e => setCompetitor(e.target.value)}
                        className="w-full bg-black border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:border-[#0a84ff] outline-none transition-all placeholder:text-slate-600"
                    />
                </div>

                <div>
                    <label className="block text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1.5">
                        用户拟提问 (Test Queries)
                        <span className="ml-2 text-[9px] text-slate-600 bg-[#2c2c2e] px-1 py-0.5 rounded">一行一个</span>
                    </label>
                    <textarea
                        value={userQueries}
                        onChange={(e) => setUserQueries(e.target.value)}
                        className="w-full h-32 bg-black border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-300 outline-none resize-none focus:border-[#0a84ff] custom-scrollbar leading-relaxed"
                        placeholder="输入用户可能会问模型的问题..."
                    />
                </div>

                <div>
                    <label className="block text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1.5">搜索范围 (Search Scope)</label>
                    <div className="relative">
                        <select 
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                            className="w-full bg-black border border-white/10 rounded-lg px-3 py-2.5 text-sm text-slate-300 outline-none appearance-none cursor-pointer hover:border-white/20 transition-all"
                        >
                            <option value="auto">⚡ 自动选择 (Auto Mode)</option>
                            <option disabled>──────────</option>
                            {geoModels.length > 0 ? (
                                geoModels.map(m => (
                                    <option key={m.id} value={m.name}>{m.display_name}</option>
                                ))
                            ) : (
                                <>
                                    <option value="zhipu">智谱 GLM-4</option>
                                    <option value="qwen">通义千问 Qwen</option>
                                </>
                            )}
                        </select>
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500">
                            <ArrowRightCircle size={14} className="rotate-90"/>
                        </div>
                    </div>
                </div>
            </div>

            {/* Footer Action */}
            <div className="p-5 border-t border-white/5 bg-[#1c1c1e]/70 shrink-0">
                <button 
                    onClick={handleAnalyze}
                    disabled={analyzing}
                    className={`w-full py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${
                        analyzing 
                            ? 'bg-[#2c2c2e] text-slate-500 border border-white/5 cursor-not-allowed' 
                            : 'bg-gradient-to-r from-[#0071e3] to-[#0a84ff] hover:from-[#0a84ff] hover:to-[#64d2ff] text-white shadow-apple active:scale-[0.98]'
                    }`}
                >
                    {analyzing ? (
                        <>
                            <div className="w-4 h-4 border-2 border-white/20 border-t-[#0a84ff] rounded-full animate-spin"></div>
                            正在分析市场数据...
                        </>
                    ) : (
                        <>
                            <TrendingUp size={18} />
                            开启诊断洞察
                        </>
                    )}
                </button>
            </div>
        </div>

        {/* Right: Content Area (9 Cols) */}
        <div className="col-span-9 flex flex-col gap-6 h-full overflow-y-auto custom-scrollbar pr-2">
            
            {/* Top Row: Visualizations */}
            <div className="flex gap-6 h-80 shrink-0">
                {/* Radar Chart (2/3) */}
                <div className="flex-[2] bg-[#1c1c1e]/60 rounded-2xl border border-white/5 p-6 relative overflow-hidden flex flex-col">
                    <div className="flex justify-between items-start mb-2 z-10 relative">
                        <h3 className="text-sm font-bold text-slate-300">品牌维度分析 (Brand Dimensions)</h3>
                        <div className="flex items-center gap-2 bg-black/40 rounded-full px-1 pl-3 py-1 border border-white/5">
                            <span className="text-[10px] text-[#64d2ff] font-mono flex items-center gap-1">
                                <BrainCircuit size={10} />
                                {getModelDisplayName()}
                            </span>
                            <button 
                                onClick={handleTestModel}
                                className="bg-[#0071e3] hover:bg-[#0077ed] text-white p-1 rounded-full transition-colors"
                                title="测试此模型 (Test Model)"
                            >
                                <ArrowRightCircle size={12} />
                            </button>
                        </div>
                    </div>

                        <div className="flex w-full h-full relative">
                            {!result && (
                                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-10">
                                    <div className="bg-[#1c1c1e]/90 backdrop-blur-sm px-4 py-2 rounded-full border border-white/5"> 
                                        <p className="text-slate-400 font-bold text-xs">等待分析数据 (Waiting)</p>
                                    </div>
                                </div>
                            )}
                            <ResponsiveContainer width="100%" height="100%">
                                {result && result.pieData[0].value > 0 ? (
                                    <RadarChart cx="50%" cy="50%" outerRadius="70%" data={result ? result.sov : defaultRadarData}>
                                        <PolarGrid stroke="#334155" />
                                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                                        <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                                        <Radar 
                                            name={brand || "我的品牌"} 
                                            dataKey="A" 
                                            stroke={result && result.bestRank > 0 ? "#6366f1" : "#818cf8"} 
                                            strokeWidth={2} 
                                            fill={result && result.bestRank > 0 ? "#6366f1" : "#818cf8"} 
                                            fillOpacity={0.3} 
                                        />
                                        {competitor && (
                                            <Radar name={competitor} dataKey="B" stroke={result ? "#ec4899" : "#1e293b"} strokeWidth={2} fill={result ? "#ec4899" : "#1e293b"} fillOpacity={0.3} />
                                        )}
                                        <Legend />
                                        <Tooltip 
                                            contentStyle={{ backgroundColor: '#1c1c1e', borderColor: 'rgba(255,255,255,0.1)' }}
                                            itemStyle={{ color: '#e2e8f0' }}
                                        />
                                    </RadarChart>
                                ) : (
                                    <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs">
                                        <Map size={32} className="opacity-20 mb-2" />
                                        {result ? '未上榜，相关指标无法计算' : '暂无数据'}
                                    </div>
                                )}
                            </ResponsiveContainer>
                        </div>
                    </div>

                {/* Pie Chart (1/3) */}
                <div className="flex-1 bg-[#1c1c1e]/60 rounded-2xl border border-white/5 p-6 flex flex-col relative overflow-hidden">
                     <div className="flex justify-between items-center mb-2 z-10 relative">
                        <h3 className="text-sm font-bold text-slate-300">
                            {result ? '品牌提及率' : '声量份额'}
                        </h3>
                        <div className="text-[10px] bg-white/5 rounded px-2 py-0.5 text-slate-400 font-mono">
                             {getModelDisplayName()}
                        </div>
                     </div>
                     
                     {analyzing ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#1c1c1e]/80 backdrop-blur-sm z-20 space-y-4">
                            <div className="relative w-20 h-20">
                               <div className="absolute inset-0 rounded-full border-4 border-[#0a84ff]/20 border-t-[#0a84ff] animate-spin"></div>
                               <div className="absolute inset-4 rounded-full border-4 border-white/10 border-b-white/50 animate-spin-reverse"></div>
                            </div>
                            <div className="text-center space-y-1">
                                <p className="text-white text-xs font-bold">正在进行 AI 深度思考...</p>
                                <p className="text-slate-400 text-[10px] font-mono">实时获取搜索引擎数据中...</p>
                            </div>
                        </div>
                     ) : !result ? (
                         <div className="flex-1 flex items-center justify-center">
                             <div className="w-32 h-32 rounded-full border-4 border-white/8 border-t-slate-700 animate-spin opacity-50"></div>
                         </div>
                     ) : (
                        <div className="flex-1 min-h-0">
                             <ResponsiveContainer width="100%" height="100%">
                                {result.pieData[0].value > 0 ? (
                                    <PieChart>
                                        <Pie
                                            data={result.pieData}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={50}
                                            outerRadius={70}
                                            paddingAngle={5}
                                            dataKey="value"
                                        >
                                            {result.pieData.map((entry: any, index: number) => (
                                                <Cell key={`cell-${index}`} fill={index === 0 ? '#10b981' : '#ef4444'} />
                                            ))}
                                        </Pie>
                                        <Tooltip 
                                            contentStyle={{ backgroundColor: '#1c1c1e', borderColor: 'rgba(255,255,255,0.1)' }} 
                                            itemStyle={{ color: '#fff' }}
                                        />
                                        <Legend verticalAlign="bottom" height={36} iconSize={8} wrapperStyle={{ fontSize: '10px' }}/>
                                    </PieChart>
                                ) : (
                                    <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs text-center px-4">
                                        <AlertTriangle size={32} className="opacity-20 mb-2" />
                                        未从搜索结果中发现{brand}，<br/>无法计算声量份额
                                    </div>
                                )}
                            </ResponsiveContainer>
                        </div>
                     )}
                </div>
            </div>

            {/* Middle Row: Simulation-Status & Interactive Process [Integrated] */}
            <div className="flex flex-col gap-4">
                 {/* 1. Status Display Panel */}
                 <div className="bg-[#1c1c1e]/60 rounded-2xl border border-white/5 p-6 relative overflow-hidden h-32 shrink-0 flex items-center justify-between">
                     <div>
                         <h3 className="text-lg font-bold text-white mb-1">分析状态</h3>
                         {analyzing ? (
                             <div className="text-[#0a84ff] font-mono text-sm flex items-center gap-2">
                                 <Cpu size={14} className="animate-pulse"/> 
                                 {progressText} {progress}%
                             </div>
                         ) : result ? (
                             <div className="text-emerald-400 font-mono text-sm flex items-center gap-2">
                                 <CheckCircle2 size={14}/> 
                                 分析已完成
                             </div>
                         ) : (
                             <div className="text-slate-500 font-mono text-sm flex items-center gap-2">
                                 <Terminal size={14}/> 
                                 等待开始
                             </div>
                         )}
                     </div>

                     {/* Progress Bar Background */}
                     {analyzing && (
                         <div className="absolute bottom-0 left-0 h-1 bg-[#0a84ff] transition-all duration-100 ease-linear" style={{ width: `${progress}%` }}></div>
                     )}
                     
                     {/* Quick Metrics */}
                     {result && (
                         <div className="flex gap-8 mr-4 animate-fade-in-up">
                             <div className="text-center">
                                 <div className="text-[10px] text-slate-500 uppercase tracking-widest">综合排名预测</div>
                                 <div className="text-2xl font-bold text-white">
                                     {result.bestRank > 0 
                                        ? (result.bestRank <= 3 ? '前三 (Top 3)' : `第 ${result.bestRank} 名`) 
                                        : (result.pieData[0].value > 0 ? '已收录 (Visible)' : '未上榜')
                                     }
                                 </div>
                             </div>
                             <div className="text-center">
                                 <div className="text-[10px] text-slate-500 uppercase tracking-widest">品牌可见性</div>
                                 <div className="text-2xl font-bold text-[#0a84ff]">
                                     {result.pieData[0].value > 0
                                        ? ((result.pieData[0].value / (result.pieData[0].value + result.pieData[1].value)) * 100).toFixed(0) + "%"
                                        : '-'
                                     }
                                 </div>
                             </div>
                             <div className="text-center">
                                 <div className="text-[10px] text-slate-500 uppercase tracking-widest">情感倾向</div>
                                 <div className="text-2xl font-bold text-emerald-400">
                                     {result.pieData[0].value > 0
                                        ? (result.sov.find((s: any) => s.subject === '情感倾向')?.A > 50 ? '正面 (Positive)' : ((result as any).sov.find((s: any) => s.subject === '情感倾向')?.A < 50 && (result as any).sov.find((s: any) => s.subject === '情感倾向')?.A > 0 ? '负面' : '中性 (Neutral)'))
                                        : '-'
                                     }
                                 </div>
                             </div>
                         </div>
                     )}
                 </div>

                 {/* 2. Simulation Results Body / Process View */}
                 {(result || analyzing) && (
                     <div className="bg-[#1c1c1e]/60 rounded-2xl border border-white/5 overflow-hidden flex flex-col relative min-h-[300px]">
                        
                            <div className="flex-1 flex flex-col animate-fade-in">
                                <div className="p-8 flex items-start gap-4">
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#0a84ff] to-[#bf5af2] flex items-center justify-center shadow-apple shrink-0">
                                        <Cpu size={20} className="text-white"/>
                                    </div>
                                    <div className="flex-1 space-y-2">
                                        <div className="flex items-center justify-between mb-1">
                                            <div className="text-sm text-slate-400 font-bold">
                                                {selectedModel === 'auto' ? '智能优选模型 (Auto-Mode)' : selectedModel} 
                                                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded bg-white/10 ml-2">Live Engine</span>
                                            </div>

                                            {result && result.queryAnalysis && result.queryAnalysis[0] && !result.queryAnalysis[0].mentioned && (
                                                <button 
                                                    onClick={() => router.push(`/optimize?q=${encodeURIComponent(result.queryAnalysis[0].question)}&brand=${encodeURIComponent(brand)}`)}
                                                    className="flex items-center gap-2 text-xs font-bold text-white bg-[#0071e3] hover:bg-[#0077ed] hover:scale-105 active:scale-95 transition-all px-4 py-2 rounded-lg shadow-apple animate-pulse border border-[#0a84ff]"
                                                >
                                                    <TrendingUp size={14} className="fill-current" /> 
                                                    立即优化 (Optimize Now)
                                                </button>
                                            )}
                                        </div>
                                        <div className="text-base text-slate-200 leading-relaxed p-4 bg-white/[0.03] rounded-xl border border-white/5 min-h-[100px]">
                                            {analyzing ? (
                                                <div className="whitespace-pre-wrap font-mono text-sm text-[#7dc1ff]/80">
                                                    {streamingSnippet || "Initializing connection to neural network..."}
                                                    <span className="inline-block w-2 h-4 ml-1 align-middle bg-[#0a84ff]/50 animate-pulse"/>
                                                </div>
                                            ) : result && result.queryAnalysis[0] ? (
                                                <TypewriterEffect text={result.queryAnalysis[0].snippet_raw || result.queryAnalysis[0].snippet} />
                                            ) : (
                                                <p className="text-slate-500 italic">未返回有效数据 (No data returned).</p>
                                            )}
                                        </div>
                                        {result && result.queryAnalysis && result.queryAnalysis[0] && (
                                            <div className="flex items-center gap-2 mt-3 flex-wrap">
                                                <div className="flex items-center gap-2 bg-black/20 pl-2 pr-1 py-1 rounded border border-white/5 group">
                                                    <span className="text-xs text-slate-500">提问: {result.queryAnalysis[0].question}</span>
                                                    <button 
                                                        onClick={() => handleCopyQuestion(result.queryAnalysis[0].question, 0)}
                                                        className="p-1 hover:bg-white/10 rounded text-slate-400 transition-colors"
                                                        title="复制问题"
                                                    >
                                                        {copiedId === 0 ? <Check size={12} className="text-emerald-400"/> : <Copy size={12} />}
                                                    </button>
                                                </div>
                                                
                                                {result.queryAnalysis[0].mentioned && (
                                                    <span className="text-xs text-slate-500 bg-black/20 px-2 py-1 rounded border border-white/5">
                                                        排名: {result.queryAnalysis[0].rank > 0 ? `Top ${result.queryAnalysis[0].rank}` : '已上榜'}
                                                    </span>
                                                )}
                                                
                                                <span className="text-xs text-slate-500 bg-black/20 px-2 py-1 rounded border border-white/5">置信度: High</span>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {result && (
                                <div className="flex-1 bg-black/20 p-6 border-t border-white/5">
                                     <h4 className="text-xs font-bold text-slate-400 uppercase mb-4 flex items-center gap-2">
                                        <TrendingUp size={14}/> 关键指标影响预测
                                     </h4>
                                     <div className="grid grid-cols-2 gap-4">
                                         <div className="bg-white/5 p-4 rounded border border-white/5">
                                             <div className="flex justify-between mb-2">
                                                 <span className="text-sm text-slate-300">GEO 推荐概率</span>
                                                 <span className="text-emerald-400 font-bold">
                                                     {result.bestRank > 0 ? 'High' : '-'}
                                                 </span>
                                             </div>
                                             <div className="w-full bg-slate-700 h-1.5 rounded-full overflow-hidden">
                                                 <div className={`h-full ${result.bestRank > 0 ? 'bg-emerald-500 w-[85%]' : 'bg-slate-700 w-0'}`}></div>
                                             </div>
                                             <p className="text-xs text-slate-500 mt-2">
                                                 {result.bestRank > 0 
                                                    ? '内容结构符合 GEO 收录标准。' 
                                                    : '品牌未上榜，无法评估推荐概率。'}
                                             </p>
                                         </div>
                                         <div className="bg-white/5 p-4 rounded border border-white/5">
                                             <div className="flex justify-between mb-2">
                                                 <span className="text-sm text-slate-300">品牌关联度</span>
                                                 <span className="text-blue-400 font-bold">
                                                     {result.bestRank > 0 ? 'Strong' : '-'}
                                                 </span>
                                             </div>
                                             <div className="w-full bg-slate-700 h-1.5 rounded-full overflow-hidden">
                                                 <div className={`h-full ${result.bestRank > 0 ? 'bg-blue-500 w-[90%]' : 'bg-slate-700 w-0'}`}></div>
                                             </div>
                                             <p className="text-xs text-slate-500 mt-2">
                                                 {result.bestRank > 0 
                                                    ? '核心关键词与品牌形成了强绑定。' 
                                                    : '品牌未上榜，无法评估关联强度。'}
                                             </p>
                                         </div>
                                     </div>
                                </div>
                                )}
                            </div>
                     </div>
                 )}
            </div>

            {/* Bottom Row: Insights */}
            <div className="bg-[#1c1c1e]/60 rounded-2xl border border-white/5 p-6 shrink-0 mb-6 mt-4">
                <h3 className="text-sm font-bold text-slate-300 mb-4 flex items-center gap-2">
                    <ShieldCheck size={16} className="text-emerald-500" />
                    Arthur 战略备忘录 (Strategic Insights)
                </h3>
                 {!result ? (
                    <div className="text-xs text-slate-500">暂无数据。</div>
                 ) : (
                    <ul className="space-y-3">
                        {result.insights.map((insight: string, i: number) => (
                             <li key={i} className="text-sm text-slate-300 leading-relaxed bg-black/20 p-3 rounded border-l-2 border-[#0a84ff]">
                                 {insight}
                             </li>
                        ))}
                    </ul>
                 )}
            </div>
        </div>
      </div>
    </div>
  );
}
