"use client";
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Send, Clock, ArrowLeft, Loader2, Play } from 'lucide-react';
import Link from 'next/link';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState } from '@/components/ui/empty-state';

const API_URL = "http://localhost:8010";

const MISSION_STATUS_LABELS: Record<string, string> = {
  planning: '规划中',
  pending: '待处理',
  queued: '排队中',
  in_progress: '进行中',
  running: '进行中',
  completed: '已完成',
  failed: '失败',
};

export default function MissionPage() {
  const searchParams = useSearchParams();
  const employeeId = searchParams.get('employee_id');
  const [employee, setEmployee] = useState<any>(null);
  const [objective, setObjective] = useState("");
  const [mission, setMission] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [planning, setPlanning] = useState(false); // AI thinking state

  // Load Employee details
  useEffect(() => {
     if(employeeId) {
         // Should have an endpoint to get single employee, but for now I'll use the list or assume context
         // Ideally: fetch(`${API_URL}/agents/employees/${employeeId}`)
     }
  }, [employeeId]);

  const handleStartMission = async () => {
    if (!objective.trim()) return;
    setPlanning(true);
    
    try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_URL}/agents/missions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({
                employee_id: parseInt(employeeId || "0"), // Fallback if missing
                title: "New Mission", // Could be extracted from objective
                objective: objective
            })
        });
        
        if (res.ok) {
            const data = await res.json();
            // Poll for updates if it was async, or just set if sync
            setMission(data); 
            // If the plan is empty, we might need to poll. 
            // Our backend implementation was synchronous for the demo, so `data` should have tasks.
            if (data.id) {
                 fetchMissionDetails(data.id);
            }
        }
    } catch (e) {
        console.error(e);
    } finally {
        setPlanning(false);
    }
  };

  const fetchMissionDetails = async (id: number) => {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/agents/missions/${id}`, {
          headers: { 'Authorization': `Bearer ${token}` }
      });
      if(res.ok) {
          const data = await res.json(); // { mission, tasks }
          setMission(data);
      }
  };

  return (
    <div className="min-h-screen bg-bg text-text p-8 flex flex-col h-screen">
       {/* Header */}
       <div className="border-b border-separator pb-6 mb-6">
           <Link href="/workforce" className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text mb-4 transition-colors">
               <ArrowLeft size={14} /> 返回团队
           </Link>
           <PageHeader
             title="任务控制台"
             description="下达一个高层目标，观看数字员工自动拆解并执行。"
             className="mb-0"
           />
       </div>

       <div className="flex flex-1 gap-8 overflow-hidden">
           {/* Left: Chat / Input */}
           <div className="w-1/3 flex flex-col space-y-4">
               <div className="bg-surface p-6 rounded-xl border border-separator flex-1 flex flex-col shadow-card">
                   <div className="flex-1 space-y-4 overflow-y-auto mb-4">
                        {/* Agent Greeting */}
                        <div className="flex gap-4">
                            <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-xs text-on-accent font-bold">AI</div>
                            <div className="bg-surface-2 p-3 rounded-lg rounded-tl-none text-sm text-text">
                                准备就绪，请下达我的下一个目标。
                            </div>
                        </div>

                        {/* User Objective */}
                        {mission && (
                            <div className="flex gap-4 flex-row-reverse">
                                <div className="w-8 h-8 rounded-full bg-surface-2 flex items-center justify-center text-xs text-text-secondary font-bold">我</div>
                                <div className="bg-accent/15 border border-accent/25 p-3 rounded-lg rounded-tr-none text-sm text-text">
                                    {mission.mission?.objective || objective}
                                </div>
                            </div>
                        )}
                   </div>

                   {/* Input Area */}
                   {!mission ? (
                        <div className="relative">
                            <textarea 
                                className="w-full bg-bg border border-separator rounded-lg p-3 pr-12 text-sm text-text placeholder:text-text-tertiary focus:ring-2 focus:ring-accent focus:outline-none resize-none h-32"
                                placeholder="例如：对「GlobalPilot AI」的产品定价进行竞品分析…"
                                value={objective}
                                onChange={(e) => setObjective(e.target.value)}
                            />
                            <button 
                                onClick={handleStartMission}
                                disabled={planning || !objective.trim()}
                                className="absolute bottom-3 right-3 bg-accent hover:bg-accent-hover text-on-accent p-2 rounded-md disabled:opacity-50 transition-colors"
                            >
                                {planning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                            </button>
                        </div>
                   ) : (
                       <div className="text-center p-4 bg-bg/50 rounded-lg border border-separator text-text-secondary text-sm">
                           任务进行中，请在右侧查看执行计划。
                       </div>
                   )}
               </div>
           </div>

           {/* Right: Plan Display */}
           <div className="flex-1 bg-surface rounded-xl border border-separator flex flex-col overflow-hidden shadow-card">
               <div className="p-4 border-b border-separator bg-surface/70 flex justify-between items-center">
                   <h2 className="font-semibold text-text flex items-center">
                       <Clock className="mr-2 h-4 w-4 text-accent" /> 执行计划
                   </h2>
                   {mission && (
                       <span className="text-xs px-2 py-1 rounded bg-accent/15 text-accent border border-accent/25 font-bold">
                           {MISSION_STATUS_LABELS[mission.mission?.status] || mission.mission?.status}
                       </span>
                   )}
               </div>
               
               <div className="flex-1 overflow-y-auto p-6 space-y-6">
                   {!mission && !planning && (
                       <EmptyState
                         icon={Play}
                         size="sm"
                         title="暂无进行中的任务"
                         description="在左侧输入目标并发送，数字员工会自动拆解执行计划。"
                       />
                   )}

                   {planning && (
                       <div className="space-y-4 animate-pulse">
                           <div className="h-4 bg-surface-2 rounded w-3/4"></div>
                           <div className="h-4 bg-surface-2 rounded w-1/2"></div>
                           <div className="h-32 bg-surface-2 rounded w-full"></div>
                       </div>
                   )}
                   
                   {mission?.tasks?.map((task: any, index: number) => (
                       <div key={task.id} className="relative pl-8 border-l-2 border-separator last:border-0 pb-6">
                           {/* Timeline Dot */}
                           <div className={`absolute left-[-9px] top-0 w-4 h-4 rounded-full border-2 ${
                               task.status === 'completed' ? 'bg-success border-success' : 
                               task.status === 'in_progress' ? 'bg-accent border-accent' : 
                               'bg-surface border-separator'
                           }`}></div>

                           <div className="bg-surface-2/60 border border-separator rounded-lg p-4 hover:border-accent/30 transition-colors">
                               <div className="flex justify-between items-start mb-2">
                                   <h3 className="font-medium text-text">
                                       <span className="text-text-secondary mr-2 tabular-nums">步骤 {task.order_index || index+1}</span>
                                       {task.title || `任务 ${task.id}`}
                                   </h3>
                                   <span className="text-xs bg-surface px-2 py-0.5 rounded text-text-secondary border border-separator">
                                       {task.task_type}
                                   </span>
                               </div>
                               <p className="text-sm text-text-secondary mb-3">{task.description}</p>
                               
                               {/* Output Area (if any) */}
                               {task.result_data && (
                                   <div className="bg-bg p-3 rounded text-xs font-mono text-success border border-separator mt-2">
                                       {JSON.stringify(task.result_data)}
                                   </div>
                               )}
                           </div>
                       </div>
                   ))}
               </div>
           </div>
       </div>
    </div>
  );
}
