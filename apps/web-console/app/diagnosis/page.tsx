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
            __html: displayedText.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white bg-accent/15 px-1 rounded">$1</strong>').replace(/\n/g, '<br/>') 
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

  const COLORS = ["rgb(var(--ui-success))", "rgb(var(--ui-danger))", "rgb(var(--ui-text-tertiary))"];

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
    <div className="min-h-screen bg-bg text-text font-sans p-6 overflow-y-auto w-full custom-scrollbar">
      
      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-60px)]">
        
        {/* Left: Configuration (3 Cols) */}
        <div className="col-span-3 bg-surface/60 rounded-2xl border border-separator flex flex-col h-full overflow-hidden">
            {/* Header */}
            <div className="p-5 border-b border-separator bg-text/5 shrink-0">
                 <h3 className="text-sm font-bold text-text flex items-center gap-2">
                    <Search size={16} className="text-accent" />
                    诊断目标配置
                </h3>
            </div>

            {/* Form Content */}
            <div className="p-5 overflow-y-auto custom-scrollbar flex-1 space-y-4">
                <div>
                     <label className="block text-[10px] uppercase tracking-wider text-accent font-bold mb-1.5">您的品牌 (Your Brand)</label>
                     <div className="relative group">
                        <input 
                            value={brand}
                            onChange={e => setBrand(e.target.value)}
                            className="w-full bg-bg border border-separator rounded-lg px-3 py-2.5 text-sm text-white focus:border-accent outline-none transition-all group-hover:border-separator"
                            placeholder="输入您的品牌名称"
                        />
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary">
                             <ShieldCheck size={14} />
                        </div>
                     </div>
                </div>

                <div className="relative py-1 flex items-center justify-center">
                    <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-text/10 to-transparent"></div>
                    <span className="relative bg-surface px-2 text-[10px] text-text-secondary font-mono">VS</span>
                </div>

                <div>
                    <label className="block text-[10px] uppercase tracking-wider text-text-secondary font-bold mb-1.5">竞品品牌 (Competitor)</label>
                    <input 
                        placeholder="例如: 特斯拉 (选填)"
                        value={competitor}
                        onChange={e => setCompetitor(e.target.value)}
                        className="w-full bg-bg border border-separator rounded-lg px-3 py-2.5 text-sm text-white focus:border-accent outline-none transition-all placeholder:text-text-tertiary"
                    />
                </div>

                <div>
                    <label className="block text-[10px] uppercase tracking-wider text-text-secondary font-bold mb-1.5">
                        用户拟提问 (Test Queries)
                        <span className="ml-2 text-[9px] text-text-tertiary bg-surface-2 px-1 py-0.5 rounded">一行一个</span>
                    </label>
                    <textarea
                        value={userQueries}
                        onChange={(e) => setUserQueries(e.target.value)}
                        className="w-full h-32 bg-bg border border-separator rounded-lg px-3 py-2 text-sm text-text outline-none resize-none focus:border-accent custom-scrollbar leading-relaxed"
                        placeholder="输入用户可能会问模型的问题..."
                    />
                </div>

                <div>
                    <label className="block text-[10px] uppercase tracking-wider text-text-secondary font-bold mb-1.5">搜索范围 (Search Scope)</label>
                    <div className="relative">
                        <select 
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                            className="w-full bg-bg border border-separator rounded-lg px-3 py-2.5 text-sm text-text outline-none appearance-none cursor-pointer hover:border-separator transition-all"
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
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-text-secondary">
                            <ArrowRightCircle size={14} className="rotate-90"/>
                        </div>
                    </div>
                </div>
            </div>

            {/* Footer Action */}
            <div className="p-5 border-t border-separator bg-surface/70 shrink-0">
                <button 
                    onClick={handleAnalyze}
                    disabled={analyzing}
                    className={`w-full py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${
                        analyzing 
                            ? 'bg-surface-2 text-text-secondary border border-separator cursor-not-allowed' 
                            : 'bg-gradient-to-r from-accent to-accent hover:from-accent hover:to-accent text-white shadow-card active:scale-[0.98]'
                    }`}
                >
                    {analyzing ? (
                        <>
                            <div className="w-4 h-4 border-2 border-separator border-t-accent rounded-full animate-spin"></div>
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
                <div className="flex-[2] bg-surface/60 rounded-2xl border border-separator p-6 relative overflow-hidden flex flex-col">
                    <div className="flex justify-between items-start mb-2 z-10 relative">
                        <h3 className="text-sm font-bold text-text">品牌维度分析 (Brand Dimensions)</h3>
                        <div className="flex items-center gap-2 bg-bg/40 rounded-full px-1 pl-3 py-1 border border-separator">
                            <span className="text-[10px] text-accent font-mono flex items-center gap-1">
                                <BrainCircuit size={10} />
                                {getModelDisplayName()}
                            </span>
                            <button 
                                onClick={handleTestModel}
                                className="bg-accent hover:bg-accent-hover text-white p-1 rounded-full transition-colors"
                                title="测试此模型 (Test Model)"
                            >
                                <ArrowRightCircle size={12} />
                            </button>
                        </div>
                    </div>

                        <div className="flex w-full h-full relative">
                            {!result && (
                                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-10">
                                    <div className="bg-surface/90 backdrop-blur-sm px-4 py-2 rounded-full border border-separator"> 
                                        <p className="text-text-secondary font-bold text-xs">等待分析数据 (Waiting)</p>
                                    </div>
                                </div>
                            )}
                            <ResponsiveContainer width="100%" height="100%">
                                {result && result.pieData[0].value > 0 ? (
                                    <RadarChart cx="50%" cy="50%" outerRadius="70%" data={result ? result.sov : defaultRadarData}>
                                        <PolarGrid stroke="rgb(var(--ui-text-tertiary))" />
                                        <PolarAngleAxis dataKey="subject" tick={{ fill: "rgb(var(--ui-text-secondary))", fontSize: 10 }} />
                                        <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                                        <Radar 
                                            name={brand || "我的品牌"} 
                                            dataKey="A" 
                                            stroke={result && result.bestRank > 0 ? "rgb(var(--ui-accent))" : "rgb(var(--ui-accent) / 0.6)"} 
                                            strokeWidth={2} 
                                            fill={result && result.bestRank > 0 ? "rgb(var(--ui-accent))" : "rgb(var(--ui-accent) / 0.6)"} 
                                            fillOpacity={0.3} 
                                        />
                                        {competitor && (
                                            <Radar name={competitor} dataKey="B" stroke={result ? "rgb(var(--ui-danger))" : "rgb(var(--ui-surface-2))"} strokeWidth={2} fill={result ? "rgb(var(--ui-danger))" : "rgb(var(--ui-surface-2))"} fillOpacity={0.3} />
                                        )}
                                        <Legend />
                                        <Tooltip 
                                            contentStyle={{ backgroundColor: 'rgb(var(--ui-surface))', borderColor: 'rgb(var(--ui-separator) / var(--ui-separator-alpha))' }}
                                            itemStyle={{ color: 'rgb(var(--ui-text))' }}
                                        />
                                    </RadarChart>
                                ) : (
                                    <div className="flex flex-col items-center justify-center h-full text-text-secondary text-xs">
                                        <Map size={32} className="opacity-20 mb-2" />
                                        {result ? '未上榜，相关指标无法计算' : '暂无数据'}
                                    </div>
                                )}
                            </ResponsiveContainer>
                        </div>
                    </div>

                {/* Pie Chart (1/3) */}
                <div className="flex-1 bg-surface/60 rounded-2xl border border-separator p-6 flex flex-col relative overflow-hidden">
                     <div className="flex justify-between items-center mb-2 z-10 relative">
                        <h3 className="text-sm font-bold text-text">
                            {result ? '品牌提及率' : '声量份额'}
                        </h3>
                        <div className="text-[10px] bg-text/5 rounded px-2 py-0.5 text-text-secondary font-mono">
                             {getModelDisplayName()}
                        </div>
                     </div>
                     
                     {analyzing ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-surface/80 backdrop-blur-sm z-20 space-y-4">
                            <div className="relative w-20 h-20">
                               <div className="absolute inset-0 rounded-full border-4 border-accent/20 border-t-accent animate-spin"></div>
                               <div className="absolute inset-4 rounded-full border-4 border-separator border-b-text/50 animate-spin-reverse"></div>
                            </div>
                            <div className="text-center space-y-1">
                                <p className="text-white text-xs font-bold">正在进行 AI 深度思考...</p>
                                <p className="text-text-secondary text-[10px] font-mono">实时获取搜索引擎数据中...</p>
                            </div>
                        </div>
                     ) : !result ? (
                         <div className="flex-1 flex items-center justify-center">
                             <div className="w-32 h-32 rounded-full border-4 border-separator border-t-slate-700 animate-spin opacity-50"></div>
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
                                                <Cell key={`cell-${index}`} fill={index === 0 ? "rgb(var(--ui-success))" : "rgb(var(--ui-danger))"} />
                                            ))}
                                        </Pie>
                                        <Tooltip 
                                            contentStyle={{ backgroundColor: 'rgb(var(--ui-surface))', borderColor: 'rgb(var(--ui-separator) / var(--ui-separator-alpha))' }} 
                                            itemStyle={{ color: '#fff' }}
                                        />
                                        <Legend verticalAlign="bottom" height={36} iconSize={8} wrapperStyle={{ fontSize: '10px' }}/>
                                    </PieChart>
                                ) : (
                                    <div className="flex flex-col items-center justify-center h-full text-text-secondary text-xs text-center px-4">
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
                 <div className="bg-surface/60 rounded-2xl border border-separator p-6 relative overflow-hidden h-32 shrink-0 flex items-center justify-between">
                     <div>
                         <h3 className="text-lg font-bold text-white mb-1">分析状态</h3>
                         {analyzing ? (
                             <div className="text-accent font-mono text-sm flex items-center gap-2">
                                 <Cpu size={14} className="animate-pulse"/> 
                                 {progressText} {progress}%
                             </div>
                         ) : result ? (
                             <div className="text-success font-mono text-sm flex items-center gap-2">
                                 <CheckCircle2 size={14}/> 
                                 分析已完成
                             </div>
                         ) : (
                             <div className="text-text-secondary font-mono text-sm flex items-center gap-2">
                                 <Terminal size={14}/> 
                                 等待开始
                             </div>
                         )}
                     </div>

                     {/* Progress Bar Background */}
                     {analyzing && (
                         <div className="absolute bottom-0 left-0 h-1 bg-accent transition-all duration-100 ease-linear" style={{ width: `${progress}%` }}></div>
                     )}
                     
                     {/* Quick Metrics */}
                     {result && (
                         <div className="flex gap-8 mr-4 animate-fade-in-up">
                             <div className="text-center">
                                 <div className="text-[10px] text-text-secondary uppercase tracking-widest">综合排名预测</div>
                                 <div className="text-2xl font-bold text-white">
                                     {result.bestRank > 0 
                                        ? (result.bestRank <= 3 ? '前三 (Top 3)' : `第 ${result.bestRank} 名`) 
                                        : (result.pieData[0].value > 0 ? '已收录 (Visible)' : '未上榜')
                                     }
                                 </div>
                             </div>
                             <div className="text-center">
                                 <div className="text-[10px] text-text-secondary uppercase tracking-widest">品牌可见性</div>
                                 <div className="text-2xl font-bold text-accent">
                                     {result.pieData[0].value > 0
                                        ? ((result.pieData[0].value / (result.pieData[0].value + result.pieData[1].value)) * 100).toFixed(0) + "%"
                                        : '-'
                                     }
                                 </div>
                             </div>
                             <div className="text-center">
                                 <div className="text-[10px] text-text-secondary uppercase tracking-widest">情感倾向</div>
                                 <div className="text-2xl font-bold text-success">
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
                     <div className="bg-surface/60 rounded-2xl border border-separator overflow-hidden flex flex-col relative min-h-[300px]">
                        
                            <div className="flex-1 flex flex-col animate-fade-in">
                                <div className="p-8 flex items-start gap-4">
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-accent to-accent-hover flex items-center justify-center shadow-card shrink-0">
                                        <Cpu size={20} className="text-white"/>
                                    </div>
                                    <div className="flex-1 space-y-2">
                                        <div className="flex items-center justify-between mb-1">
                                            <div className="text-sm text-text-secondary font-bold">
                                                {selectedModel === 'auto' ? '智能优选模型 (Auto-Mode)' : selectedModel} 
                                                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded bg-text/10 ml-2">Live Engine</span>
                                            </div>

                                            {result && result.queryAnalysis && result.queryAnalysis[0] && !result.queryAnalysis[0].mentioned && (
                                                <button 
                                                    onClick={() => router.push(`/optimize?q=${encodeURIComponent(result.queryAnalysis[0].question)}&brand=${encodeURIComponent(brand)}`)}
                                                    className="flex items-center gap-2 text-xs font-bold text-white bg-accent hover:bg-accent-hover hover:scale-105 active:scale-95 transition-all px-4 py-2 rounded-lg shadow-card animate-pulse border border-accent"
                                                >
                                                    <TrendingUp size={14} className="fill-current" /> 
                                                    立即优化 (Optimize Now)
                                                </button>
                                            )}
                                        </div>
                                        <div className="text-base text-text leading-relaxed p-4 bg-text/[0.03] rounded-xl border border-separator min-h-[100px]">
                                            {analyzing ? (
                                                <div className="whitespace-pre-wrap font-mono text-sm text-accent/80">
                                                    {streamingSnippet || "Initializing connection to neural network..."}
                                                    <span className="inline-block w-2 h-4 ml-1 align-middle bg-accent/50 animate-pulse"/>
                                                </div>
                                            ) : result && result.queryAnalysis[0] ? (
                                                <TypewriterEffect text={result.queryAnalysis[0].snippet_raw || result.queryAnalysis[0].snippet} />
                                            ) : (
                                                <p className="text-text-secondary italic">未返回有效数据 (No data returned).</p>
                                            )}
                                        </div>
                                        {result && result.queryAnalysis && result.queryAnalysis[0] && (
                                            <div className="flex items-center gap-2 mt-3 flex-wrap">
                                                <div className="flex items-center gap-2 bg-bg/20 pl-2 pr-1 py-1 rounded border border-separator group">
                                                    <span className="text-xs text-text-secondary">提问: {result.queryAnalysis[0].question}</span>
                                                    <button 
                                                        onClick={() => handleCopyQuestion(result.queryAnalysis[0].question, 0)}
                                                        className="p-1 hover:bg-text/10 rounded text-text-secondary transition-colors"
                                                        title="复制问题"
                                                    >
                                                        {copiedId === 0 ? <Check size={12} className="text-success"/> : <Copy size={12} />}
                                                    </button>
                                                </div>
                                                
                                                {result.queryAnalysis[0].mentioned && (
                                                    <span className="text-xs text-text-secondary bg-bg/20 px-2 py-1 rounded border border-separator">
                                                        排名: {result.queryAnalysis[0].rank > 0 ? `Top ${result.queryAnalysis[0].rank}` : '已上榜'}
                                                    </span>
                                                )}
                                                
                                                <span className="text-xs text-text-secondary bg-bg/20 px-2 py-1 rounded border border-separator">置信度: High</span>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {result && (
                                <div className="flex-1 bg-bg/20 p-6 border-t border-separator">
                                     <h4 className="text-xs font-bold text-text-secondary uppercase mb-4 flex items-center gap-2">
                                        <TrendingUp size={14}/> 关键指标影响预测
                                     </h4>
                                     <div className="grid grid-cols-2 gap-4">
                                         <div className="bg-text/5 p-4 rounded border border-separator">
                                             <div className="flex justify-between mb-2">
                                                 <span className="text-sm text-text">GEO 推荐概率</span>
                                                 <span className="text-success font-bold">
                                                     {result.bestRank > 0 ? 'High' : '-'}
                                                 </span>
                                             </div>
                                             <div className="w-full bg-surface-2 h-1.5 rounded-full overflow-hidden">
                                                 <div className={`h-full ${result.bestRank > 0 ? 'bg-success w-[85%]' : 'bg-surface-2 w-0'}`}></div>
                                             </div>
                                             <p className="text-xs text-text-secondary mt-2">
                                                 {result.bestRank > 0 
                                                    ? '内容结构符合 GEO 收录标准。' 
                                                    : '品牌未上榜，无法评估推荐概率。'}
                                             </p>
                                         </div>
                                         <div className="bg-text/5 p-4 rounded border border-separator">
                                             <div className="flex justify-between mb-2">
                                                 <span className="text-sm text-text">品牌关联度</span>
                                                 <span className="text-accent font-bold">
                                                     {result.bestRank > 0 ? 'Strong' : '-'}
                                                 </span>
                                             </div>
                                             <div className="w-full bg-surface-2 h-1.5 rounded-full overflow-hidden">
                                                 <div className={`h-full ${result.bestRank > 0 ? 'bg-accent w-[90%]' : 'bg-surface-2 w-0'}`}></div>
                                             </div>
                                             <p className="text-xs text-text-secondary mt-2">
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
            <div className="bg-surface/60 rounded-2xl border border-separator p-6 shrink-0 mb-6 mt-4">
                <h3 className="text-sm font-bold text-text mb-4 flex items-center gap-2">
                    <ShieldCheck size={16} className="text-success" />
                    Arthur 战略备忘录 (Strategic Insights)
                </h3>
                 {!result ? (
                    <div className="text-xs text-text-secondary">暂无数据。</div>
                 ) : (
                    <ul className="space-y-3">
                        {result.insights.map((insight: string, i: number) => (
                             <li key={i} className="text-sm text-text leading-relaxed bg-bg/20 p-3 rounded border-l-2 border-accent">
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
