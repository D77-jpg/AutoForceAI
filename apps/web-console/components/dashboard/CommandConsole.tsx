"use client";

import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, Brain, ChevronDown, User } from 'lucide-react';
import type { QuickCommand } from '@/lib/dashboard-types';

/**
 * 指挥台：页面视觉重心。
 * 比其他卡片更突出：rounded-2xl + 轻微主色渐变描边（border 用 accent/20，暗色同样生效）。
 */
export default function CommandConsole({ quickCommands }: { quickCommands: QuickCommand[] }) {
  const [prompt, setPrompt] = useState('');
  const [assignee, setAssignee] = useState('自动分配');
  const [showAssignee, setShowAssignee] = useState(false);

  return (
    <section
      aria-label="指挥台"
      className="bg-surface border border-accent/20 rounded-2xl p-5 shadow-card flex flex-col gap-4"
    >
      <div className="flex items-baseline gap-2">
        <h2 className="text-sm font-semibold text-text tracking-tight">指挥台</h2>
        <span className="text-xs text-text-tertiary">用一句话把任务交给你的 AI 团队</span>
      </div>

      {/* 输入区 */}
      <div className="rounded-xl border border-separator bg-bg/50 focus-within:border-accent/40 transition-colors p-3.5 flex flex-col gap-3">
        <label htmlFor="command-input" className="sr-only">
          任务描述
        </label>
        <textarea
          id="command-input"
          rows={2}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="分析 Q3 北美五金类目的询盘变化，下周一前出一份报告"
          className="w-full resize-none bg-transparent border-none outline-none text-[15px] leading-relaxed text-text placeholder:text-text-tertiary"
        />
        <div className="flex items-center gap-2 flex-wrap">
          {/* 指派下拉 */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowAssignee((v) => !v)}
              aria-expanded={showAssignee}
              aria-haspopup="listbox"
              className="h-[30px] px-2.5 rounded-md border border-separator bg-surface hover:bg-surface-2 text-xs text-text flex items-center gap-1.5 transition-colors"
            >
              <User size={12} className="text-text-secondary" />
              指派：{assignee}
              <ChevronDown size={11} className={`text-text-tertiary transition-transform duration-fast ${showAssignee ? 'rotate-180' : ''}`} />
            </button>
            {showAssignee && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowAssignee(false)} aria-hidden="true" />
                <div role="listbox" className="absolute top-full left-0 mt-1 w-40 bg-surface border border-separator rounded-xl shadow-popover p-1 z-50 animate-fade-in-up">
                  {['自动分配', '按模块负责人', '指定员工'].map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      role="option"
                      aria-selected={assignee === opt}
                      onClick={() => {
                        setAssignee(opt);
                        setShowAssignee(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs rounded-lg transition-colors ${
                        assignee === opt ? 'text-accent bg-accent/10 font-medium' : 'text-text hover:bg-text/5'
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* 引用知识大脑 */}
          <Link
            href="/knowledge/brain"
            className="h-[30px] px-2.5 rounded-md border border-separator bg-surface hover:bg-surface-2 text-xs text-text flex items-center gap-1.5 transition-colors"
          >
            <Brain size={12} />
            引用知识大脑
          </Link>

          {/* 派发主按钮 */}
          <button
            type="button"
            disabled
            aria-describedby="dispatch-helper"
            title="任务派发接口尚未接入"
            className="ml-auto h-[34px] px-4 rounded-pill bg-accent text-on-accent text-[13px] font-medium flex items-center gap-1.5 opacity-50 cursor-not-allowed"
          >
            派发接口待接入
            <ArrowRight size={13} />
          </button>
        </div>
        <p id="dispatch-helper" className="text-[11px] text-text-tertiary">
          当前可先整理任务草稿；此处不会创建或派发真实任务。
        </p>
      </div>

      {/* 快捷指令胶囊 */}
      <div className="flex flex-wrap gap-2">
        {quickCommands.map((qc) => (
          <button
            key={qc.id}
            type="button"
            onClick={() => setPrompt(qc.prompt)}
            className="h-[30px] px-3 rounded-pill border border-separator bg-surface hover:bg-surface-2 text-xs text-text-secondary hover:text-text transition-colors"
          >
            {qc.label}
          </button>
        ))}
      </div>
    </section>
  );
}
