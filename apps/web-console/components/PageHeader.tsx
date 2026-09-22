import * as React from "react"
import { cn } from "@/lib/utils"

export interface PageHeaderProps {
  title: string
  description?: string
  /** 标题右侧操作区（按钮等），所有子应用保持相同位置与尺寸 */
  actions?: React.ReactNode
  className?: string
}

/**
 * 统一页面标题：纯文字大标题 + 下方一行说明，右侧操作区对齐基线
 */
export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-4 mb-6", className)}>
      <div className="min-w-0">
        <h1 className="apple-title">{title}</h1>
        {description && <p className="apple-subtitle">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  )
}
