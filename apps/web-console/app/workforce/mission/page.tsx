"use client";
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Send, CheckCircle, Clock, ArrowRight, Loader2, Play } from 'lucide-react';
import Link from 'next/link';

const API_URL = "http://localhost:8010";

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
           <Link href="/workforce" className="text-sm text-text-secondary hover:text-white mb-4 inline-block">← Back to Team</Link>
           <h1 className="text-2xl font-bold text-white">Mission Control</h1>
           <p className="text-text-secondary">Assign a high-level goal and watch the agent break it down.</p>
       </div>

       <div className="flex flex-1 gap-8 overflow-hidden">
           {/* Left: Chat / Input */}
           <div className="w-1/3 flex flex-col space-y-4">
               <div className="bg-surface p-6 rounded-xl border border-separator flex-1 flex flex-col">
                   <div className="flex-1 space-y-4 overflow-y-auto mb-4">
                        {/* Agent Greeting */}
                        <div className="flex gap-4">
                            <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-xs text-white font-bold">AI</div>
                            <div className="bg-surface-2 p-3 rounded-lg rounded-tl-none text-sm text-text">
                                Ready for orders. What is my next objective?
                            </div>
                        </div>

                        {/* User Objective */}
                        {mission && (
                            <div className="flex gap-4 flex-row-reverse">
                                <div className="w-8 h-8 rounded-full bg-surface-2 flex items-center justify-center text-xs text-white font-bold">YOU</div>
                                <div className="bg-accent/15 border border-accent/25 p-3 rounded-lg rounded-tr-none text-sm text-white">
                                    {mission.mission?.objective || objective}
                                </div>
                            </div>
                        )}
                   </div>

                   {/* Input Area */}
                   {!mission ? (
                        <div className="relative">
                            <textarea 
                                className="w-full bg-bg border border-separator rounded-lg p-3 pr-12 text-sm focus:ring-2 focus:ring-accent focus:outline-none resize-none h-32"
                                placeholder="E.g. Conduct a competitive analysis of 'GlobalPilot AI' product pricing..."
                                value={objective}
                                onChange={(e) => setObjective(e.target.value)}
                            />
                            <button 
                                onClick={handleStartMission}
                                disabled={planning || !objective.trim()}
                                className="absolute bottom-3 right-3 bg-accent hover:bg-accent-hover p-2 rounded-md disabled:opacity-50 transition-colors"
                            >
                                {planning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                            </button>
                        </div>
                   ) : (
                       <div className="text-center p-4 bg-bg/50 rounded-lg border border-separator text-text-secondary text-sm">
                           Mission in progress. Check the plan on the right.
                       </div>
                   )}
               </div>
           </div>

           {/* Right: Plan Display */}
           <div className="flex-1 bg-surface rounded-xl border border-separator flex flex-col overflow-hidden">
               <div className="p-4 border-b border-separator bg-surface/70 flex justify-between items-center">
                   <h2 className="font-semibold text-white flex items-center">
                       <Clock className="mr-2 h-4 w-4 text-accent" /> Execution Plan
                   </h2>
                   {mission && (
                       <span className="text-xs px-2 py-1 rounded bg-accent/15 text-accent border border-accent/25 uppercase font-bold">
                           {mission.mission?.status}
                       </span>
                   )}
               </div>
               
               <div className="flex-1 overflow-y-auto p-6 space-y-6">
                   {!mission && !planning && (
                       <div className="h-full flex flex-col items-center justify-center text-text-tertiary">
                           <Play className="h-12 w-12 mb-4 opacity-20" />
                           <p>No mission active.</p>
                       </div>
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
                                       <span className="text-text-secondary mr-2">Step {task.order_index || index+1}</span>
                                       {task.title || `Task ${task.id}`}
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
