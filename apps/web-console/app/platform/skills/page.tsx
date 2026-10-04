"use client";

import { useEffect, useState } from 'react';
import { RefreshCw, Terminal } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';

type Skill = { name: string; description: string; tags: string[]; parameters: { name: string; type: string; required: boolean }[] };
type Capability = { id: string; name: string; configured: boolean; detail: string };

export default function SkillSettingsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  async function refresh() {
    setLoading(true);
    setError('');
    setSkills([]);
    setCapabilities([]);
    const [registry, runtime] = await Promise.allSettled([
      api.get<{ skills: Skill[] }>('/api/v1/platform/skills'),
      api.get<{ items: Capability[] }>('/api/v1/platform/capabilities'),
    ]);
    if (registry.status === 'fulfilled') setSkills(registry.value.data.skills);
    if (runtime.status === 'fulfilled') setCapabilities(runtime.value.data.items);
    if (registry.status === 'rejected' || runtime.status === 'rejected') setError('部分能力状态读取失败，请确认管理员权限和后端连接后重试。');
    setLoading(false);
  }
  useEffect(() => { void refresh(); }, []);
  return <div className="p-4 md:p-8 space-y-6">
    <PageHeader title="技能工具箱" description="查看实际注册技能与服务端配置。注册技能或配置密钥不代表自动执行已通过验收。" actions={<Button variant="outline" disabled={loading} onClick={() => void refresh()} className="gap-2"><RefreshCw size={16} />刷新状态</Button>} />
    {loading && <p role="status">正在读取技能状态…</p>}
    {error && <p role="alert" className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">{error}</p>}
    <Tabs defaultValue="library">
      <TabsList className="mb-5"><TabsTrigger value="library">注册技能</TabsTrigger><TabsTrigger value="config">基础能力连接状态</TabsTrigger></TabsList>
      <TabsContent value="library">
        {!loading && skills.length === 0 && <p className="text-text-secondary">没有可显示的注册技能。</p>}
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{skills.map(skill => <article key={skill.name} className="glass-panel p-5 space-y-3">
          <h2 className="font-semibold flex items-center gap-2"><Terminal size={18} />{skill.name}</h2>
          <p className="text-sm text-text-secondary">{skill.description}</p>
          {skill.parameters.length > 0 && <ul className="text-xs text-text-secondary space-y-2">{skill.parameters.map(parameter => <li key={parameter.name}>{parameter.name}：{parameter.type}{parameter.required ? '（必填）' : ''}</li>)}</ul>}
          <div className="flex flex-wrap gap-2">{skill.tags.map(tag => <span key={tag} className="rounded-full bg-surface-2 px-2 py-1 text-xs text-text-secondary">{tag}</span>)}</div>
        </article>)}</div>
      </TabsContent>
      <TabsContent value="config" className="space-y-4">
        <p className="text-sm text-text-secondary">以下状态读取服务端当前配置。接入设置需由管理员写入服务端配置并重启服务，密钥不会回显到页面。</p>
        {capabilities.map(capability => <article key={capability.id} className="glass-panel p-5 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">{capability.name}</h2><span className={`text-sm ${capability.configured ? 'text-text-secondary' : 'text-warning'}`}>{capability.configured ? '已配置，待实际验收' : '缺少配置'}</span></div>
          <p className="text-sm text-text-secondary">{capability.detail}</p>
        </article>)}
      </TabsContent>
    </Tabs>
  </div>;
}
