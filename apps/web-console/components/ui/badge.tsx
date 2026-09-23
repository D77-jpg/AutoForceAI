import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline"
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "border-transparent bg-accent text-on-accent",
    secondary: "border-transparent bg-surface-2 text-text-secondary",
    destructive: "border-transparent bg-danger text-on-accent",
    outline: "text-text-secondary border-separator",
  }
  return (
    <div className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-tight transition-colors", variants[variant], className)} {...props} />
  )
}

export { Badge }
