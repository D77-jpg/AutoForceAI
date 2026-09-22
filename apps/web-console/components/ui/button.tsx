import * as React from "react"
import { cn } from "@/lib/utils"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
  size?: "default" | "sm" | "lg" | "icon"
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    
    const variants = {
      default: "bg-[#0071e3] text-white hover:bg-[#0077ed] shadow-sm",
      destructive: "bg-[#ff453a] text-white hover:bg-[#ff6961]",
      outline: "border border-white/12 bg-transparent hover:bg-white/6 text-[#f5f5f7]",
      secondary: "bg-[#2c2c2e] text-[#f5f5f7] hover:bg-[#3a3a3c]",
      ghost: "hover:bg-white/8 text-[#f5f5f7]",
      link: "text-[#0a84ff] underline-offset-4 hover:underline",
    }
    
    const sizes = {
      default: "h-10 px-4 py-2 rounded-full",
      sm: "h-8 rounded-full px-3 text-[13px]",
      lg: "h-12 rounded-full px-8",
      icon: "h-10 w-10 rounded-full",
    }

    return (
      <button
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap text-sm font-medium tracking-tight transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]/50 disabled:pointer-events-none disabled:opacity-40",
          variants[variant],
          sizes[size],
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
