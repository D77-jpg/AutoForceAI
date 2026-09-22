"use client";
import React from 'react';
import { Briefcase, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';

export default function CrmPage() {
  return (
    <div className="min-h-screen bg-bg text-text p-8">
      <PageHeader
        title="AI CRM"
        description="Genesis_CRM 集成暂缓，当前使用本地线索池承接询盘。"
      />
      <div className="flex flex-col items-center justify-center text-center py-20">
        <div className="bg-accent/10 p-6 rounded-full border border-accent/20 mb-6 shadow-card">
          <Briefcase size={48} strokeWidth={1.75} className="text-accent" />
        </div>
        <p className="text-text-secondary max-w-md mb-8">
          当前询盘先落入本地线索池，可筛选、改状态、导出 CSV；CRM 稳定后再由投递器同步，无需返工。
        </p>
        <div className="flex gap-2">
          <Link href="/leads">
            <Button>打开本地线索池</Button>
          </Link>
          <Link href="/">
            <Button variant="outline">
              <ArrowLeft size={16} className="mr-2" /> 返回门户
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
