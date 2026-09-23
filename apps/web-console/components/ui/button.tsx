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
      default: "bg-accent text-on-accent hover:bg-accent-hover shadow-sm",
      destructive: "bg-danger text-on-accent hover:bg-danger/90",
      outline: "border border-separator bg-transparent hover:bg-text/5 text-text",
      secondary: "bg-surface-2 text-text hover:bg-surface-2/70",
      ghost: "hover:bg-text/10 text-text",
      link: "text-accent underline-offset-4 hover:underline",
    }

    const sizes = {
      default: "h-10 px-4 py-2 rounded-md",
      sm: "h-8 rounded-md px-3 text-[13px]",
      lg: "h-12 rounded-md px-8",
      icon: "h-10 w-10 rounded-md",
    }

    return (
      <button
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap text-sm font-medium tracking-tight transition-all duration-fast ease-apple active:scale-[0.96] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 disabled:pointer-events-none disabled:opacity-40",
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
