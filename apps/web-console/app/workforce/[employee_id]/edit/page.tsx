"use client";

import { useEffect, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { PageHeader } from '@/components/PageHeader';
import api from '@/lib/api';
import { errorMessage, fetchProjects, projectQuery, type Employee, type WorkforceProject } from '../../workforce-api';

type Editable = Pick<Employee, 'name' | 'description' | 'system_prompt' | 'max_steps' | 'timeout_seconds' | 'max_cost_usd'>;

export default function EditEmployeePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [project, setProject] = useState<WorkforceProject | null>(null);
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [form, setForm] = useState<Editable | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const projectId = searchParams.get('project_id');
  const employeeId = params.employee_id;

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const projects = await fetchProjects();
        const selected = projects.find(item => String(item.id) === projectId);
        if (!selected) throw new Error('未选择授权项目或当前项目不可访问，请从员工大厅重新选择。');
        if (typeof employeeId !== 'string' || !/^\d+$/.test(employeeId)) throw new Error('员工 ID 无效。');
        const { data } = await api.get<Employee>(`/agents/${selected.id}/employees/${employeeId}`);
        if (data.project_id !== selected.id) throw new Error('员工不属于当前项目。');
        if (!active) return;
        setProject(selected);
        setEmployee(data);
        setForm({ name: data.name, description: data.description || '', system_prompt: data.system_prompt || '', max_steps: data.max_steps, timeout_seconds: data.timeout_seconds, max_cost_usd: data.max_cost_usd });
      } catch (err) { if (active) setError(`无法加载员工：${errorMessage(err)}`); }
      finally { if (active) setLoading(false); }
    }
    void load();
    return () => { active = false; };
  }, [projectId, employeeId]);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!project || !employee || !form) return;
    if (!form.name.trim()) return setError('员工姓名不能为空。');
    setSaving(true);
    setError('');
    try {
      // PATCH only fields that changed; preserve prompt version and the immutable template snapshot otherwise.
      const changes: Partial<Editable> = {};
      if (form.name.trim() !== employee.name) changes.name = form.name.trim();
      if (form.description !== employee.description) changes.description = form.description;
      if (form.system_prompt !== employee.system_prompt) changes.system_prompt = form.system_prompt;
      if (form.max_steps !== employee.max_steps) changes.max_steps = form.max_steps;
      if (form.timeout_seconds !== employee.timeout_seconds) changes.timeout_seconds = form.timeout_seconds;
      if (form.max_cost_usd !== employee.max_cost_usd) changes.max_cost_usd = form.max_cost_usd;
      if (Object.keys(changes).length) await api.patch(`/agents/${project.id}/employees/${employee.id}`, changes);
      router.push(`/workforce${projectQuery(project.id)}`);
    } catch (err) { setError(`保存失败：${errorMessage(err)}`); }
    finally { setSaving(false); }
  }

  return <div className="min-h-screen bg-bg text-text p-6"><div className="max-w-3xl mx-auto space-y-6">
    <Link href={`/workforce${project ? projectQuery(project.id) : ''}`} className="text-sm text-text-secondary hover:text-accent">← 返回员工大厅</Link>
    <PageHeader title="编辑数字员工" description="仅编辑当前员工的独立配置；岗位模板升级不会自动覆盖已有员工。" />
    {loading ? <p role="status">正在加载员工配置…</p> : error && !employee ? <p role="alert" className="text-red-600">{error}</p> : employee && form && <>
      <div className="rounded-xl border border-separator bg-surface p-5 space-y-2 text-sm">
        <p>所属项目：{project?.name} · 角色：{employee.role}</p>
        <p>来源模板：{employee.template_key || '未关联'} · 模板版本：{employee.template_version || '未记录'} · Prompt 版本：{employee.prompt_version || '未记录'}</p>
        <p>组织 / 项目范围：{employee.data_scope ? `组织：${employee.data_scope.organization}；项目：${employee.data_scope.project}；跨项目：${employee.data_scope.cross_project ? '允许' : '禁止'}` : '未记录'}；工具白名单：{employee.allowed_tools?.join('、') || '无可运行工具'}</p>
        <p>外部写入/发送：{employee.requires_human_approval_for_external_actions ? '需人工审核确认' : '按员工配置执行'}</p>
        <p className="text-text-secondary">工具白名单、组织/项目边界与模板来源不可在此页更改；不会将尚未可用的发送邮件或浏览器自动化列为可运行能力。</p>
      </div>
      <form onSubmit={save} className="rounded-xl border border-separator bg-surface p-5 space-y-4">
        {error && <p role="alert" className="text-red-600">{error}</p>}
        <Field label="员工姓名" value={form.name} onChange={value => setForm({ ...form, name: value })} />
        <Field label="职责描述" value={form.description} onChange={value => setForm({ ...form, description: value })} />
        <label className="block text-sm font-semibold">角色指令<textarea value={form.system_prompt} onChange={event => setForm({ ...form, system_prompt: event.target.value })} rows={8} className="block mt-2 w-full rounded-lg border border-separator bg-bg p-3 text-text" /></label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <NumberField label="最大步骤" value={form.max_steps} min={1} onChange={value => setForm({ ...form, max_steps: value })} />
          <NumberField label="超时（秒）" value={form.timeout_seconds} min={1} onChange={value => setForm({ ...form, timeout_seconds: value })} />
          <NumberField label="费用预算（美元）" value={form.max_cost_usd} min={0} step="0.01" onChange={value => setForm({ ...form, max_cost_usd: value })} />
        </div>
        <button disabled={saving} className="rounded-lg bg-accent px-5 py-3 text-on-accent disabled:opacity-50">{saving ? '保存中…' : '保存员工配置'}</button>
      </form>
    </>}
  </div></div>;
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="block text-sm font-semibold">{label}<input value={value} onChange={event => onChange(event.target.value)} className="block mt-2 w-full rounded-lg border border-separator bg-bg p-3 text-text" /></label>;
}
function NumberField({ label, value, min, step, onChange }: { label: string; value?: number; min: number; step?: string; onChange: (value: number) => void }) {
  return <label className="block text-sm font-semibold">{label}<input type="number" required min={min} step={step || '1'} value={value ?? ''} onChange={event => onChange(Number(event.target.value))} className="block mt-2 w-full rounded-lg border border-separator bg-bg p-3 text-text" /></label>;
}
