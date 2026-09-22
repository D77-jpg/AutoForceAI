"use client";
import { useRouter } from 'next/navigation';
import { useState, useEffect, useMemo } from 'react';
import api from '../../lib/api';
import { 
  Search, Activity, BarChart3, Clock, ArrowUpRight, Zap, Target, 
  AlertTriangle, CheckCircle2, TrendingUp, ShieldCheck, FileText,
  MousePointer2, X, Play
} from 'lucide-react';
import { useToast } from '../../contexts/ToastContext';
import { useGlobalState } from '../../contexts/GlobalStateContext';
import Link from 'next/link';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, 
  ResponsiveContainer, AreaChart, Area, Legend 
} from 'recharts';

interface Task {
  id: number;
  target_brand: string;
  query: string;
  engine_name: string;
  is_mentioned: boolean;
  rank_position: number;
  sentiment_score: number;
  created_at: string;
  reasoning: string;
  suggestions?: string[];
  status?: string;
}

export default function GEODashboard() {
  const { showToast } = useToast();
  // Sync with Diagnosis State
  const { 
      brand, setBrand, query, setQuery,
      setDiagBrand, setDiagUserQueries 
  } = useGlobalState();
  
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [engine, setEngine] = useState('perplexity');
  const [watches, setWatches] = useState<any[]>([]);
  const [intervalHours, setIntervalHours] = useState(24);
  const router = useRouter();

  // Metrics Calculation
  const metrics = useMemo(() => {
    if (tasks.length === 0) return null;

    // Fix Issue 1: Case-insensitive filtering & Search in Query too
    // FIX: Trim whitespace to avoid "Brand " mismatching "Brand"
    const lowerBrand = brand?.trim().toLowerCase() || "";
    const brandTasks = brand 
        ? tasks.filter(t => {
            const b = (t.target_brand || "").toLowerCase();
            const q = (t.query || "").toLowerCase();
            return b.includes(lowerBrand) || q.includes(lowerBrand);
        })
        : tasks;
        
    const totalRaw = brandTasks.length;

    // Helper for safe boolean check (handles number 1, string '1', boolean true, string 'true')
    const isMentioned = (t: Task) => {
       // Universally convert to string for checking
       const val = String(t.is_mentioned).toLowerCase();
       if (val === 'true' || val === '1' || val === 'yes') return true;
       
       // Fallback: If it has a valid positive rank, it counts as mentioned
       const rank = Number(t.rank_position);
       if (!isNaN(rank) && rank > 0) return true;

       return false;
    };

    // Correct Logic V4: 
    // "Success" = Mentioned. (Ranked OR Unranked but Mentioned)
    const isSuccess = (t: Task) => isMentioned(t);

    // Deduplicate brandTasks to get unique scenarios (latest status per query)
    // Keys are (Brand + Query)
    const seen = new Set<string>();
    const uniqueBrandTasks = [];
    for (const task of brandTasks) {
        const key = `${task.target_brand?.trim().toLowerCase()}|${task.query?.trim().toLowerCase()}`;
        if (!seen.has(key)) {
            seen.add(key);
            uniqueBrandTasks.push(task);
        }
    }

    const uniqueTotal = uniqueBrandTasks.length;

    // Recalculate based on strict success
    const successTasks = uniqueBrandTasks.filter(t => isSuccess(t));
    const failedTasks = uniqueBrandTasks.filter(t => !isSuccess(t));
    
    // Ensure mentionedCount logic matches successTasks length for consistency
    const mentionedCount = successTasks.length;

    const avgSentiment = uniqueTotal > 0 
        ? uniqueBrandTasks.reduce((acc, curr) => acc + (curr.sentiment_score || 0), 0) / uniqueTotal
        : 0;
        
    const visibilityScore = uniqueTotal > 0 
        ? ((mentionedCount / uniqueTotal) * 0.6 + (avgSentiment / 10) * 0.4) * 100
        : 0; 
    
    // Debugging (Enabled by User Request)
    console.log("GEO Debug:", { brand, lowerBrand, total: uniqueTotal, success: successTasks.length, failed: failedTasks.length });

    return {
      total: uniqueTotal,
      mentionedCount,
      visibilityRate: uniqueTotal > 0 ? (mentionedCount / uniqueTotal) * 100 : 0,
      avgSentiment: avgSentiment.toFixed(1),
      visibilityScore: visibilityScore.toFixed(0),
      failedTasks,
      successTasks
    };
  }, [tasks, brand]);

  // Chart Data Preparation
  const chartData = useMemo(() => {
    if (!tasks.length) return [];
    // Group by date (MM-DD)
    const grouped = tasks.reduce((acc: any, task) => {
        const date = new Date(task.created_at).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
        if (!acc[date]) acc[date] = { date, total: 0, mentioned: 0, sentimentSum: 0 };
        acc[date].total += 1;
        if (task.is_mentioned) acc[date].mentioned += 1;
        acc[date].sentimentSum += (task.sentiment_score || 0);
        return acc;
    }, {});

    return Object.values(grouped).map((item: any) => ({
        date: item.date,
        visibility: ((item.mentioned / item.total) * 100).toFixed(0),
        sentiment: (item.sentimentSum / item.total).toFixed(1)
    })).slice(-7); // Last 7 days/points
  }, [tasks]);

  const fetchHistory = async () => {
    try {
      const res = await api.get(`/api/v1/branding/tasks?limit=50`); 
      setTasks(res.data); 
    } catch (err) {
      console.error("加载历史失败", err);
    }
    try {
      const w = await api.get(`/api/v1/branding/watches`);
      setWatches(w.data.items || []);
    } catch (err) {
      // unauthenticated pages may skip
    }
  };

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleStartTask = async () => {
    if (!brand || !query) return showToast("请填写品牌和查询词", "error");
    
    // Sync to Diagnosis Page State
    setDiagBrand(brand);
    setDiagUserQueries(query);
    setLoading(true);
    try {
      await api.post('/api/v1/branding/analyze', {
        target_brand: brand,
        query,
        engine_name: engine,
        language: /[A-Za-z]/.test(query) ? 'en' : 'zh',
      });
      showToast("监测任务已提交（Perplexity / 选定引擎）", "success");
      fetchHistory();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "提交失败，改为打开诊断页", "error");
      router.push('/diagnosis?auto=true');
      return;
    } finally {
      setLoading(false);
    }
  };

  const handleSchedule = async () => {
    if (!brand || !query) return showToast("请填写品牌和查询词", "error");
    try {
      await api.post('/api/v1/branding/watches', {
        target_brand: brand,
        query,
        engine_name: engine,
        language: 'en',
        interval_hours: intervalHours,
      });
      showToast(`已加入定时监测，每 ${intervalHours} 小时查询一次`, "success");
      fetchHistory();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "创建监测失败", "error");
    }
  };

  const handleDeleteTask = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    // Optimistic Update immediately to prevent flickering
    setTasks(prev => prev.filter(t => t.id !== id));
    
    try {
        await api.delete(`/api/v1/branding/tasks/${id}`);
        showToast("记录已删除", "success");
    } catch (err) {
        // Only revert if we are sure it failed.
        // But for "Deleted card appears again", usually means server didn't delete. 
        // We now implemented the DELETE endpoint to fix this.
        console.error("Delete failed", err);
    }
  };

  const handleCardClick = (task: Task) => {
      setBrand(task.target_brand);
      setQuery(task.query);
      // Fix Issue 3: Pass context to Diagnosis
      setDiagBrand(task.target_brand);
      setDiagUserQueries(task.query);
      router.push('/diagnosis');
  };

  return (
    <div className="space-y-6 animate-slide-in-right pt-4 h-full overflow-y-auto px-1">
      
      {/* 1. Practical Action Header */}
      <div className="flex flex-col md:flex-row gap-6 items-stretch">
        {/* Left: Quick Launch */}
        <div className="flex-[2] bg-[#1c1c1e] border border-white/8 rounded-[24px] p-6 flex flex-col justify-between relative overflow-hidden">
             <div className="relative z-10">
                <h2 className="text-[22px] font-semibold tracking-tight text-white mb-2 flex items-center gap-2">
                   <Zap className="text-[#ffd60a] fill-current" size={20}/> 
                   GEO 优化引擎
                </h2>
                <p className="text-[15px] text-[#86868b] mb-6 max-w-lg">
                   输入品牌与英文查询词（如 best hydraulic pump supplier China），定时查询 Perplexity 等生成式引擎，记录品牌是否被提及。
                </p>
                
                <div className="flex gap-2 w-full max-w-3xl bg-black/40 p-2 rounded-full border border-white/10">
                    <input 
                      type="text" 
                      value={brand}
                      onChange={(e) => setBrand(e.target.value)}
                      placeholder="品牌名称 (Brand)"
                      className="w-1/4 bg-transparent border-r border-white/10 text-white placeholder-slate-500 focus:outline-none px-4 text-sm font-medium"
                    />
                    {brand && (
                       <button onClick={() => setBrand('')} className="absolute left-[22%] top-3 text-slate-500 hover:text-white" title="Clear Filter">
                          <X size={12} />
                       </button>
                    )}
                    <input 
                      type="text" 
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder='英文查询词 e.g. best hydraulic pump supplier China'
                      className="flex-1 bg-transparent text-white placeholder-slate-500 focus:outline-none px-4 text-sm"
                    />
                    <select
                      value={engine}
                      onChange={(e) => setEngine(e.target.value)}
                      className="bg-transparent text-xs text-slate-300 border-l border-white/10 px-2 outline-none"
                    >
                      <option value="perplexity">Perplexity</option>
                      <option value="qwen">Qwen</option>
                      <option value="zhipu">Zhipu</option>
                    </select>
                    <button 
                      onClick={handleStartTask}
                      disabled={loading}
                      className="bg-[#0071e3] hover:bg-[#0077ed] text-white px-4 py-2 rounded-full text-sm font-medium transition-all shadow-apple disabled:opacity-50"
                    >
                      {loading ? <span className="animate-pulse">Running...</span> : "立即监测"}
                    </button>
                    <button
                      onClick={handleSchedule}
                      className="bg-white/10 hover:bg-white/20 text-white px-3 py-2 rounded-lg text-xs"
                    >
                      定时
                    </button>
                </div>
                <div className="flex items-center gap-2 mt-2 text-[11px] text-slate-500">
                  <span>间隔</span>
                  <input
                    type="number"
                    min={1}
                    max={168}
                    value={intervalHours}
                    onChange={(e) => setIntervalHours(Number(e.target.value) || 24)}
                    className="w-16 bg-black/30 border border-white/10 rounded px-1 py-0.5"
                  />
                  <span>小时 · 历史趋势见下方卡片</span>
                  {watches.length > 0 && <span className="text-[#64d2ff]">已启用 {watches.filter(w => w.enabled).length} 条监测</span>}
                </div>
             </div>
             
             {/* Background Decoration */}
             <div className="absolute right-0 bottom-0 w-64 h-64 bg-[#0a84ff]/10 rounded-full blur-3xl -z-0"></div>
        </div>

        {/* Right: Real-time Score */}
        <div className="flex-1 glass-card p-6 flex flex-col justify-center items-center text-center relative overflow-hidden bg-[#1c1c1e]/80">
            {metrics ? (
                <>
                    <h3 className="text-sm font-medium text-slate-400 uppercase tracking-widest mb-1">GEO 健康度评分</h3>
                    <div className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-t from-emerald-400 to-white mb-2">
                        {metrics.visibilityScore}
                    </div>
                    <div className="flex gap-4 text-xs font-mono text-slate-500">
                        <span className="flex items-center gap-1"><Target size={12}/> 提及率 {metrics.visibilityRate.toFixed(0)}%</span>
                        <span className="flex items-center gap-1"><ShieldCheck size={12}/> 情感 {metrics.avgSentiment}</span>
                    </div>
                </>
            ) : (
                <div className="text-slate-500 text-sm">暂无分析数据</div>
            )}
        </div>
      </div>

      {/* 2. Priority & Opportunities Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Col 1: Missed Opportunities (High Priority) */}
          <div className="glass-card flex flex-col border-l-4 border-l-red-500/50 h-[400px]">
              <div className="p-4 border-b border-white/5 flex justify-between items-center bg-red-500/5">
                  <h3 className="font-bold text-slate-200 flex items-center gap-2">
                      <AlertTriangle size={18} className="text-red-400"/>
                      未收录品牌 (Missed)
                  </h3>
                  <span className="text-xs bg-red-500/20 text-red-300 px-2 py-0.5 rounded-full">
                      {metrics?.failedTasks.length || 0} items
                  </span>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar">
                  {metrics?.failedTasks.map(task => (
                      <div 
                        key={task.id} 
                        onClick={() => handleCardClick(task)}
                        className="p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-colors group relative cursor-pointer"
                      >
                          <button 
                             onClick={(e) => handleDeleteTask(e, task.id)}
                             className="absolute top-2 right-2 p-1 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all z-10"
                          >
                             <X size={14} />
                          </button>

                          <div className="flex justify-between items-start mb-1">
                             <h4 className="text-lg font-bold text-slate-200">{task.target_brand}</h4>
                          </div>
                          
                          <p className="text-sm text-slate-400 font-medium mb-3 line-clamp-2">{task.query}</p>

                          <div className="flex items-center gap-2 mt-auto">
                             <div className="text-[10px] text-slate-500 bg-black/20 px-2 py-0.5 rounded border border-white/5 flex items-center gap-1">
                                 <Zap size={10} className="text-[#0a84ff]"/>
                                 {task.engine_name || 'AI Engine'}
                             </div>
                              <button 
                                className="ml-auto text-[10px] text-[#0a84ff] flex items-center gap-1 hover:text-[#64d2ff] transition-colors"
                              >
                                  Diagnose <Play size={10} />
                              </button>
                          </div>
                      </div>
                  ))}
                  {(!metrics || metrics.failedTasks.length === 0) && (
                      <div className="h-full flex flex-col items-center justify-center text-slate-600">
                          <CheckCircle2 size={32} className="mb-2 opacity-20"/>
                          <p className="text-xs">太棒了！暂无未收录的关键词</p>
                      </div>
                  )}
              </div>
          </div>

          {/* Col 2: Optimization Success (References) */}
          <div className="glass-card flex flex-col border-l-4 border-l-emerald-500/50 h-[400px]">
              <div className="p-4 border-b border-white/5 flex justify-between items-center bg-emerald-500/5">
                  <h3 className="font-bold text-slate-200 flex items-center gap-2">
                      <CheckCircle2 size={18} className="text-emerald-400"/>
                      已收录品牌 (Visible)
                  </h3>
                  <span className="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full">
                      {metrics?.successTasks.length || 0} items
                  </span>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar">
                   {metrics?.successTasks.map(task => (
                      <div 
                        key={task.id} 
                        onClick={() => handleCardClick(task)}
                        className="p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-colors group relative cursor-pointer"
                      >
                          <button 
                             onClick={(e) => handleDeleteTask(e, task.id)}
                             className="absolute top-2 right-2 p-1 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all z-10"
                          >
                             <X size={14} />
                          </button>

                          <div className="flex justify-between items-start mb-1">
                             <h4 className="text-lg font-bold text-slate-200">{task.target_brand}</h4>
                             {task.rank_position && task.rank_position > 0 ? (
                                <span className="text-sm font-black text-emerald-400">#{task.rank_position}</span>
                             ) : (
                                <span className="text-xs font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">收录</span>
                             )}
                          </div>
                          
                          <p className="text-sm text-slate-400 font-medium mb-3 line-clamp-2">{task.query}</p>

                          <div className="flex items-center gap-2 mt-auto">
                              <div className="text-[10px] text-slate-500 bg-black/20 px-2 py-0.5 rounded border border-white/5 flex items-center gap-1">
                                 <Zap size={10} className="text-[#0a84ff]"/>
                                 {task.engine_name || 'AI Engine'}
                             </div>
                             <div className="flex items-center gap-1 ml-auto">
                                <Activity size={10} className="text-emerald-500"/>
                                <span className="text-[10px] text-emerald-400">{task.sentiment_score}分</span>
                             </div>
                          </div>
                      </div>
                  ))}
                  {(!metrics || metrics.successTasks.length === 0) && (
                      <div className="h-full flex flex-col items-center justify-center text-slate-600">
                          <CheckCircle2 size={32} className="mb-2 opacity-20"/>
                          <p className="text-xs">暂无已收录的记录</p>
                      </div>
                  )}
              </div>
          </div>

          {/* Col 3: Trend & Insights */}
          <div className="glass-card flex flex-col h-[400px]">
              <div className="p-4 border-b border-white/5">
                  <h3 className="font-bold text-slate-200 flex items-center gap-2">
                      <TrendingUp size={18} className="text-blue-400"/>
                      可见性趋势 (Tractions)
                  </h3>
              </div>
              <div className="flex-1 p-4">
                  <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData}>
                          <defs>
                              <linearGradient id="colorVis" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                              </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} vertical={false}/>
                          <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false}/>
                          <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} domain={[0, 100]}/>
                          <RechartsTooltip 
                              contentStyle={{ backgroundColor: '#1c1c1e', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: '12px' }}
                              itemStyle={{ color: '#e2e8f0' }}
                          />
                          <Area type="monotone" dataKey="visibility" stroke="#6366f1" fillOpacity={1} fill="url(#colorVis)" strokeWidth={2} name="可见性 %"/>
                      </AreaChart>
                  </ResponsiveContainer>
              </div>
              {/* Recommendations Footer */}
              <div className="p-4 border-t border-white/5 bg-[#1c1c1e]/50">
                  <div className="flex items-start gap-3">
                      <FileText size={16} className="text-[#0a84ff] mt-1"/>
                      <div>
                          <h4 className="text-xs font-bold text-slate-300">优化建议 (AI Insights)</h4>
                          <p className="text-[10px] text-slate-500 mt-1 leading-relaxed">
                              {metrics?.failedTasks.length ? 
                              `检测到 ${metrics.failedTasks.length} 个查询词未收录您的品牌。建议针对未命中查询词增加结构化数据 (Schema.org) 并优化官网 FAQ 模块。` :
                              "当前品牌 GEO 表现优异，建议持续监控竞品动态，保持内容新鲜度。"}
                          </p>
                      </div>
                  </div>
              </div>
          </div>

      </div>
    </div>
  );
}
// Remove old StatCard to avoid duplication errors if unused, or keep it inside if preferred. 
// I completely rewrote the component so old logic is gone.



