"use client";
import { PageHeader } from "@/components/PageHeader";

export default function KnowledgeBrain() {
  return (
    <div className="min-h-screen bg-bg text-text p-8">
      <PageHeader
        title="企业知识大脑"
        description="对话入口已在右侧 ChatSidebar。请先在「知识文档」上传资料，再回到工作台提问。"
      />
    </div>
  );
}
