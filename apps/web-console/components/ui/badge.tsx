import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline"
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "border-transparent bg-[#0071e3] text-white",
    secondary: "border-transparent bg-[#2c2c2e] text-[#f5f5f7]",
    destructive: "border-transparent bg-[#ff453a] text-white",
    outline: "text-[#f5f5f7] border-white/12",
  }
  return (
    <div className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-tight transition-colors", variants[variant], className)} {...props} />
  )
}

export { Badge }
