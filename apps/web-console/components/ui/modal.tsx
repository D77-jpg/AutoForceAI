"use client"
import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

export interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: React.ReactNode
  /** 底部操作区（按钮组） */
  footer?: React.ReactNode
  className?: string
}

/**
 * 统一弹窗：遮罩点击 / Esc 关闭，标题 + 内容 + 底部操作区
 */
export function Modal({ open, onClose, title, description, children, footer, className }: ModalProps) {
  React.useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          "relative w-full max-w-md bg-surface border border-separator rounded-2xl shadow-modal animate-modal-in",
          className
        )}
      >
        <div className="flex items-start justify-between p-5 pb-0">
          <div className="min-w-0">
            <h2 className="text-[17px] font-semibold text-text tracking-tight">{title}</h2>
            {description && <p className="text-[13px] text-text-secondary mt-1">{description}</p>}
          </div>
          <button
            onClick={onClose}
            aria-label="关闭"
            className="w-7 h-7 shrink-0 rounded-full bg-text/5 hover:bg-text/10 flex items-center justify-center text-text-secondary transition-colors"
          >
            <X size={14} />
          </button>
        </div>
        <div className="p-5">{children}</div>
        {footer && (
          <div className="flex justify-end gap-2 px-5 pb-5 pt-0">{footer}</div>
        )}
      </div>
    </div>
  )
}
