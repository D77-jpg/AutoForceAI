"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { 
  Bot, 
  Send, 
  RefreshCw, 
  Sparkles, 
  Image as ImageIcon, 
  Hash, 
  Share2, 
  CheckCircle2, 
  Loader2,
  Smartphone,
  Globe,
  Edit3,
  X
} from 'lucide-react';
import api from '../../lib/api';
import { useGlobalState } from '../../contexts/GlobalStateContext';
import { useToast } from '../../contexts/ToastContext';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState } from '@/components/ui/empty-state';

// --- Types ---

interface LogStep {
  id: number;
  message: string;
  status: 'pending' | 'active' | 'completed';
  timestamp: string;
}

// --- Data ---

const PLATFORMS = [
  { id: 'linkedin', name: 'LinkedIn', icon: 'in', color: 'bg-accent' },
  { id: 'wordpress', name: 'WordPress', icon: '🅦', color: 'bg-accent' },
  { id: 'x', name: 'X / Twitter', icon: '𝕏', color: 'bg-surface-2' },
  { id: 'redbook', name: '小红书', icon: '📕', color: 'bg-danger' },
  { id: 'zhihu', name: '知乎', icon: '❓', color: 'bg-accent' },
  { id: 'baidu_baike', name: '百度词条', icon: '📖', color: 'bg-accent' },
];

const TONES = [
    { id: 'professional', name: '专业权威', emoji: '🧐' },
    { id: 'viral', name: '爆款网感', emoji: '🔥' },
    { id: 'empathetic', name: '情感共鸣', emoji: '🥰' },
    { id: 'controversial', name: '犀利观点', emoji: '⚡' },
];

// --- Components ---

