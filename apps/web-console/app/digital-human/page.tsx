"use client";
import React from 'react';
import { Video, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function DigitalHumanPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center p-8">
      <div className="bg-accent/10 p-6 rounded-full border border-accent/20 mb-6 shadow-[0_0_30px_rgb(var(--ui-accent)/0.2)]">
        <Video size={48} className="text-accent" />
      </div>
      <h1 className="text-3xl font-bold text-white mb-2">数字人梦工厂</h1>
      <p className="text-text-secondary max-w-md mb-8">
        数字人模块规划中（远期）。将提供高保真虚拟人视频生成与直播流管理。<br/>
        Digital Human module is planned for a future release.
      </p>
      <Link href="/" className="flex items-center gap-2 px-6 py-2 bg-text/5 hover:bg-text/10 border border-separator rounded-lg text-sm text-white transition-colors">
         <ArrowLeft size={16} /> 返回门户
      </Link>
    </div>
  );
}
