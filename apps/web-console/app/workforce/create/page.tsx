"use client";

import { useEffect, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import api from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { errorMessage, fetchProjects, projectQuery, type RoleTemplate, type WorkforceProject } from '../workforce-api';

export default function CreateEmployeePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { showToast } = useToast();
  const [projects, setProjects] = useState<WorkforceProject[]>([]);
  const [projectId, setProjectId] = useState('');
  const [templates, setTemplates] = useState<RoleTemplate[]>([]);
  const [templateKey, setTemplateKey] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const selected = templates.find(template => template.key === templateKey);

  useEffect(() => {
    let active = true;
    Promise.all([fetchProjects(), api.get<RoleTemplate[]>('/agents/role-templates')])
      .then(([availableProjects, response]) => {
        if (!active) return;
        if (!Array.isArray(response.data)) throw new Error('岗位模板响应格式不正确');
        setProjects(availableProjects);
        setTemplates(response.data);
        const requested = searchParams.get('project_id');
        if (requested && availableProjects.some(project => String(project.id) === requested)) setProjectId(requested);
        else if (requested) setError('当前项目不可访问，请重新选择授权项目。');
      })
      .catch(err => { if (active) setError(`无法加载项目或岗位模板：${errorMessage(err)}`); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [searchParams]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!projects.some(project => String(project.id) === projectId)) return setError('请先选择可访问的真实项目。');
    if (!selected) return setError('请选择一个有效的岗位模板。');
    setSaving(true);
    setError('');
    try {
      await api.post(`/agents/${projectId}/employees/from-template`, {
        template_key: selected.key,
        ...(name.trim() ? { name: name.trim() } : {}),
      });
      showToast('数字员工创建成功；后续模板升级不会自动覆盖其配置。', 'success');
      router.push(`/workforce${projectQuery(Number(projectId))}`);
    } catch (err) {
      setError(`创建失败：${errorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  return <div className="min-h-screen bg-bg text-text p-6"><div className="max-w-6xl mx-auto space-y-6">
    <Link href={`/workforce${projectId ? projectQuery(Number(projectId)) : ''}`} className="inline-flex gap-2 items-center text-sm text-text-secondary hover:text-accent"><ArrowLeft size={16} /> 返回员工大厅</Link>
    <PageHeader title="从岗位模板创建" description="选定授权项目与外贸岗位；创建后可单独编辑员工，模板升级不会覆盖现有配置。" />
    {loading ? <p role="status" className="flex gap-2 items-center"><Loader2 className="animate-spin" size={18} /> 正在加载授权项目和模板…</p> : <>
      {error && <p role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-600">{error}</p>}
      {projects.length === 0 && <p role="alert" className="text-text-secondary">没有可访问的项目，无法创建员工。</p>}
      {templates.length === 0 && <p role="alert" className="text-text-secondary">暂无可用岗位模板，无法创建员工。</p>}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-xl border border-separator bg-surface p-5 space-y-4">
          <label className="block text-sm font-semibold" htmlFor="workforce-project">所属项目（必选）</label>
          <select id="workforce-project" value={projectId} onChange={event => { setProjectId(event.target.value); setError(''); }} className="w-full rounded-lg border border-separator bg-bg p-3 text-text" required>
            <option value="">请选择项目</option>
            {projects.map(project => <option key={project.id} value={project.id}>{project.name}（组织 {project.organization_id} / 项目 {project.id}）</option>)}
          </select>
          <label className="block text-sm font-semibold" htmlFor="employee-name">员工姓名（可选）</label>
          <input id="employee-name" value={name} onChange={event => setName(event.target.value)} placeholder="留空则使用模板默认名称" className="w-full rounded-lg border border-separator bg-bg p-3 text-text" />
        </div>
        <div><h2 className="font-semibold mb-3">选择岗位模板</h2><div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {templates.map(template => <button type="button" key={template.key} onClick={() => { setTemplateKey(template.key); setError(''); }} aria-pressed={template.key === templateKey} className={`text-left rounded-xl border p-5 bg-surface hover:border-accent ${template.key === templateKey ? 'border-accent ring-1 ring-accent' : 'border-separator'}`}>
            <strong>{template.name}</strong><span className="ml-2 text-xs text-text-secondary">v{template.template_version}</span>
            <p className="mt-2 text-sm text-text-secondary">{template.description}</p>
          </button>)}
        </div></div>
        {selected && <section className="rounded-xl border border-separator bg-surface p-5 space-y-4" aria-label="模板详情">
          <h2 className="font-semibold text-lg">{selected.name} · 模板详情</h2>
          <Detail label="角色目标" value={selected.goal} />
          <Detail label="禁止事项" value={selected.prohibitions.length ? selected.prohibitions.join('；') : '无额外事项'} />
          <Detail label="工具白名单" value={selected.allowed_tools.length ? selected.allowed_tools.join('、') : '无可运行工具'} />
          <Detail label="尚不可运行的能力" value={selected.unavailable_capabilities.length ? selected.unavailable_capabilities.join('、') : '无'} />
          <Detail label="组织 / 项目数据范围" value={`组织：${selected.data_scope.organization}；项目：${selected.data_scope.project}；跨项目：${selected.data_scope.cross_project ? '允许' : '禁止'}`} />
          <Detail label="执行上限" value={`${selected.max_steps} 步 · ${selected.timeout_seconds} 秒 · $${selected.max_cost_usd} 费用预算`} />
          <Detail label="外部写入与发送" value={selected.requires_human_approval_for_external_actions ? '需要人工审核确认；模板本身不授权自动执行' : '按模板策略执行'} />
          <Detail label="版本" value={`模板 ${selected.template_version} · Prompt ${selected.prompt_version}`} />
        </section>}
        <button type="submit" disabled={saving || loading || !projectId || !selected} className="rounded-lg bg-accent px-5 py-3 font-medium text-on-accent disabled:opacity-50">{saving ? '创建中…' : '从模板创建员工'}</button>
      </form>
    </>}
  </div></div>;
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div className="grid gap-1 text-sm sm:grid-cols-[180px_1fr]"><span className="text-text-secondary">{label}</span><span className="whitespace-pre-wrap break-words">{value}</span></div>;
}
