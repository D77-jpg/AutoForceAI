"use client";
import { PageHeader } from "@/components/PageHeader";

export default function Page() {
  return (
    <div className="min-h-screen bg-bg text-text p-8">
      <PageHeader
        title="方案生成"
        description="请使用工作台里的方案生成（solution_router），本页为入口占位。"
      />
    </div>
  );
}
