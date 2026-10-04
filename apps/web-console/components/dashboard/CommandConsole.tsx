"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, Brain } from 'lucide-react';
import { Button } from '@/components/ui/button';

const QUESTIONS = [
  '根据知识库整理产品的交货期和起订量',
  '根据产品资料起草一份英文客户回复',
  '总结知识库中的常见售后问题',
];

export default function CommandConsole() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  return <section aria-label="知识问答入口" className="bg-surface border border-accent/20 rounded-2xl p-5 shadow-card space-y-4">
    <h2 className="text-sm font-semibold flex items-center gap-2"><Brain size={16} />知识问答</h2>
    <p className="text-xs text-text-secondary">在知识大脑中选择资料、生成回答并保存会话。</p>
    <form onSubmit={e => { e.preventDefault(); if (prompt.trim()) router.push(`/knowledge/brain?query=${encodeURIComponent(prompt.trim())}`); }} className="space-y-3">
      <label htmlFor="command-input" className="sr-only">问题描述</label>
      <textarea id="command-input" rows={2} maxLength={8000} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="输入需要知识助手回答的问题" className="w-full rounded-xl border border-separator bg-bg p-3 text-text" />
      <Button type="submit" disabled={!prompt.trim()} className="gap-2">进入知识大脑<ArrowRight size={16} /></Button>
    </form>
    <div className="flex flex-wrap gap-2">{QUESTIONS.map(question => <button key={question} onClick={() => setPrompt(question)} className="rounded-full border border-separator px-3 py-2 text-xs text-text-secondary hover:bg-surface-2">{question}</button>)}</div>
  </section>;
}
