"use client";
import React from 'react';
import { Construction, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function OrganizationPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center p-8">
      <div className="bg-emerald-500/10 p-6 rounded-full border border-emerald-500/20 mb-6 shadow-[0_0_30px_rgba(16,185,129,0.2)]">
        <Construction size={48} className="text-emerald-400" />
      </div>
      <h1 className="text-3xl font-bold text-white mb-2">虚拟组织中心</h1>
      <p className="text-slate-400 max-w-md mb-8">
        虚拟组织中心正在构建中。您将在此编排您的 AI 员工团队。<br/>
        Virtual Organization Center is under construction.
      </p>
      <Link href="/" className="flex items-center gap-2 px-6 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-white transition-colors">
         <ArrowLeft size={16} /> 返回门户
      </Link>
    </div>
  );
}
