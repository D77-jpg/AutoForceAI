"use client";
import React from 'react';
import { Briefcase, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function CrmPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center p-8">
      <div className="bg-danger/10 p-6 rounded-full border border-danger/20 mb-6 shadow-[0_0_30px_rgb(var(--ui-danger)/0.2)]">
        <Briefcase size={48} className="text-danger" />
      </div>
      <h1 className="text-3xl font-bold text-white mb-2">AI 客户关系管理 CRM</h1>
      <p className="text-text-secondary max-w-md mb-8">
        Genesis_CRM 集成暂缓。当前询盘先落入本地线索池，可筛选、改状态、导出 CSV；CRM 稳定后再由投递器同步，无需返工。
      </p>
      <div className="flex gap-3">
        <Link href="/leads" className="px-6 py-2.5 bg-accent hover:bg-accent-hover rounded-lg text-sm text-white">打开本地线索池</Link>
        <Link href="/" className="flex items-center gap-2 px-6 py-2 bg-text/5 hover:bg-text/10 border border-separator rounded-lg text-sm text-white transition-colors">
           <ArrowLeft size={16} /> 返回门户
        </Link>
      </div>
    </div>
  );
}
