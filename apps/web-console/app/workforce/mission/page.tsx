"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import api from '@/lib/api';
import { PageHeader } from '@/components/PageHeader';

/** H-06 is a configuration-only rollout: no metered/cancellable LLM planner exists yet. */
export default function MissionPage() {
  const searchParams = useSearchParams();
  const projectId = searchParams.get('project_id');
  const employeeId = searchParams.get('employee_id');
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setName('');
    if (!projectId || !employeeId || !/^\d+$/.test(projectId) || !/^\d+$/.test(employeeId)) {
      setError('缺少有效项目或员工 ID，请从数字员工大厅进入。');
      return;
    }
    setError('');
    void api.get(`/agents/${projectId}/employees/${employeeId}`)
      .then(({ data }) => { if (active) setName(data.name); })
      .catch(() => { if (active) setError('员工不存在或无权访问。'); });
    return () => { active = false; };
  }, [employeeId, projectId]);

  return <main className="min-h-screen bg-bg text-text p-8">
    <div className="max-w-4xl mx-auto space-y-6">
      <Link href="/workforce" className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text"><ArrowLeft size={16} />返回员工大厅</Link>
      <PageHeader title="任务规划暂不可用" description="H-06 岗位模板已可创建、审阅和编辑，但数字员工没有已验证的自动执行工具。" />
      {error ? <p role="alert" className="rounded-lg border border-red-500/40 p-4 text-red-600">{error}</p> : null}
      {name ? <p>员工：{name}（项目 {projectId}）</p> : null}
      <section className="rounded-xl border border-separator bg-surface p-6 space-y-3 text-text-secondary">
        <h2 className="font-semibold text-text">安全边界</h2>
        <p>当前模型适配器无法强制执行超时及费用预算，因此服务端禁止实时规划；此页面不会创建任务、发信或写入外部系统。</p>
        <p>待后续完成可信的有界模型调用及独立人工审核执行通道后，才能开放任务规划。</p>
      </section>
    </div>
  </main>;
}
