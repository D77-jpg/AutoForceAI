"use client";
import React from 'react';
import { Construction, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function OrganizationPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center p-8">
      <div className="bg-success/10 p-6 rounded-full border border-success/20 mb-6 shadow-card">
        <Construction size={48} className="text-success" />
      </div>
      <h1 className="text-3xl font-bold text-text mb-2">虚拟组织中心</h1>
      <p className="text-text-secondary max-w-md mb-8">
        虚拟组织中心正在构建中。您将在此编排您的 AI 员工团队。
      </p>
      <Link href="/" className="flex items-center gap-2 px-6 py-2 bg-text/5 hover:bg-text/10 border border-separator rounded-lg text-sm text-text transition-colors">
         <ArrowLeft size={16} /> 返回门户
      </Link>
    </div>
  );
}
