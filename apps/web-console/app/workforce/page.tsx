"use client";
import React, { useState, useEffect } from 'react';
import { Plus, User, Zap, Bot, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';

const API_URL = "http://localhost:8010";

const ROLE_LABELS: Record<string, string> = {
  strategist: '策略专家',
  executor: '执行专员',
  archivist: '档案管理员',
};

export default function WorkforcePage() {
  const router = useRouter();
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
    <div className="min-h-screen bg-bg text-text p-8">
      <div className="max-w-7xl mx-auto">

        <PageHeader
          title="数字员工大厅"
          description="管理您的 AI 员工团队并分配任务。"
          actions={
            <Link href="/workforce/create">
              <Button>
                <Plus size={16} strokeWidth={1.75} className="mr-1.5" /> 新建数字员工
              </Button>
            </Link>
          }
        />

        {/* Content */}
        {loading ? (
             <EmptyState
               icon={Loader2}
               size="sm"
               title="正在加载数字员工"
               description="正在获取您的团队信息，请稍候…"
             />
        ) : employees.length === 0 ? (
            <EmptyState
              icon={Bot}
              size="lg"
              title="还没有数字员工"
              description="创建您的第一位数字员工，为其配置角色、能力与任务。"
              actionLabel="新建数字员工"
              onAction={() => router.push('/workforce/create')}
            />
        ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Employee Cards */}
                {employees.map((emp: any) => (
                <div key={emp.id} className="bg-surface border border-separator rounded-xl overflow-hidden hover:bg-surface-2 transition-all group shadow-card">
                    <div className="p-6">
                        <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-4">
                                <div className="h-12 w-12 rounded-full bg-surface-2 flex items-center justify-center text-accent">
                                    {emp.avatar_url ? (
                                        <img src={emp.avatar_url} alt={emp.name} className="h-full w-full object-cover rounded-full" />
                                    ) : (
                                        <User size={24} strokeWidth={1.75} />
                                    )}
                                </div>
                                <div>
                                    <h3 className="font-bold text-lg text-text group-hover:text-accent transition-colors">{emp.name}</h3>
                                    <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent/10 text-accent">
                                        {ROLE_LABELS[emp.role] || emp.role}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <p className="text-text-secondary text-sm mb-6 h-10 line-clamp-2">
                            {emp.description}
                        </p>

                        <div className="space-y-3">
                            <div className="apple-section-label">核心能力</div>
                            <div className="flex flex-wrap gap-2">
                                {emp.capabilities?.map((cap: string, i: number) => (
                                    <span key={i} className="text-xs bg-surface-2 text-text-secondary px-2.5 py-1 rounded-full">
                                        {cap}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="px-6 py-4 border-t border-separator mt-auto">
                        <Link href={`/workforce/mission?employee_id=${emp.id}`}>
                            <button className="w-full h-10 flex items-center justify-center bg-surface-2 hover:bg-surface-2/70 text-text rounded-md transition-colors text-sm font-medium">
                                <Zap className="mr-2 h-4 w-4 text-warning" strokeWidth={1.75} /> 分配任务
                            </button>
                        </Link>
                    </div>
                </div>
                ))}

                {/* Create New Card (as last item) */}
                <Link href="/workforce/create" className="group block h-full">
                    <div className="h-full bg-surface/60 border-2 border-dashed border-separator rounded-xl flex flex-col items-center justify-center p-8 hover:border-accent/40 hover:bg-surface transition-all cursor-pointer min-h-[300px]">
                        <div className="bg-surface-2 p-4 rounded-full mb-4 group-hover:scale-110 transition-transform">
                            <Plus className="h-6 w-6 text-text-secondary" strokeWidth={1.75} />
                        </div>
                        <h3 className="font-medium text-text">招募新员工</h3>
                        <p className="text-text-secondary text-sm mt-2 text-center">为您的团队添加一位数字员工</p>
                    </div>
                </Link>
            </div>
        )}
      </div>
    </div>
  );
}
