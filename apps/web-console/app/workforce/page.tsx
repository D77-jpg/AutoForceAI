"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Plus, User, Zap, Bot, Loader2, Pencil } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import api from '@/lib/api';
import { errorMessage, fetchProjects, projectQuery, type Employee, type WorkforceProject } from './workforce-api';

export default function WorkforcePage() {
  const searchParams = useSearchParams();
  const [projects, setProjects] = useState<WorkforceProject[]>([]);
  const [projectId, setProjectId] = useState('');
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [employeesLoading, setEmployeesLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetchProjects().then(data => {
      if (!active) return;
      setProjects(data);
      const requested = searchParams.get('project_id');
      if (requested && data.some(project => String(project.id) === requested)) setProjectId(requested);
      else if (requested) setError('当前项目不可访问，请重新选择授权项目。');
    }).catch(err => { if (active) setError(`项目加载失败：${errorMessage(err)}`); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [searchParams]);

  useEffect(() => {
    if (!projectId || !projects.some(project => String(project.id) === projectId)) return;
    let active = true;
    setEmployeesLoading(true);
    api.get<Employee[]>(`/agents/${projectId}/employees`).then(({ data }) => {
      if (!active) return;
      if (!Array.isArray(data)) throw new Error('员工列表响应格式不正确');
      setEmployees(data);
      setError('');
    }).catch(err => { if (active) { setEmployees([]); setError(`员工加载失败：${errorMessage(err)}`); } })
      .finally(() => { if (active) setEmployeesLoading(false); });
    return () => { active = false; };
  }, [projectId, projects]);

  function selectProject(id: string) {
    setEmployees([]);
    setProjectId(id);
    setError('');
    setEmployeesLoading(Boolean(id));
  }

  return <div className="min-h-screen bg-bg text-text p-8"><div className="max-w-7xl mx-auto space-y-6">
    <PageHeader title="数字员工大厅" description="选择授权项目，查看数字员工；从五类岗位模板创建并独立编辑。" actions={
      <Link href={`/workforce/create${projectId ? projectQuery(Number(projectId)) : ''}`}><Button><Plus size={16} className="mr-1.5" /> 从模板创建</Button></Link>
    } />
    {loading ? <EmptyState icon={Loader2} size="sm" title="正在加载授权项目" description="请稍候…" /> : <>
      {error && <p role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-600">{error}</p>}
      {projects.length === 0 ? <p className="text-text-secondary">没有可访问的项目，无法加载数字员工。</p> : <div className="rounded-xl border border-separator bg-surface p-4">
        <label htmlFor="workforce-project" className="block mb-2 text-sm font-semibold">当前项目（必选）</label>
        <select id="workforce-project" className="w-full max-w-md rounded-lg border border-separator bg-bg p-3 text-text" value={projectId} onChange={event => selectProject(event.target.value)}>
          <option value="">请选择项目</option>
          {projects.map(project => <option key={project.id} value={project.id}>{project.name}（组织 {project.organization_id} / 项目 {project.id}）</option>)}
        </select>
      </div>}
      {!projectId ? <p className="text-text-secondary">请选择项目后查看数字员工，多个项目不会自动选择。</p> : employeesLoading ? <EmptyState icon={Loader2} size="sm" title="正在加载数字员工" description="请稍候…" /> : error ? null : employees.length === 0 ?
        <EmptyState icon={Bot} size="lg" title="还没有数字员工" description="请从岗位模板创建第一位员工。" /> :
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">{employees.map(employee => <div key={employee.id} className="bg-surface border border-separator rounded-xl overflow-hidden shadow-card">
          <div className="p-6 space-y-4"><div className="flex items-center gap-3"><User size={24} className="text-accent" /><div><h3 className="font-bold text-lg">{employee.name}</h3><span className="text-xs text-text-secondary">{employee.role}</span></div></div>
            <p className="text-text-secondary text-sm">{employee.description}</p>
            {employee.template_key && <p className="text-xs text-text-secondary">模板 {employee.template_key} · v{employee.template_version || '未记录'}（已创建员工不会被模板升级覆盖）</p>}
            <div className="flex flex-wrap gap-2">{(employee.allowed_tools || []).map(tool => <span key={tool} className="text-xs bg-surface-2 px-2 py-1 rounded-full">{tool}</span>)}</div>
          </div>
          <div className="px-6 py-4 border-t border-separator flex gap-2">
            <Link className="flex-1 rounded-md bg-surface-2 p-2 text-center text-sm" href={`/workforce/${employee.id}/edit${projectQuery(Number(projectId))}`}><Pencil size={14} className="inline mr-1" />编辑配置</Link>
            <span title="缺少可强制预算和超时的模型适配器" className="flex-1 rounded-md bg-surface-2 p-2 text-center text-sm text-text-secondary" aria-disabled="true"><Zap size={14} className="inline mr-1" />规划暂不可用</span>
          </div>
        </div>)}</div>
    }</>}
  </div></div>;
}