const PhoneMockup = ({ 
    content, 
    isEditing, 
    onUpdate 
}: { 
    content: any; 
    isEditing: boolean; 
    onUpdate: (newContent: any) => void; 
}) => (
    <div className="relative mx-auto border-separator bg-surface-2 border-[8px] rounded-[30px] h-[600px] w-[300px] shadow-modal overflow-hidden flex flex-col">
        {/* Notch */}
        <div className="h-[24px] bg-surface-2 absolute top-0 left-[50%] translate-x-[-50%] w-[120px] rounded-b-[16px] z-20"></div>
        
        {/* Status Bar */}
        <div className="h-8 bg-bg w-full flex justify-between items-center px-6 text-[10px] text-text z-10">
            <span className="tabular-nums">9:41</span>
            <div className="flex gap-1 items-center">
                <span className="font-bold">5G</span>
                <div className="w-4 h-2.5 border border-separator rounded-[2px]" />
            </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 bg-bg text-text overflow-y-auto custom-scrollbar relative">
            {!content ? (
                <EmptyState
                    size="sm"
                    icon={Smartphone}
                    title="准备生成预览"
                    description="填写左侧战略简报并点击「立即生成」，这里将展示实机预览。"
                    className="h-full"
                />
            ) : (
                <div className="flex flex-col min-h-full">
                    {/* Image Area */}
                    <div className="h-64 bg-surface-2 relative group overflow-hidden shrink-0">
                        {content.image_url ? (
                            <img 
                                src={content.image_url} 
alt="生成的视觉图"
                                className="w-full h-full object-cover animate-in fade-in duration-700"
                            />
                        ) : (
                            <div className="absolute inset-0 flex items-center justify-center text-text-secondary bg-surface-2">
                                <ImageIcon size={32} />
                                <span className="ml-2 text-xs font-medium">AI 生成视觉图</span>
                            </div>
                        )}
                        
                        {/* Overlay Gradient */}
                        <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-black/60 to-transparent" />
                    </div>

                    {/* Text Content */}
                    <div className="p-4 flex-1 flex flex-col">
                        {isEditing ? (
                            <div className="space-y-4 flex-1">
                                <input 
                                    className="w-full text-lg font-bold border-b border-separator pb-1 focus:border-danger outline-none bg-transparent"
                                    value={content.title || ''}
                                    onChange={(e) => onUpdate({ ...content, title: e.target.value })}
                                    placeholder="输入标题"
                                />
                                <textarea 
                                    className="w-full text-sm text-text-secondary leading-relaxed border border-separator rounded p-2 focus:border-danger outline-none resize-none h-[200px] bg-surface-2"
                                    value={content.body || ''}
                                    onChange={(e) => onUpdate({ ...content, body: e.target.value })}
                                    placeholder="输入正文内容"
                                />
                                <div className="space-y-1">
                                    <label className="text-xs text-text-secondary">标签 (逗号分隔)</label>
                                    <input 
                                        className="w-full text-xs text-accent border-b border-separator pb-1 focus:border-danger outline-none bg-transparent"
                                        value={content.tags?.join(', ') || ''}
                                        onChange={(e) => onUpdate({ ...content, tags: e.target.value.split(',').map((t: string) => t.trim()) })}
                                    />
                                </div>
                            </div>
                        ) : (
                            <>
                                <h3 className="font-bold text-lg leading-tight mb-2">{content.title}</h3>
                                <p className="text-sm text-text-secondary whitespace-pre-line leading-relaxed mb-4 min-h-[100px]">
                                    {content.body}
                                </p>
                                <div className="flex flex-wrap gap-1 mb-4">
                                    {content.tags?.map((tag:string, i:number) => (
                                        <span key={i} className="text-accent text-xs">#{tag}</span>
                                    ))}
                                </div>
                            </>
                        )}
                        
                        <div className="text-xs text-text-secondary border-t pt-3 flex justify-between items-center mt-auto">
                            <span>2 分钟前</span>
                            <div className="flex gap-3">
                                <Share2 size={14} />
                            </div>
                        </div>
                    </div>
                    
                    {/* Mock Floating Action */}
                    {!isEditing && (
                        <div className="absolute bottom-4 right-4 w-12 h-12 bg-danger rounded-full shadow-lg flex items-center justify-center text-on-accent">
                            <span className="text-xl">❤</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    </div>
);

// --- Main Page ---

export default function ContentFactory() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { showToast } = useToast();
  
  // State Persistence via Global State
  const { 
    contentTopic: topic, setContentTopic: setTopic,
    contentPlatform: platform, setContentPlatform: setPlatform,
    contentTone: tone, setContentTone: setTone,
    contentPoints: points, setContentPoints: setPoints,
    contentResult: result, setContentResult: setResult,
    contentLogs: logs, setContentLogs: setLogs
  } = useGlobalState();
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isEditing, setIsEditing] = useState(false); // Local state for edit mode

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-fill from URL params
  useEffect(() => {
     const q = searchParams.get('q');
     const b = searchParams.get('brand');
     
     // Only set if we don't have existing topics (to respect persistence)
     // BUT if user explicitly clicked "Optimize" on diagnosis, they likely want to override.
     // Let's assume URL params usually imply a fresh intent.
     // We only update if 'q' is different from current topic to avoid reset on refresh if params persist but state also persists
     if (q && q !== topic) {
         setTopic(q);
         if (b) {
             let generatedPoints = `- 品牌主体: ${b}\n- 针对问题: "${q}"\n- 核心目标: 在回答中植入品牌软广`;
             
             if (q.includes('中小企业') || q.includes('成本')) {
                 generatedPoints += `\n- 强调高性价比和低门槛`;
             }
             if (q.includes('GEO') || q.includes('优化')) {
                 generatedPoints += `\n- 突出 ${b} 的AI搜索优化能力`;
             }
             setPoints(generatedPoints);
         }
     }
  }, [searchParams]); // eslint-disable-line

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleGenerate = async () => {
    if (!topic) return;
    setIsGenerating(true);
    setLogs([]); // Clear previous logs
    setResult(null);
    setIsEditing(false);

    const steps = [
        "正在深入分析话题趋势与搜索热度...",
        "扫描竞品高赞爆款内容...",
        "构建叙事结构 (钩子 -> 价值 -> 召唤)...",
        "撰写具有情绪共鸣的文案初稿...",
        "SEO 关键词植入与优化...",
        "生成病毒式传播视觉图 (DALL-E 3)...",
        "最终润色与格式校验..."
    ];

    // Initial Log
    setLogs([{
        id: Date.now(),
        message: "接收战略需求...",
        status: 'completed',
        timestamp: new Date().toLocaleTimeString()
    }, {
        id: Date.now() + 1,
        message: steps[0],
        status: 'active',
        timestamp: new Date().toLocaleTimeString()
    }]);

    let stepIndex = 1;
    const interval = setInterval(() => {
        if (stepIndex < steps.length) {
             setLogs((prev: any[]) => {
                const newLogs = [...prev];
                if (newLogs.length > 0) newLogs[newLogs.length - 1].status = 'completed';
                newLogs.push({
                    id: Date.now() + stepIndex,
                    message: steps[stepIndex],
                    status: 'active',
                    timestamp: new Date().toLocaleTimeString()
                });
                return newLogs;
            });
            stepIndex++;
        }
    }, 2500);

    try {
        const platformName = PLATFORMS.find(p => p.id === platform)?.name || platform;
        const toneName = TONES.find(t => t.id === tone)?.name || tone;

        const response = await api.post('/content/generate', {
            topic,
            platform: platformName,
            tone: toneName,
            key_points: points
        });

        const data = response.data;
        
        clearInterval(interval);
        
        // Complete all logs
        setLogs((prev: any[]) => {
             const final = prev.map(l => ({...l, status: 'completed' as const}));
             return [...final, {
                 id: Date.now(),
                 message: "生成验证完毕，任务完成。",
                 status: 'completed',
                 timestamp: new Date().toLocaleTimeString()
             }];
        });

        setResult(data);
        showToast("内容生成成功！", "success");

    } catch (error) {
        clearInterval(interval);
        console.error(error);
        setLogs((prev: any[]) => [...prev, {
            id: Date.now(),
            message: "连接数字大脑失败。",
            status: 'completed',
            timestamp: new Date().toLocaleTimeString() 
        }]);
        showToast("生成失败，请检查连接。", "error");
    } finally {
        setIsGenerating(false);
    }
  };

  const handleApprove = async () => {
    if (!result) return;
    setIsPublishing(true);

    try {
        // Map frontend platform to backend expected platform
        let backendPlatform = platform;
        
        const response = await api.post('/content/publish', {
            platform: backendPlatform,
            title: result.title,
            content: result.body + (result.image_url ? `\n\n![Image](${result.image_url})` : "")
        });

        const resData = response.data;
        
        // Add success log
        setLogs((prev: any[]) => [...prev, {
            id: Date.now(),
            message: `发布成功: ${resData.msg || '进入分发队列'}`,
            status: 'completed',
            timestamp: new Date().toLocaleTimeString()
        }]);

        // Auto-wake RPA client
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = 'digitalemployee://wake';
        document.body.appendChild(iframe);
        setTimeout(() => document.body.removeChild(iframe), 3000);

        showToast("已批准并发布！(正在唤起客户端)", "success");

        // Redirect to distribution after short delay
        setTimeout(() => {
            showToast("正在跳转至分发中心...", "success");
            // Pass job_id to auto-expand
            if (resData.job_id) {
                router.push(`/distribution?expandJobId=${resData.job_id}`);
            } else {
                router.push('/distribution');
            }
        }, 1500);

    } catch (e: any) {
        console.error(e);
        // Add error log
        setLogs((prev: any[]) => [...prev, {
            id: Date.now(),
            message: `发布失败: ${e.response?.data?.detail || e.message || "未知错误"}`,
            status: 'completed',
            timestamp: new Date().toLocaleTimeString()
        }]);
        showToast(`发布失败: ${e.response?.data?.detail || e.message || "未知错误"}`, "error");
    } finally {
        setIsPublishing(false);
    }
  };

  return (
    <div className="h-screen bg-bg text-text font-sans selection:bg-danger/30 w-full overflow-hidden flex flex-col">
      
      <div className="px-6 pt-4 shrink-0">
        <PageHeader
          title="内容工厂"
          description="定义内容生成任务，实时跟踪 Leo 的生成进程，并在发布前预览效果。"
        />
      </div>

      {/* 2. Main Workspace */}
      <main className="flex-1 flex min-h-0">
          
          {/* LEFT: Strategic Brief (Input) */}
          <div className="w-[400px] border-r border-separator p-6 flex flex-col gap-6 overflow-y-auto bg-surface/40">
              <div>
                  <h2 className="text-lg font-bold text-text mb-1">战略简报</h2>
                  <p className="text-xs text-text-secondary">为 Leo 定义内容生成任务。</p>
              </div>

              <div className="space-y-4">
                  {/* Topic */}
                  <div className="space-y-2">
                      <label className="text-xs font-bold text-text-secondary uppercase tracking-wider">核心话题</label>
                      <div className="relative">
                          <input 
                            type="text" 
                            value={topic}
                            onChange={(e) => setTopic(e.target.value)}
                            placeholder="例如: 2026年AI营销趋势..." 
                            className="w-full bg-surface border border-separator rounded-lg p-3 text-sm text-text focus:border-danger focus:outline-none transition-colors"
                          />
                          <Sparkles size={14} className="absolute right-3 top-3.5 text-danger opacity-50" />
                      </div>
                  </div>

                  {/* Platform */}
                  <div className="space-y-2">
                      <label className="text-xs font-bold text-text-secondary uppercase tracking-wider">发布平台</label>
                      <div className="grid grid-cols-2 gap-2">
                          {PLATFORMS.map(p => (
                              <button 
                                key={p.id}
                                onClick={() => setPlatform(p.id)}
                                className={`flex items-center gap-2 p-2 rounded-lg border text-xs font-medium transition-all ${
                                    platform === p.id 
                                    ? `bg-text/10 border-danger text-text shadow-[0_0_10px_rgb(var(--ui-danger)/0.2)]` 
                                    : 'bg-transparent border-separator text-text-secondary hover:bg-text/5'
                                }`}
                              >
                                  <span>{p.icon}</span>
                                  {p.name}
                              </button>
                          ))}
                      </div>
                  </div>

                   {/* Tone */}
                   <div className="space-y-2">
                      <label className="text-xs font-bold text-text-secondary uppercase tracking-wider">语气风格</label>
                      <div className="grid grid-cols-2 gap-2">
                          {TONES.map(t => (
                              <button 
                                key={t.id}
                                onClick={() => setTone(t.id)}
                                className={`flex items-center gap-2 p-2 rounded-lg border text-xs font-medium transition-all ${
                                    tone === t.id 
                                    ? `bg-text/10 border-danger text-text` 
                                    : 'bg-transparent border-separator text-text-secondary hover:bg-text/5'
                                }`}
                              >
                                  <span>{t.emoji}</span>
                                  {t.name}
                              </button>
                          ))}
                      </div>
                  </div>

                  {/* Key Points */}
                  <div className="space-y-2">
                      <label className="text-xs font-bold text-text-secondary uppercase tracking-wider">关键卖点</label>
                      <textarea 
                        value={points}
                        onChange={(e) => setPoints(e.target.value)}
                        placeholder="- 低成本优势&#10;- 强调易用性..."
                        className="w-full h-24 bg-surface border border-separator rounded-lg p-3 text-sm text-text focus:border-danger focus:outline-none transition-colors resize-none"
                      />
                  </div>
              </div>

              <div className="mt-auto pt-6 border-t border-separator">
                  <button 
                    onClick={handleGenerate}
                    disabled={isGenerating || !topic}
                    className={`w-full py-3 rounded-lg flex items-center justify-center gap-2 font-bold text-sm transition-all ${
                        isGenerating || !topic 
                        ? 'bg-surface-2 text-text-secondary cursor-not-allowed' 
                        : 'bg-danger hover:bg-danger/90 text-on-accent shadow-card'
                    }`}
                  >
                      {isGenerating ? (
                          <>
                            <Loader2 size={16} className="animate-spin" />
                            思考中...
                          </>
                      ) : (
                          <>
                            <Send size={16} />
                            立即生成
                          </>
                      )}
                  </button>
              </div>
          </div>

          {/* MIDDLE: Thought Chain (Process) */}
          <div className="flex-1 bg-bg p-8 flex flex-col relative overflow-hidden">
              <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at center, rgb(var(--ui-danger)) 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
              
              <div className="relative z-10 max-w-2xl mx-auto w-full">
                  <h3 className="text-xs font-mono text-text-secondary uppercase tracking-widest mb-2 border-b border-separator pb-2">
                      Leo 神经网络处理进程 (Neural Process)
                  </h3>

                  <div className="space-y-6 max-h-[calc(100vh-280px)] overflow-y-auto custom-scrollbar pr-3 pb-10">
                      {logs.length === 0 && !result && (
                          <div className="text-center py-20 opacity-30">
                              <Bot size={48} className="mx-auto mb-4" />
                              <p className="text-sm font-mono">等待任务指令...</p>
                          </div>
                      )}

                      {logs.map((log) => (
                          <div key={log.id} className="flex gap-4 animate-in fade-in slide-in-from-left-4 duration-500">
                              <div className="relative flex flex-col items-center">
                                  <div className={`w-3 h-3 rounded-full border-2 z-10 bg-bg ${
                                      log.status === 'completed' ? 'border-danger bg-danger' :
                                      log.status === 'active' ? 'border-danger animate-pulse' :
                                      'border-separator'
                                  }`} />
                                  <div className="w-px h-full bg-surface-2 absolute top-3" />
                              </div>
                              <div className="pb-4">
                                  <div className={`text-sm font-mono mb-1 ${
                                      log.status === 'active' ? 'text-danger' : 'text-text'
                                  }`}>
                                      {log.message}
                                  </div>
                                  <div className="text-[10px] text-text-tertiary font-mono">
                                      {log.timestamp}
                                  </div>
                              </div>
                          </div>
                      ))}
                      <div ref={logsEndRef} />
                  </div>
              </div>
          </div>

          {/* RIGHT: Output Preview */}
          <div className="w-[380px] border-l border-separator bg-surface/50 backdrop-blur p-8 flex flex-col justify-center relative">
              <div className="absolute top-4 right-4 z-50">
                  <button 
                    onClick={() => setIsEditing(!isEditing)}
                    className={`p-2 rounded transition-colors ${isEditing ? 'bg-danger text-on-accent' : 'hover:bg-text/5 text-text-secondary hover:text-text'}`}
                    title={isEditing ? "退出编辑" : "编辑内容"}
                    disabled={!result}
                  >
                      {isEditing ? <X size={16} /> : <Edit3 size={16} />}
                  </button>
              </div>
              
              <div className="mb-8 text-center">
                  <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-1">实机预览 (Live Preview)</h3>
                  <p className="text-[10px] text-text-tertiary">iPhone 15 Pro Max • 5G</p>
              </div>

              <PhoneMockup 
                content={result} 
                isEditing={isEditing}
                onUpdate={setResult}
              />
              
              {result && (
                  <div className="mt-8 flex gap-3">
                      <button 
                        onClick={handleApprove}
                        disabled={isPublishing || isEditing}
                        className={`flex-1 py-2 rounded-lg border text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                            isEditing 
                            ? 'border-separator text-text-tertiary cursor-not-allowed'
                            : 'border-danger/30 bg-danger/10 text-danger hover:bg-danger/20'
                        }`}
                      >
                          {isPublishing ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                          {isPublishing ? "发布中..." : "批准并发布"}
                      </button>
                  </div>
              )}
          </div>

      </main>
    </div>
  );
}
