"use client";
import React from 'react';
import { Video, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';

export default function DigitalHumanPage() {
  return (
    <div className="min-h-screen bg-bg text-text p-8">
      <PageHeader
        title="数字人直播"
        description="数字人模块规划中（远期）。"
      />
      <div className="flex flex-col items-center justify-center text-center py-20">
        <div className="bg-accent/10 p-6 rounded-full border border-accent/20 mb-6 shadow-card">
          <Video size={48} className="text-accent" />
        </div>
        <p className="text-text-secondary max-w-md mb-8">
          将提供高保真虚拟人视频生成与直播流管理。
        </p>
        <Link href="/">
          <Button variant="outline">
            <ArrowLeft size={16} className="mr-2" /> 返回门户
          </Button>
        </Link>
      </div>
    </div>
  );
}
