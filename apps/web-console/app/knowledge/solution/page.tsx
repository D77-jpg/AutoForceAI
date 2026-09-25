"use client";

import { useEffect, useRef, useState } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import {
  ContextItem, ContextResult, DraftPage, Generation, OutlineResult, PageContent, Settings,
  editOutline, generateOutline, generatePageContent, generatePpt, listKnowledgeBases,
  movePage, renumberPages, retrieveContext,
} from '@/lib/solution-api';

const field = 'w-full rounded-md border border-separator bg-bg p-2 text-text disabled:opacity-50';
const panel = 'rounded-xl border border-separator bg-surface p-5 space-y-4';
const message = (error: unknown) => error instanceof Error ? error.message : '操作失败，请重试。';

function Sources({ items }: { items: ContextItem[] }) {
  if (!items.length) return <p className="text-sm text-text-secondary">没有知识库检索结果，将使用通用知识；请核验生成内容。</p>;
  return <ul className="space-y-2">{items.map((item, index) => <li key={`${item.doc_id}-${index}`} className="rounded-md border border-separator p-3 text-sm">
    <div className="font-medium break-words">来源：{item.doc_name}（文档 {item.doc_id}） · 相关度：{Number.isFinite(item.score) ? item.score.toFixed(3) : '未提供'}</div>
    <details className="mt-2"><summary className="cursor-pointer">查看检索片段</summary><p className="mt-2 whitespace-pre-wrap break-words">{item.content}</p></details>
  </li>)}</ul>;
}
function GenerationStatus({ result }: { result: Generation }) {
  return <div className={`rounded-md border p-3 text-sm ${result.generation_mode === 'fallback' ? 'border-amber-500 bg-amber-500/10 text-amber-700 dark:text-amber-300' : 'border-separator text-text-secondary'}`}>
    <strong>{result.generation_mode === 'fallback' ? '模板回退（非模型生成）' : '模型生成'}</strong>
    {result.generation_mode === 'fallback' && <p>原因：{result.fallback_reason || '服务未提供具体原因'}</p>}
    <p>{result.knowledge_used ? '本次使用了知识库内容。' : '本次未使用知识库内容，基于通用知识/模板，请核验。'}</p>
  </div>;
}

