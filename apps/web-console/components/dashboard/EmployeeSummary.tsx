"use client";

import Link from 'next/link';
import type { DashboardEmployee } from '@/lib/dashboard-types';

export default function EmployeeSummary({ employees, loading, unavailable }: { employees: DashboardEmployee[]; loading: boolean; unavailable: boolean }) {
  return <section aria-label="数字员工配置" className="bg-surface border border-separator rounded-xl shadow-card p-5 space-y-4">
    <div className="flex gap-3 items-center justify-between"><h2 className="text-sm font-semibold">数字员工配置</h2><Link href="/workforce" className="text-sm text-accent underline">管理项目与员工</Link></div>
    <p className="text-xs text-text-secondary">以下为已保存的员工配置；自动执行尚未完成验收。</p>
    {loading ? <p role="status">正在读取员工配置…</p> : unavailable ? <p role="alert" className="text-warning">员工配置读取失败，请到数字员工大厅重试。</p> : employees.length === 0 ? <p className="text-sm text-text-secondary">还没有数字员工。请先创建项目，再从岗位模板创建员工。</p> :
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{employees.map(employee => <div key={`${employee.project_id}-${employee.id}`} className="border border-separator rounded-lg p-4 space-y-2">
        <h3 className="font-medium">{employee.name}</h3><p className="text-xs text-text-secondary">{employee.project_name} · {employee.role}</p><p className="text-sm text-text-secondary">{employee.description}</p>
        <Link href={`/workforce/${employee.id}/edit?project_id=${employee.project_id}`} className="inline-block text-sm text-accent underline py-2">编辑配置</Link>
      </div>)}</div>}
  </section>;
}
