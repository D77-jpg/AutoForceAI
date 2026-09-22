"use client";
import React, { useState, useEffect } from 'react';
import { Plus, User, Zap, Briefcase } from 'lucide-react';
import Link from 'next/link';

const API_URL = "http://localhost:8010";

export default function WorkforcePage() {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Hardcode some employees for demo if API fails or is empty, 
    // but try to fetch first.
    const fetchEmployees = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_URL}/agents/1/employees`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
              setEmployees(data);
          } else {
              // Fallback to "Create One" state
              setEmployees([]);
          }
        }
      } catch (e) {
        console.error("Failed to fetch employees", e);
      } finally {
        setLoading(false);
      }
    };
    fetchEmployees();
  }, []);

  return (
    <div className="min-h-screen bg-black text-[#f5f5f7] p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex justify-between items-center border-b border-white/8 pb-6">
          <div>
            <h1 className="text-[32px] font-semibold tracking-tight text-white">数字员工大厅</h1>
            <p className="text-[15px] text-[#86868b] mt-2">管理您的 AI 员工团队并分配任务。</p>
          </div>
          <Link href="/workforce/create">
            <button className="flex items-center gap-2 bg-[#0071e3] hover:bg-[#0077ed] text-white px-5 py-2.5 rounded-full font-medium transition-colors">
              <Plus size={18} />
              <span>新建员工</span>
            </button>
          </Link>
        </div>

        {/* Content */}
        {loading ? (
             <div className="text-center py-20 text-slate-500">Loading workforce...</div>
        ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Employee Cards */}
                {employees.map((emp: any) => (
                <div key={emp.id} className="bg-[#1c1c1e] border border-white/8 rounded-[20px] overflow-hidden hover:bg-[#2c2c2e] transition-all group">
                    <div className="p-6">
                        <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-4">
                                <div className="h-12 w-12 rounded-full bg-[#2c2c2e] flex items-center justify-center text-[#0a84ff]">
                                    {emp.avatar_url ? (
                                        <img src={emp.avatar_url} alt={emp.name} className="h-full w-full object-cover rounded-full" />
                                    ) : (
                                        <User size={24} />
                                    )}
                                </div>
                                <div>
                                    <h3 className="font-bold text-lg text-white group-hover:text-[#0a84ff] transition-colors">{emp.name}</h3>
                                    <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium bg-[#0a84ff]/12 text-[#64d2ff] capitalize">
                                        {emp.role}
                                    </span>
                                </div>
                            </div>
                        </div>
                        
                        <p className="text-slate-400 text-sm mb-6 h-10 line-clamp-2">
                            {emp.description}
                        </p>

                        <div className="space-y-3">
                            <div className="text-[11px] font-semibold text-[#6e6e73] uppercase tracking-[0.12em]">Capabilities</div>
                            <div className="flex flex-wrap gap-2">
                                {emp.capabilities?.map((cap: string, i: number) => (
                                    <span key={i} className="text-xs bg-[#2c2c2e] text-[#d2d2d7] px-2.5 py-1 rounded-full">
                                        {cap}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                    
                    <div className="px-6 py-4 border-t border-white/8 mt-auto">
                        <Link href={`/workforce/mission?employee_id=${emp.id}`}>
                            <button className="w-full flex items-center justify-center bg-[#2c2c2e] hover:bg-[#3a3a3c] text-white py-2.5 rounded-full transition-colors text-sm font-medium">
                                <Zap className="mr-2 h-4 w-4 text-[#ffd60a]" /> Assign Mission
                            </button>
                        </Link>
                    </div>
                </div>
                ))}

                {/* Create New Card (if empty or as last item) */}
                <Link href="/workforce/create" className="group block h-full">
                    <div className="h-full bg-[#1c1c1e]/60 border-2 border-dashed border-white/10 rounded-[20px] flex flex-col items-center justify-center p-8 hover:border-white/20 hover:bg-[#1c1c1e] transition-all cursor-pointer min-h-[300px]">
                        <div className="bg-[#2c2c2e] p-4 rounded-full mb-4 group-hover:scale-110 transition-transform">
                            <Plus className="h-6 w-6 text-[#86868b]" />
                        </div>
                        <h3 className="font-medium text-[#f5f5f7]">Recruit New Employee</h3>
                        <p className="text-[#86868b] text-sm mt-2 text-center">Add a new digital worker to your team</p>
                    </div>
                </Link>
            </div>
        )}
      </div>
    </div>
  );
}
