"use client";
import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import api from '../../lib/api';
import { Share2, Bot, CheckCircle, Clock, AlertTriangle, RefreshCw, Layers, RotateCcw, ExternalLink, Trash2, Edit, ChevronDown, ChevronUp, Maximize2, Minimize2, StopCircle, Monitor } from 'lucide-react';
import { useGlobalState } from '../../contexts/GlobalStateContext';
import { useToast } from '../../contexts/ToastContext';
import { useSearchParams } from 'next/navigation';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState } from '@/components/ui/empty-state';
import { Modal } from '@/components/ui/modal';
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from '@/components/ui/table';
import { Button } from '@/components/ui/button';

interface RPAJob {
  id: number;
  platform: string;
  job_type: string;
  status: string;
  result_log: string | null;
  execution_logs?: { timestamp: number, step: string, message: string, status: string }[];
  created_at: string;
  payload?: any;
}

const statusConfig = {
  queued: { label: "排队中", color: "bg-surface-2 text-text-secondary border-separator", icon: Clock },
  claimed: { label: "执行中", color: "bg-accent/10 text-accent border-accent/20", icon: RefreshCw },
  success: { label: "发布成功", color: "bg-success/10 text-success border-success/20", icon: CheckCircle },
  failed: { label: "执行失败", color: "bg-danger/10 text-danger border-danger/20", icon: AlertTriangle }
};


