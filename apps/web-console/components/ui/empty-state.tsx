import * as React from "react"
import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "./button"

export interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  /** 主按钮文案；不传则不显示按钮 */
  actionLabel?: string
  onAction?: () => void
  /** lg：主数据缺失时独占主区域；sm：面板内下级列表为空 */
  size?: "lg" | "sm"
  className?: string
}

/**
 * 统一空状态：居中大图标 + 标题 + 一行说明 + 可选蓝色主按钮
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  size = "lg",
  className,
}: EmptyStateProps) {
  const isLg = size === "lg"
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        isLg ? "py-24 px-6" : "py-10 px-4",
        className
      )}
    >
      <div
        className={cn(
          "rounded-[22%] bg-surface-2 flex items-center justify-center text-text-tertiary",
          isLg ? "w-16 h-16 mb-5" : "w-11 h-11 mb-3"
        )}
      >
        <Icon size={isLg ? 30 : 20} strokeWidth={1.5} />
      </div>
      <h3 className={cn("font-semibold text-text tracking-tight", isLg ? "text-[17px]" : "text-sm")}>
        {title}
      </h3>
      {description && (
        <p className={cn("text-text-secondary max-w-sm", isLg ? "text-sm mt-2" : "text-xs mt-1.5")}>
          {description}
        </p>
      )}
      {actionLabel && (
        <Button onClick={onAction} size={isLg ? "default" : "sm"} className={isLg ? "mt-6" : "mt-4"}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
