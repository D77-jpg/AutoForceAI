"use client";

import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Plus, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import api from '@/lib/api';
import { expireAuthSession } from '@/lib/auth-session';
import { readBrainStream, type BrainSource } from '@/lib/brain-stream';

type Session = { id: number; title: string };
type Base = { id: number; name: string };
type Message = { role: string; content: string; sources?: BrainSource[] };

export default function KnowledgeBrain() {
  const { token } = useAuth();
  const params = useSearchParams();
  const [query, setQuery] = useState(params.get('query') || '');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [bases, setBases] = useState<Base[]>([]);
  const [kbIds, setKbIds] = useState<number[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState('');
  const [error, setError] = useState('');
  const controller = useRef<AbortController | null>(null);
  const operation = useRef(0);
  const output = useRef<HTMLDivElement>(null);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [history, libraries] = await Promise.all([api.get<Session[]>('/api/v1/brain/sessions'), api.get<{ items: Base[] }>('/api/v1/kb/bases')]);
      setSessions(history.data);
      setBases(libraries.data.items);
    } catch { setError('会话或知识库加载失败，请重试。'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); return () => { operation.current++; controller.current?.abort(); }; }, []);
  useEffect(() => { output.current?.scrollTo({ top: output.current.scrollHeight }); }, [messages, step]);

  async function openSession(id: number) {
    const current = ++operation.current;
    setBusy(true);
    setError('');
    try {
      const { data } = await api.get<{ role: string; content: string; citations?: { id: number; title: string; kb_name?: string }[] }[]>(`/api/v1/brain/sessions/${id}/messages`);
      if (current !== operation.current) return;
      setMessages(data.map(m => ({ ...m, sources: m.citations?.map(s => ({ doc_id: s.id, doc_name: s.title, kb_name: s.kb_name })) })));
      setSessionId(id);
      setStep('已读取保存的会话');
    } catch { if (current === operation.current) setError('历史记录加载失败，请重试。'); }
    finally { if (current === operation.current) setBusy(false); }
  }

  async function send() {
    if (busy || !query.trim() || !token) return;
    const question = query.trim();
    const current = ++operation.current;
    const abort = new AbortController();
    const timeout = setTimeout(() => abort.abort(), 120000);
    controller.current = abort;
    setBusy(true);
    setError('');
    setStep('正在连接模型');
    setQuery('');
    setMessages(previous => [...previous, { role: 'user', content: question }, { role: 'assistant', content: '' }]);
    try {
      const base = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');
      const response = await fetch(`${base}/api/v1/brain/chat`, {
        method: 'POST', signal: abort.signal,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ query: question, session_id: sessionId, ...(kbIds.length ? { kb_ids: kbIds } : {}) }),
      });
      if (response.status === 401) expireAuthSession(token);
      if (!response.ok || !response.body) throw new Error(`请求失败（${response.status}），请检查登录和模型配置。`);
      await readBrainStream(response.body, event => {
        if (current !== operation.current) return;
        if (event.t === 'init' && event.session_id) setSessionId(event.session_id);
        if (event.t === 'step') setStep(event.msg || '');
        if (event.t === 'token' || event.t === 'meta') setMessages(previous => previous.map((m, index) => index === previous.length - 1
          ? { ...m, content: m.content + (event.t === 'token' ? event.chunk || '' : ''), sources: event.sources || m.sources } : m));
      });
      if (current !== operation.current) return;
      setStep('回答已保存');
      try { setSessions((await api.get<Session[]>('/api/v1/brain/sessions')).data); }
      catch { setError('回答已保存，会话列表更新失败，请刷新列表。'); }
    } catch (err) {
      if (current === operation.current) { setError(err instanceof Error ? err.message : '回答失败，请重试。'); setStep('回答未完成'); }
    } finally { clearTimeout(timeout); if (current === operation.current) setBusy(false); }
  }

  return <div className="p-4 md:p-8 space-y-6">
    <PageHeader title="企业知识大脑" description="选择知识库提问，查看引用，并随时恢复已保存的会话。" actions={<Link href="/knowledge" className="inline-flex items-center h-10 rounded-md border border-separator px-4 text-sm hover:bg-surface-2">管理知识文档</Link>} />
    {error && <div role="alert" className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">{error} <button onClick={() => void load()} disabled={busy} className="ml-3 underline">刷新列表</button></div>}
    <div className="grid gap-5 md:grid-cols-[240px_minmax(0,1fr)]">
      <aside className="rounded-xl border border-separator bg-surface p-4 space-y-4">
        <Button disabled={busy} onClick={() => { setSessionId(null); setMessages([]); setStep(''); setError(''); }} className="w-full gap-2"><Plus size={16} />新建对话</Button>
        <h2 className="text-sm font-semibold">历史会话</h2>
        {loading ? <p role="status">正在加载…</p> : sessions.length === 0 ? <p className="text-sm text-text-secondary">暂无保存的会话</p> : <ul className="space-y-1 max-h-80 overflow-y-auto">{sessions.map(s => <li key={s.id}><button disabled={busy} onClick={() => void openSession(s.id)} className={`w-full rounded-lg p-3 text-left text-sm break-words ${sessionId === s.id ? 'bg-accent/10 text-accent' : 'hover:bg-surface-2'}`}>{s.title}</button></li>)}</ul>}
        <h2 className="text-sm font-semibold">知识范围</h2>
        <p className="text-xs text-text-secondary">不选择时检索组织公开知识库；无匹配资料时会使用模型通用知识。</p>
        {bases.map(kb => <label key={kb.id} className="flex gap-2 items-center py-2 text-sm"><input type="checkbox" disabled={busy} checked={kbIds.includes(kb.id)} onChange={e => setKbIds(previous => e.target.checked ? [...previous, kb.id] : previous.filter(id => id !== kb.id))} />{kb.name}</label>)}
        {!loading && bases.length === 0 && <p className="text-sm text-text-secondary">尚未上传知识资料。</p>}
      </aside>
      <section className="rounded-xl border border-separator bg-surface p-4 flex flex-col min-w-0">
        <div ref={output} className="min-h-72 max-h-[60vh] overflow-y-auto space-y-5 p-2" aria-label="对话记录">
          {messages.length === 0 && <p className="text-text-secondary">输入问题开始对话。回答的引用会显示在对应消息下方。</p>}
          {messages.map((message, index) => <article key={index} className={`rounded-lg p-4 ${message.role === 'user' ? 'bg-accent/10' : 'bg-surface-2'}`}>
            <p className="text-xs font-semibold mb-2">{message.role === 'user' ? '我' : '知识助手'}</p>
            <div className="prose prose-sm dark:prose-invert max-w-none break-words"><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || (busy ? '正在生成…' : '没有完成回答')}</ReactMarkdown></div>
            {message.sources && message.sources.length > 0 && <ul className="mt-4 border-t border-separator pt-3 text-xs text-text-secondary space-y-1">{message.sources.map(source => <li key={source.doc_id}>引用：{source.doc_name}{source.kb_name ? ` · ${source.kb_name}` : ''}</li>)}</ul>}
          </article>)}
        </div>
        <p role="status" className="min-h-7 text-xs text-text-secondary py-2">{step}</p>
        <form onSubmit={e => { e.preventDefault(); void send(); }} className="space-y-3 border-t border-separator pt-4">
          <label htmlFor="brain-question" className="block text-sm font-medium">问题</label>
          <textarea id="brain-question" maxLength={8000} rows={3} value={query} disabled={busy} onChange={e => setQuery(e.target.value)} className="w-full rounded-lg bg-bg border border-separator p-3 text-text" placeholder="例如：根据产品资料，交货期和最小起订量是多少？" />
          <Button type="submit" disabled={busy || loading || !query.trim()} className="gap-2">{busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}{busy ? '正在处理' : '发送问题'}</Button>
        </form>
      </section>
    </div>
  </div>;
}