export default function Distribution() {
  const { 
    distJobs: jobs, setDistJobs: setJobs,
    distExpandedJobId: expandedJobId, setDistExpandedJobId: setExpandedJobId
  } = useGlobalState();

  // Use Next.js hook for params
  const searchParams = useSearchParams();
  // Define fetchJobs early so it can be called in effects
  // We need to move fetchJobs up or wrap it in useCallback if we want to use it in useEffect above.
  // Instead, let's just trigger a "needsRefresh" flag or call it after definition.
  
  const [loading, setLoading] = useState(jobs.length === 0);
  const [filterPlatform, setFilterPlatform] = useState<string>('all');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [total, setTotal] = useState<number>(0);
  const [deletingIds, setDeletingIds] = useState<number[]>([]);
  const [jobDetails, setJobDetails] = useState<Record<number, RPAJob>>({});

  const [editingJob, setEditingJob] = useState<RPAJob | null>(null);
  const [editForm, setEditForm] = useState({ title: '', content: '' });
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [maximizeLogs, setMaximizeLogs] = useState(false);
  const pollRef = useRef<number | null>(null);
  const { showToast } = useToast();

  // Platform tabs config (Synced with Optimize/Content Creation)
  const PLATFORMS = [
     { id: 'all', label: '全部任务', alias: [] as string[] },
     { id: 'linkedin', label: 'LinkedIn', alias: [] as string[] },
     { id: 'wordpress', label: 'WordPress', alias: ['website', 'wp'] },
     { id: 'x', label: 'X / Twitter', alias: ['twitter'] },
     { id: 'redbook', label: '小红书', alias: ['xiaohongshu'] },
     { id: 'tiktok', label: '抖音', alias: ['douyin'] },
     { id: 'zhihu', label: '知乎', alias: ['social_qa'] },
     { id: 'baidu_baike', label: '百度词条', alias: ['baike', 'wiki'] }
  ];

  // Fetch Jobs Function
  const fetchJobs = async (p: number = page, limit: number = pageSize) => {
    setLoading(true);
    try {
      const offset = (p - 1) * limit;
      // Filter out view_browser jobs on backend to ensure pagination works correctly
      const res = await api.get(`/api/v1/rpa/jobs?limit=${limit}&offset=${offset}&exclude_job_type=view_browser`);
      if (res.status === 200) {
        let items = [];
        let totalCount = 0;
        
        // Support older responses (array) for backward compatibility
        if (Array.isArray(res.data)) {
          items = res.data;
          totalCount = res.data.length;
        } else if (res.data && res.data.items) {
          items = res.data.items;
          totalCount = res.data.total || res.data.items.length;
        } 
        
        // Filter out system view jobs and update state
        const visibleItems = items.filter((j: any) => j.job_type !== 'view_browser');
        setJobs(visibleItems);
        // Adjust total count loosely
        setTotal(totalCount > items.length ? totalCount - (items.length - visibleItems.length) : visibleItems.length);
        
      }
    } catch (error) {
      console.error("Failed to fetch jobs", error);
      showToast && showToast('无法获取任务列表', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Handle auto-expand logic (After fetchJobs is defined)
  useEffect(() => {
     if (searchParams) {
         const paramId = searchParams.get('expandJobId');
         if (paramId) {
             const id = parseInt(paramId);
             if (!isNaN(id)) {
                 // Trigger immediate refresh to ensure we have the new job
                 fetchJobs(1, 20); 
                 
                 setExpandedJobId(id);
                 // Optional: clean up URL
                 window.history.replaceState({}, '', '/distribution');
             }
         }
     }
  }, [searchParams]);

  // Filter jobs logic
  const filteredJobs = jobs.filter(job => {
      if (filterPlatform === 'all') return true;
      const platformConfig = PLATFORMS.find(p => p.id === filterPlatform);
      if (!platformConfig) return false;
      return job.platform === filterPlatform || (platformConfig.alias && platformConfig.alias.includes(job.platform));
  });

  const handleEdit = (e: React.MouseEvent, job: RPAJob) => {
      e.stopPropagation();
      setEditingJob(job);
      setEditForm({
          title: job.payload?.title || '',
          content: job.payload?.content || ''
      });
  };

  // New Handler for triggering remote view (clicking link button)
  const handleTriggerView = async (e: React.MouseEvent, url: string, platform: string = 'xiaohongshu') => {
      e.preventDefault();
      e.stopPropagation();
      showToast('正在呼叫RPA机器人打开窗口...', 'info');
      try {
          await api.get(`/api/v1/rpa/trigger-view?url=${encodeURIComponent(url)}&platform=${platform}`);
      } catch (err: any) {
           const msg = err?.response?.data?.detail || err?.message || '呼叫失败';
           showToast(msg, 'error');
      }
  };

  const saveEdit = async () => {
      if (!editingJob) return;
      try {
          const res = await api.put(`/api/v1/rpa/tasks/${editingJob.id}`, editForm);
          if (res.status === 200) {
              setEditingJob(null);
              showToast('修改成功', 'success');
              fetchJobs();
          } else {
            showToast('保存失败', 'error');
          }
      } catch (e) {
          console.error(e);
          showToast((e as any)?.message || '保存出错', 'error');
      }
  };

  const fetchJobDetail = async (jobId: number) => {
    try {
      // try dedicated API first
      const res = await api.get(`/api/v1/rpa/tasks/${jobId}`);
      if (res.status === 200 && res.data) {
        // cache detailed job separately to ensure execution_logs are shown
        setJobDetails(prev => ({ ...prev, [jobId]: res.data }));
        // also merge into jobs list for quick reflect
        setJobs((prev) => {
          const found = prev.find(j => j.id === jobId);
          if (!found) return [res.data, ...prev];
          return prev.map(j => j.id === jobId ? res.data : j);
        });
        return;
      }
    } catch (err) {
      // If forbidden, notify user about permission to view logs
      console.error('Fetch job detail error', err);
      if ((err as any)?.response?.status === 403) {
        showToast && showToast('没有权限查看该任务详情和实时日志', 'error');
        return;
      }
      // fallback: refresh full list and pick the job
      try {
        await fetchJobs();
      } catch (e) {
        console.error('Failed to fetch job detail fallback', e);
      }
    }
  };

  const handleAction = async (e: React.MouseEvent, jobId: number, action: 'retry' | 'cancel' | 'delete') => {
      e.stopPropagation(); // Prevent row click expansion
      if (action === 'delete') {
        setDeleteConfirmId(jobId);
        return;
      }
      try {
        if (action === 'retry') {
          // Auto-wake RPA client on retry
          const iframe = document.createElement('iframe');
          iframe.style.display = 'none';
          iframe.src = 'digitalemployee://wake';
          document.body.appendChild(iframe);
          setTimeout(() => document.body.removeChild(iframe), 3000);

          try {
            const res = await api.post(`/api/v1/rpa/tasks/${jobId}/retry`);
            if (res.status === 200) {
              showToast('重试已触发 (尝试唤起客户端)', 'success');
              fetchJobs();
              return;
            }
          } catch (err: any) {
            console.error('Retry error', err);
            const msg = err?.message === 'Network Error' ? '网络异常，无法连接到服务器' : (err?.response?.data?.detail || err?.message || '重试失败');
            showToast(msg, 'error');
            return;
          }
        }
        if (action === 'cancel') {
          try {
            const res = await api.post(`/api/v1/rpa/tasks/${jobId}/cancel`);
            if (res.status === 200) {
              showToast('任务已取消', 'success');
              fetchJobs();
              return;
            }
          } catch (err: any) {
            console.error('Cancel error', err);
            const msg = err?.message === 'Network Error' ? '网络异常，无法连接到服务器' : (err?.response?.data?.detail || err?.message || '取消失败');
            showToast(msg, 'error');
            return;
          }
        }
        console.warn('Unhandled action or non-200 response', action);
      } catch (error: any) {
        console.error("Action failed", error);
        const msg = error?.response?.data?.detail || error?.message || '操作失败';
        alert(msg);
      }
    };

    const confirmDelete = async () => {
      if (deleteConfirmId === null) return;
      const idToDelete = deleteConfirmId;
      // mark deleting and close modal to avoid blocking UI
      setDeletingIds(prev => [...prev, idToDelete]);
      setDeleteConfirmId(null);
      try {
        const res = await api.delete(`/api/v1/rpa/tasks/${idToDelete}`);
        if (res.status === 200) {
          showToast('删除成功', 'success');
          // remove from local list immediately
          setJobs(prev => prev.filter(j => j.id !== idToDelete));
          // refresh current page to keep total accurate
          fetchJobs(page, pageSize);
        } else {
          showToast(res.data?.msg || '删除失败', 'error');
        }
      } catch (error: any) {
        console.error("Delete failed", error);
        const msg = error?.response?.data?.detail || error?.message || '删除失败';
        showToast(msg, 'error');
      } finally {
        setDeletingIds(prev => prev.filter(i => i !== idToDelete));
      }
    };

    useEffect(() => {
      fetchJobs(page, pageSize);
      const interval = setInterval(() => fetchJobs(page, pageSize), 5000); // 5s for list
      return () => clearInterval(interval);
    }, [page, pageSize]);

    // Independent polling for details when expanded
    useEffect(() => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      if (expandedJobId !== null) {
        fetchJobDetail(expandedJobId);
        // Simply poll while expanded to keep logs fresh, regardless of status
        // Logic loop prevented by removing 'jobs' dependency
        const id = window.setInterval(() => {
           fetchJobDetail(expandedJobId);
        }, 2000); 
        pollRef.current = id as unknown as number;
      }
      return () => {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      };
    }, [expandedJobId]); // Remove 'jobs' dependency to fix infinite loop

  // Stats calculation
  const stats = {
      total: jobs.length,
      running: jobs.filter(j => j.status === 'claimed').length,
      successRate: jobs.length > 0 ? Math.round((jobs.filter(j => j.status === 'success').length / jobs.length) * 100) : 0,
      today: jobs.filter(j => new Date(j.created_at).toDateString() === new Date().toDateString()).length
  };

  return (
    <div className="h-full flex flex-col p-4 animate-fade-in-up space-y-4">
      <PageHeader
        title="营销矩阵"
        description="全平台内容投放任务队列与实时执行日志。"
        className="mb-0 shrink-0"
      />
      {/* 1. Header & Stats Section */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 shrink-0">
         <div className="glass-card p-4 flex items-center justify-between border-l-4 border-l-accent">
            <div>
               <p className="text-xs text-text-secondary uppercase font-bold tracking-wider">投放任务总数</p>
               <h3 className="text-2xl font-bold text-text mt-1 tabular-nums">{stats.total}</h3>
            </div>
            <div className="p-3 bg-accent/10 rounded-lg text-accent">
               <Layers size={20}/>
            </div>
         </div>
         <div className="glass-card p-4 flex items-center justify-between border-l-4 border-l-tint-revenue">
            <div>
               <p className="text-xs text-text-secondary uppercase font-bold tracking-wider">正在执行/排队</p>
               <h3 className="text-2xl font-bold text-text mt-1 tabular-nums">{stats.running}</h3>
            </div>
            <div className="p-3 bg-accent/10 rounded-lg text-accent animate-pulse">
               <RefreshCw size={20} className={stats.running > 0 ? "animate-spin" : ""}/>
            </div>
         </div>
         <div className="glass-card p-4 flex items-center justify-between border-l-4 border-l-success">
            <div>
               <p className="text-xs text-text-secondary uppercase font-bold tracking-wider">投放成功率</p>
               <h3 className="text-2xl font-bold text-text mt-1 tabular-nums">{stats.successRate}%</h3>
            </div>
            <div className="p-3 bg-success/10 rounded-lg text-success">
               <CheckCircle size={20}/>
            </div>
         </div>
         <div className="glass-card p-4 flex items-center justify-between border-l-4 border-l-warning">
            <div>
               <p className="text-xs text-text-secondary uppercase font-bold tracking-wider">今日新增</p>
               <h3 className="text-2xl font-bold text-text mt-1 tabular-nums">+{stats.today}</h3>
            </div>
            <div className="p-3 bg-warning/10 rounded-lg text-warning">
               <Clock size={20}/>
            </div>
         </div>
      </div>

      {/* 2. Main Content Area */}
      <div className="glass-card flex-1 flex flex-col min-h-0 overflow-hidden border border-separator">
        {/* Toolbar */}
        <div className="p-2 border-b border-separator flex gap-2 shrink-0 bg-surface/60">
            {PLATFORMS.map(p => (
               <button
                  key={p.id}
                  onClick={() => setFilterPlatform(p.id)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                     filterPlatform === p.id 
                     ? 'bg-text/10 text-text shadow-sm border border-separator' 
                     : 'text-text-secondary hover:text-text hover:bg-text/5 border border-transparent'
                  }`}
               >
                  {p.label}
               </button>
            ))}
            <div className="flex-1"></div>
            <Link href="/settings/client">
                <button className="mr-2 p-1.5 hover:bg-text/5 rounded text-accent hover:text-accent transition-colors flex items-center gap-1 text-xs border border-accent/20 bg-accent/10 px-3">
                    <Monitor size={12} /> 下载客户端
                </button>
            </Link>
            <button 
                onClick={() => fetchJobs(page, pageSize)}
                className="p-1.5 hover:bg-text/5 rounded text-text-secondary hover:text-text transition-colors flex items-center gap-1 text-xs">
                <RefreshCw size={12} /> 刷新列表
            </button>
        </div>
        
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <Table className="text-sm text-text-secondary">
            <TableHead className="bg-bg/80 backdrop-blur sticky top-0 z-10">
                            <TableRow className="hover:bg-transparent">
                                <TableHeaderCell className="px-6 py-3 w-20">ID</TableHeaderCell>
                                <TableHeaderCell className="px-6 py-3 w-32">平台</TableHeaderCell>
                                <TableHeaderCell className="px-6 py-3 w-40">状态</TableHeaderCell>
                                <TableHeaderCell className="px-6 py-3">执行结果 / 任务标题</TableHeaderCell>
                                <TableHeaderCell className="px-6 py-3 text-right w-48">创建时间</TableHeaderCell>
                            </TableRow>
            </TableHead>
            <TableBody>
              {loading && jobs.length === 0 ? (
                 <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={5} className="px-6 py-20 text-center text-text-secondary">
                        <div className="flex flex-col items-center gap-3">
                           <RefreshCw className="animate-spin opacity-50" size={24}/>
                           <p>正在同步全网投放数据...</p>
                        </div>
                    </TableCell>
                 </TableRow>
              ) : filteredJobs.length === 0 ? (
                 <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={5} className="p-0">
                        <EmptyState
                            size="sm"
                            icon={Layers}
                            title="暂无符合条件的任务记录"
                            description="调整平台筛选，或从「内容工场」创建新的投放任务。"
                        />
                    </TableCell>
                 </TableRow>
              ) : (
                filteredJobs.map((job) => {
                  const statusInfo = statusConfig[job.status as keyof typeof statusConfig] || statusConfig.queued;
                  const StatusIcon = statusInfo.icon;
                  const isExpanded = expandedJobId === job.id;
                  
                  return (
                  <React.Fragment key={job.id}>
                    <TableRow 
                        onClick={() => setExpandedJobId(isExpanded ? null : job.id)}
                        className={`transition-colors cursor-pointer group ${isExpanded ? 'bg-text/[0.04]' : ''}`}
                    >
                        <TableCell className="px-6 py-4 font-mono text-xs text-text-secondary">#{job.id}</TableCell>
                        <TableCell className="px-6 py-4">
                            {(job.platform === 'redbook' || job.platform === 'xiaohongshu') ? (
                                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-danger"></span> 小红书</div>
                            ) : (job.platform === 'tiktok' || job.platform === 'douyin') ? (
                                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-bg border border-separator"></span> 抖音</div>
                            ) : (job.platform === 'zhihu' || job.platform === 'social_qa') ? (
                                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-accent"></span> 知乎</div>
                            ) : (job.platform === 'baidu_baike' || job.platform === 'baike' || job.platform === 'wiki') ? (
                                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-accent"></span> 百度词条</div>
                            ) : (job.platform === 'media' || job.platform === 'wechat') ? (
                                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-success"></span> 媒体通稿</div>
                            ) : (job.platform === 'website' || job.platform === 'wordpress' || job.platform === 'wp') ? (
                                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-accent"></span> WordPress</div>
                            ) : job.platform === 'linkedin' ? (
                                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-accent"></span> LinkedIn</div>
                            ) : (job.platform === 'x' || job.platform === 'twitter') ? (
                                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-surface-2"></span> X</div>
                            ) : (
                                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-text-tertiary"></span> {job.platform}</div>
                            )}
                        </TableCell>
                        <TableCell className="px-6 py-4">
                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${statusInfo.color}`}>
                                <StatusIcon size={12} className={job.status === 'claimed' ? 'animate-spin' : ''} />
                                {statusInfo.label}
                            </span>
                        </TableCell>
                        <TableCell className="px-6 py-4 max-w-md">
                            <div className="flex flex-col gap-1">
                                <span className="text-text font-medium truncate" title={job.payload?.title}>
                                   {job.payload?.title || "无标题任务"}
                                </span>
                            </div>
                        </TableCell>
                        <TableCell className="px-6 py-4 text-right text-xs text-text-secondary font-mono whitespace-nowrap">
                          <div className="flex items-center justify-end gap-2">
                            <span className="tabular-nums">{new Date(job.created_at).toLocaleString('zh-CN')}</span>
                            <button onClick={(e) => { e.stopPropagation(); setExpandedJobId(isExpanded ? null : job.id); }} className="p-1 rounded hover:bg-text/5">
                              {isExpanded ? <ChevronUp size={14}/> : <ChevronDown size={14}/>} 
                            </button>
                          </div>
                        </TableCell>
                    </TableRow>
                    
                    {/* Expanded Detail Panel */}
                    {isExpanded && (
                        <tr className="bg-surface/50 border-b border-separator shadow-inner">
                            <td colSpan={6} className="p-0">
                                <div className={maximizeLogs ? "fixed inset-4 z-50 bg-surface border border-separator rounded-xl shadow-2xl overflow-hidden grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-6 p-6 animate-fade-in hidden-scrollbar" : "animate-fade-in p-6 grid grid-cols-1 lg:grid-cols-2 gap-6 h-[500px]"}>
                                    
                                    {/* Left Column: Content & Controls - Always Visible now */}
                                    <div className="flex flex-col h-full overflow-hidden">
                                      <div className="flex items-center justify-between mb-3 shrink-0">
                                        <div className="text-xs text-text-secondary font-bold uppercase tracking-wider">任务详情与控制</div>
                                        <div className="flex items-center gap-2">
                                          {(job.status === 'claimed' || job.status === 'queued') && (
                                            <button 
                                                onClick={(e) => handleAction(e, job.id, 'cancel')}
                                                className="px-2 py-1 bg-warning/10 hover:bg-warning/20 text-warning border border-warning/20 rounded text-xs flex items-center gap-1 transition-all"
                                            >
                                                <StopCircle size={14}/> 停止
                                            </button>
                                          )}
                                          <button 
                                            onClick={(e) => handleEdit(e, job)}
                                            className="px-2 py-1 bg-accent/10 hover:bg-accent/20 text-accent border border-accent/20 rounded text-xs flex items-center gap-1 transition-all"
                                          >
                                            <Edit size={14}/> 编辑
                                          </button>
                                          <button 
                                            onClick={(e) => handleAction(e, job.id, 'retry')}
                                            className="px-2 py-1 bg-text/5 hover:bg-text/10 text-text border border-separator rounded text-xs flex items-center gap-1 transition-all"
                                          >
                                            <RotateCcw size={14}/> 重试
                                          </button>
                                          <button 
                                            onClick={(e) => handleAction(e, job.id, 'delete')}
                                            disabled={deletingIds.includes(job.id)}
                                            className="px-2 py-1 bg-danger/10 hover:bg-danger/20 text-danger border border-danger/20 rounded text-xs flex items-center gap-1 transition-all disabled:opacity-60"
                                          >
                                            {deletingIds.includes(job.id) ? <RefreshCw size={14} className="animate-spin"/> : <Trash2 size={14}/>} 删除
                                          </button>
                                          {job.status === 'success' && job.result_log && job.result_log.includes('|||LINK:') && (
                                              ['xiaohongshu', 'redbook'].includes(job.platform?.toLowerCase()) ? (
                                                <button
                                                  onClick={(e) => handleTriggerView(e, job.result_log!.match(/\|\|\|LINK:(.+?)\|\|\|/)?.[1] || '', job.platform)}
                                                  className="px-2 py-1 bg-accent hover:bg-accent-hover text-on-accent rounded text-xs font-bold flex items-center gap-1 transition-colors"
                                                  title="在RPA浏览器中查看（用于访问草稿箱）"
                                                >
                                                  <Monitor size={12}/> RPA预览
                                                </button>
                                              ) : (
                                                <a 
                                                  href={job.result_log.match(/\|\|\|LINK:(.+?)\|\|\|/)?.[1]} 
                                                  target="_blank" 
                                                  className="px-2 py-1 bg-accent hover:bg-accent-hover text-on-accent rounded text-xs font-bold flex items-center gap-1 transition-colors"
                                                >
                                                  <ExternalLink size={12}/> 预览/编辑
                                                </a>
                                              )
                                          )}
                                        </div>
                                      </div>
                                      
                                      <div className="flex-1 bg-bg/20 rounded-lg p-4 border border-separator flex flex-col min-h-0">
                                         <h4 className="text-sm font-bold text-text mb-2 shrink-0">{job.payload?.title || "无标题"}</h4>
                                         <div className="text-text-secondary font-mono text-xs whitespace-pre-wrap break-words leading-relaxed overflow-y-auto custom-scrollbar flex-1 min-h-0">
                                           {job.payload?.content || "无内容"}
                                         </div>
                                      </div>
                                    </div>

                                    {/* Right Column: Logs */}
                                    <div className="flex flex-col h-full overflow-hidden">
                                        <div className="flex justify-between items-center mb-3 shrink-0">
                                            <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-2">
                                                <Share2 size={12}/> 实时执行日志
                                            </h4>
                                            <div className="flex items-center gap-2">
                                                {job.status === 'claimed' && (
                                                    <span className="text-[10px] text-accent animate-pulse flex items-center gap-1 mr-2">
                                                        <div className="w-1.5 h-1.5 bg-accent rounded-full"></div>
                                                        实时
                                                    </span>
                                                )}
                                                <button onClick={() => setMaximizeLogs(!maximizeLogs)} className="text-text-secondary hover:text-text transition-colors" title={maximizeLogs ? "还原" : "最大化详情页"}>
                                                    {maximizeLogs ? <Minimize2 size={14}/> : <Maximize2 size={14}/>}
                                                </button>
                                            </div>
                                        </div>
                                        <div className={`flex-1 font-mono text-xs space-y-1.5 overflow-y-auto p-4 bg-bg rounded-lg border border-separator shadow-inner custom-scrollbar h-full`}>
                                            {((jobDetails[job.id] && jobDetails[job.id].execution_logs) || job.execution_logs) && (((jobDetails[job.id] && jobDetails[job.id].execution_logs) || job.execution_logs)?.length ?? 0) > 0 ? (
                                              (((jobDetails[job.id] && jobDetails[job.id].execution_logs) || job.execution_logs) || []).slice().reverse().map((log, i) => (
                                                    <div key={i} className="flex gap-3 group/log border-b border-separator pb-1 mb-1 last:border-0">
                                                        <span className="text-text-tertiary shrink-0 select-none w-16 text-[10px] pt-0.5">
                                                    {new Date((log.timestamp || 0) * 1000).toLocaleTimeString('zh-CN')}
                                                        </span>
                                                        <div className="flex-1 min-w-0">
                                                            <div className={`font-bold mb-0.5 ${
                                                                log.status === 'success' ? 'text-success' :
                                                                log.status === 'warning' ? 'text-warning' :
                                                                log.status === 'error' ? 'text-danger' : 'text-accent'
                                                            }`}>
                                                                {log.step}
                                                            </div>
                                                            <div className="text-text-secondary leading-relaxed whitespace-nowrap overflow-x-auto custom-scrollbar" style={{WebkitOverflowScrolling:'touch'}}>
                                                                {log.message}
                                                            </div>
                                                        </div>
                                                    </div>
                                              ))
                                            ) : (
                                                <EmptyState
                                                    size="sm"
                                                    icon={Layers}
                                                    title="暂无日志数据"
                                                    description="任务开始执行后，实时日志会显示在这里。"
                                                />
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    )}
                  </React.Fragment>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    
    {/* Edit Modal */}
    <Modal
      open={!!editingJob}
      onClose={() => setEditingJob(null)}
      title={`编辑任务内容 #${editingJob?.id ?? ''}`}
      className="max-w-2xl"
      footer={
        <>
          <Button variant="ghost" onClick={() => setEditingJob(null)}>取消</Button>
          <Button onClick={saveEdit}>保存修改</Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-bold text-text-secondary uppercase mb-1">标题</label>
          <input 
            className="w-full h-10 bg-surface-2 border border-separator rounded-md px-3 text-text text-sm focus:border-accent outline-none transition-colors"
            value={editForm.title}
            onChange={e => setEditForm({...editForm, title: e.target.value})}
          />
        </div>
        <div className="flex flex-col">
          <label className="block text-xs font-bold text-text-secondary uppercase mb-1">正文内容</label>
          <textarea 
            className="w-full h-64 bg-surface-2 border border-separator rounded-md p-3 text-text font-mono text-sm leading-relaxed focus:border-accent outline-none resize-none transition-colors"
            value={editForm.content}
            onChange={e => setEditForm({...editForm, content: e.target.value})}
          />
        </div>
      </div>
    </Modal>

    {/* 删除确认 */}
    <Modal
      open={deleteConfirmId !== null}
      onClose={() => setDeleteConfirmId(null)}
      title="确认删除"
      description="确定要删除这条任务记录吗？此操作不可恢复。"
      className="max-w-sm"
      footer={
        <>
          <Button variant="secondary" onClick={() => setDeleteConfirmId(null)}>取消</Button>
          <Button variant="destructive" onClick={confirmDelete}>确认删除</Button>
        </>
      }
    >
      <div className="flex justify-center py-2">
        <Trash2 size={32} className="text-danger" />
      </div>
    </Modal>

    {/* Pagination Controls */}
    <div className="flex items-center justify-between gap-2 p-3 border-t border-separator">
      <div className="text-xs text-text-secondary">共 {total} 条</div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
          className="px-3 py-1 text-xs rounded bg-surface-2 hover:bg-surface-2 disabled:opacity-50"
        >上一页</button>
        <span className="text-xs text-text">第 {page} 页</span>
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={page * pageSize >= total}
          className="px-3 py-1 text-xs rounded bg-surface-2 hover:bg-surface-2 disabled:opacity-50"
        >下一页</button>
        <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }} className="ml-2 bg-surface text-xs p-1 rounded">
          <option value={10}>10 / 页</option>
          <option value={20}>20 / 页</option>
          <option value={50}>50 / 页</option>
        </select>
      </div>
    </div>

    </div>
  );
}