export default function Page() {
  const [settings, setSettings] = useState<Settings>({ topic: '', target_audience: '', style: '商务', kb_ids: [] });
  const [bases, setBases] = useState<{ id: number; name: string }[]>([]);
  const [loadingBases, setLoadingBases] = useState(true);
  const [basesError, setBasesError] = useState('');
  const [basesAttempt, setBasesAttempt] = useState(0);
  const [context, setContext] = useState<ContextResult | null>(null);
  const [outline, setOutline] = useState<OutlineResult | null>(null);
  const [pages, setPages] = useState<DraftPage[]>([]);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [download, setDownload] = useState('');
  const downloadRef = useRef('');
  const active = useRef<AbortController | null>(null);
  const version = useRef(0);
  const nextId = useRef(0);
  const locked = !!busy || loadingBases;
  const clearDownload = () => {
    if (downloadRef.current) URL.revokeObjectURL(downloadRef.current);
    downloadRef.current = '';
    setDownload('');
  };
  useEffect(() => {
    const controller = new AbortController();
    setLoadingBases(true); setBasesError('');
    listKnowledgeBases({ signal: controller.signal }).then(result => {
      if (!controller.signal.aborted) setBases(result.items);
    }).catch(err => { if (!controller.signal.aborted) setBasesError(message(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoadingBases(false); });
    return () => controller.abort();
  }, [basesAttempt]);
  useEffect(() => () => {
    version.current++;
    active.current?.abort();
    active.current = null;
    if (downloadRef.current) URL.revokeObjectURL(downloadRef.current);
  }, []);

  function changeSettings(patch: Partial<Settings>) {
    if (active.current || loadingBases) return;
    version.current++;
    setSettings(previous => ({ ...previous, ...patch }));
    setContext(null); setOutline(null); setPages([]); clearDownload(); setError(''); setNotice('');
  }
  function changePages(next: DraftPage[]) {
    if (active.current) return;
    setPages(renumberPages(next)); clearDownload(); setNotice(''); setError('');
  }
  async function run(label: string, action: (signal: AbortSignal, valid: () => boolean) => Promise<void>) {
    if (active.current || loadingBases) return;
    const controller = new AbortController();
    active.current = controller;
    const ticket = ++version.current;
    const valid = () => ticket === version.current && !controller.signal.aborted;
    setBusy(label); setError(''); setNotice('');
    try { await action(controller.signal, valid); }
    catch (err) { if (valid()) setError(message(err)); }
    finally { if (valid()) { active.current = null; setBusy(''); } }
  }
  function retrieve() {
    if (!settings.topic.trim()) { setError('主题不能为空'); return; }
    void run('正在检索知识库…', async (signal, valid) => {
      setContext(null); setOutline(null); setPages([]); clearDownload();
      const result = await retrieveContext(settings, { signal });
      if (valid()) { setContext(result); setNotice('检索已完成。请查看来源和真实检索日志，再生成大纲。'); }
    });
  }
  function createOutline() {
    if (!context || !settings.topic.trim()) return;
    void run('正在生成大纲…', async (signal, valid) => {
      clearDownload(); setOutline(null); setPages([]);
      const result = await generateOutline(settings, { signal });
      if (valid()) {
        setOutline(result);
        setPages(renumberPages(result.pages.map(page => ({ id: String(++nextId.current), outline: page }))));
        if (!result.pages.length) setError('服务返回空大纲，请重试或手动添加页面。');
        else if (result.generation_mode === 'fallback') setNotice('模型未生成大纲，已载入通用结构模板；请编辑并核验各页内容。');
      }
    });
  }
  function createContent(ids: string[]) {
    const selected = pages.filter(page => ids.includes(page.id));
    if (!selected.length || selected.some(page => !page.outline.title.trim())) { setError('页面标题不能为空'); return; }
    void run('正在生成页面内容…', async (signal, valid) => {
      clearDownload();
      let failed = 0;
      let fallbacks = 0;
      for (const page of selected) {
        if (!valid()) return;
        setBusy(`正在生成第 ${page.outline.page} 页内容…`);
        // Regeneration discards the previous version, even if the request fails.
        setPages(current => current.map(item => item.id === page.id ? { ...item, content: undefined, error: undefined } : item));
        try {
          const content = await generatePageContent(settings, page.outline, { signal });
          if (content.generation_mode === 'fallback') fallbacks++;
          if (valid()) setPages(current => current.map(item => item.id === page.id ? { ...item, content, error: undefined } : item));
        } catch (err) {
          if (!valid()) return;
          failed++;
          setPages(current => current.map(item => item.id === page.id ? { ...item, error: message(err) } : item));
        }
      }
      if (valid()) setNotice(failed ? `${failed} 页生成失败，可逐页重试。` : fallbacks ? `${fallbacks} 页为未生成的空白内容；请人工填写要点并核验后再导出。` : '页面内容生成完成，可编辑核验后导出。');
    });
  }
  const completed = pages.filter(page => page.content).length;
  const canExport = pages.length > 0 && completed === pages.length && pages.every(page => page.content?.title.trim() && page.outline.title.trim() && (page.content?.generation_mode !== 'fallback' || page.content?.bullets.some(bullet => bullet.trim())));
  function exportPpt() {
    if (!canExport) return;
    void run('正在组装 PPTX 文件，请稍候…', async (signal, valid) => {
      clearDownload();
      const blob = await generatePpt(settings.topic, pages.map(page => ({ ...page.content!, page: page.outline.page, type: page.outline.type })), { signal });
      if (!valid()) return;
      const url = URL.createObjectURL(blob);
      downloadRef.current = url; setDownload(url); setNotice('PPTX 文件已生成，点击下载。');
    });
  }
  function patchContent(id: string, patch: Partial<PageContent>) {
    changePages(pages.map(page => page.id === id && page.content ? { ...page, content: { ...page.content, ...patch } } : page));
  }

  return <div className="h-full overflow-y-auto bg-bg text-text p-4 md:p-8">
    <div className="mx-auto max-w-6xl space-y-6 pb-12">
      <PageHeader title="方案生成" description="检索并核验知识来源 → 编辑大纲 → 逐页生成与编辑 → 导出 PPTX" />
      {(error || basesError) && <div role="alert" className="rounded-lg border border-danger bg-danger/10 p-4 text-danger">
        {error || basesError} {(error || basesError).includes('登录') && <a href="/login" className="ml-2 underline">前往登录</a>}
      </div>}
      <div role="status" aria-live="polite" className="text-sm text-text-secondary">{busy || notice}</div>
      <section className={panel} aria-label="方案设置">
        <h2 className="text-lg font-semibold">1. 方案设置</h2>
        <fieldset disabled={locked} className="space-y-4">
          <label className="block">方案主题 <input className={field} value={settings.topic} onChange={e => changeSettings({ topic: e.target.value })} placeholder="请输入方案主题（必填）" /></label>
          <div className="grid gap-4 md:grid-cols-2">
            <label>目标受众 <input className={field} value={settings.target_audience} onChange={e => changeSettings({ target_audience: e.target.value })} placeholder="例如：企业采购负责人" /></label>
            <label>呈现风格 <input className={field} value={settings.style} onChange={e => changeSettings({ style: e.target.value })} /></label>
          </div>
          <div><h3 className="font-medium">组织知识库</h3><p className="text-sm text-text-secondary">未选择 = 检索当前组织全部知识库。修改任何设置将清除旧检索、大纲、内容及下载。</p>
            {loadingBases ? <p>正在加载知识库…</p> : !bases.length && !basesError ? <p>当前组织暂无知识库，可继续检索并使用通用知识。</p> : null}
            <div className="mt-2 flex flex-wrap gap-4">{bases.map(base => <label key={base.id} className="flex items-center gap-2"><input type="checkbox" checked={settings.kb_ids.includes(base.id)} onChange={e => changeSettings({ kb_ids: e.target.checked ? [...settings.kb_ids, base.id] : settings.kb_ids.filter(id => id !== base.id) })} />{base.name}</label>)}</div>
          </div>
        </fieldset>
        {basesError && <Button variant="outline" disabled={locked} onClick={() => setBasesAttempt(n => n + 1)}>重试加载知识库</Button>}
        <Button disabled={locked || !!basesError || !settings.topic.trim()} onClick={retrieve}>{context ? '重新检索' : '检索知识库'}</Button>
      </section>
      {context && <section className={panel} aria-label="检索结果">
        <h2 className="text-lg font-semibold">2. 检索结果与来源（{context.items.length} 条）</h2>
        <Sources items={context.items} />
        <h3 className="font-medium">真实检索日志（服务返回，非模型思考过程）</h3>
        <ol className="space-y-2 text-sm">{context.logs.map((log, index) => <li key={index} className="rounded bg-bg p-2 break-words"><span className="text-text-secondary">{log.timestamp}</span> · <strong>{log.step}</strong><pre className="whitespace-pre-wrap font-sans">{typeof log.details === 'string' ? log.details : JSON.stringify(log.details, null, 2)}</pre></li>)}</ol>
        {!context.logs.length && <p className="text-sm text-text-secondary">服务未返回检索日志。</p>}
        <Button disabled={locked} onClick={createOutline}>已查看检索结果，{outline ? '重新生成大纲' : '生成大纲'}</Button>
      </section>}
      {outline && <section className={panel} aria-label="大纲与页面内容">
        <h2 className="text-lg font-semibold">3. 大纲与内容</h2>
        <GenerationStatus result={outline} />
        {!!outline.sources?.length && <details><summary>大纲生成使用的来源</summary><Sources items={outline.sources} /></details>}
        <p className="text-sm text-text-secondary">修改大纲字段会清除该页旧内容；重排保留内容。所有内容修改均使旧下载失效。生成期间禁止编辑。</p>
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" disabled={locked} onClick={() => changePages([...pages, { id: String(++nextId.current), outline: { page: pages.length + 1, title: '', type: 'content', key_points_hint: '' } }])}>添加页面</Button>
          <Button disabled={locked || !pages.length || pages.some(page => !page.outline.title.trim()) || completed === pages.length} onClick={() => createContent(pages.filter(page => !page.content).map(page => page.id))}>生成全部未完成页 / 重试失败页</Button>
          <span role="status" className="self-center text-sm">内容已生成 {completed} / {pages.length} 页</span>
        </div>
        {pages.map((page, index) => <article key={page.id} className="space-y-3 rounded-lg border border-separator p-4">
          <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold">第 {index + 1} 页</h3><div className="flex gap-2">
            <Button variant="outline" size="sm" aria-label={`上移第 ${index + 1} 页`} disabled={locked || index === 0} onClick={() => changePages(movePage(pages, index, -1))}>上移</Button>
            <Button variant="outline" size="sm" aria-label={`下移第 ${index + 1} 页`} disabled={locked || index === pages.length - 1} onClick={() => changePages(movePage(pages, index, 1))}>下移</Button>
            <Button variant="destructive" size="sm" aria-label={`删除第 ${index + 1} 页`} disabled={locked} onClick={() => changePages(pages.filter(item => item.id !== page.id))}>删除</Button>
          </div></div>
          <fieldset disabled={locked} className="grid gap-3 md:grid-cols-2">
            <label>大纲标题 <input className={field} value={page.outline.title} onChange={e => changePages(pages.map(item => item.id === page.id ? editOutline(item, { title: e.target.value }) : item))} /></label>
            <label>页面类型 <select className={field} value={page.outline.type} onChange={e => changePages(pages.map(item => item.id === page.id ? editOutline(item, { type: e.target.value }) : item))}><option value="cover">封面</option><option value="catalog">目录</option><option value="content">正文</option><option value="break">过渡页</option><option value="end">结束页</option></select></label>
            <label className="md:col-span-2">要点提示 <textarea className={field} value={page.outline.key_points_hint ?? ''} onChange={e => changePages(pages.map(item => item.id === page.id ? editOutline(item, { key_points_hint: e.target.value }) : item))} /></label>
          </fieldset>
          {page.error && <p role="alert" className="text-danger">{page.error}</p>}
          <Button variant="secondary" disabled={locked || !page.outline.title.trim()} onClick={() => createContent([page.id])}>{page.error ? '重试本页' : page.content ? '重新生成本页内容' : '生成本页内容'}</Button>
          {page.content && <div className="space-y-3 border-t border-separator pt-4">
            <GenerationStatus result={page.content} />
            <fieldset disabled={locked} className="grid gap-3 md:grid-cols-2">
              <label>内容标题 <input className={field} value={page.content.title} onChange={e => patchContent(page.id, { title: e.target.value })} /></label>
              <label>内容类型 <select className={field} value={page.content.type} onChange={e => patchContent(page.id, { type: e.target.value })}><option value="cover">封面</option><option value="catalog">目录</option><option value="content">正文</option><option value="break">过渡页</option><option value="end">结束页</option></select></label>
              <label className="md:col-span-2">内容要点（每行一条）<textarea rows={5} className={field} value={page.content.bullets.join('\n')} onChange={e => patchContent(page.id, { bullets: e.target.value.split('\n') })} /></label>
              <label>配图建议 <textarea className={field} value={page.content.image_suggestion ?? ''} onChange={e => patchContent(page.id, { image_suggestion: e.target.value })} /></label>
              <label>演讲备注 <textarea className={field} value={page.content.speaker_notes ?? ''} onChange={e => patchContent(page.id, { speaker_notes: e.target.value })} /></label>
              <label className="md:col-span-2">数据来源说明 <textarea className={field} value={page.content.data_source ?? ''} onChange={e => patchContent(page.id, { data_source: e.target.value })} /></label>
            </fieldset>
            <details><summary className="cursor-pointer">本页检索来源（{page.content.sources.length}）</summary><Sources items={page.content.sources} /></details>
          </div>}
        </article>)}
      </section>}
      {outline && <section className={panel} aria-label="导出 PPT">
        <h2 className="text-lg font-semibold">4. 生成与下载 PPTX</h2>
        <p>内容已生成 {completed} / {pages.length} 页。全部页面完成、标题非空且模板回退页已由人工填写要点后可导出。</p>
        <p className="text-sm text-text-secondary">导出阶段等待服务实际完成，不展示估算百分比。失败后可再次点击重试。</p>
        <div className="flex flex-wrap items-center gap-4"><Button disabled={locked || !canExport} onClick={exportPpt}>生成 PPTX / 重试导出</Button>
          {download && !locked && <a className="rounded-md bg-accent px-4 py-2 text-on-accent hover:bg-accent-hover" href={download} download="方案.pptx">下载 PPTX</a>}
        </div>
      </section>}
    </div>
  </div>;
}
