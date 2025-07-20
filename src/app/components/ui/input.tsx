import * as React from "react"

import { cn } from "@/lib/utils"

// Define the props interface for our component
export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

// --- The Input Component ---
// It uses React.forwardRef to correctly pass down refs, which is essential
// for form libraries and accessibility.
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          // --- Base Styles ---
          // Layout, typography, and background
          "flex h-10 w-full rounded-md border px-3 py-2 text-sm text-white",
          "bg-black/20 backdrop-blur-sm border-white/20", // Glassmorphism effect
          "placeholder:text-white/50", // Style for placeholder text

          // --- Interaction & Focus Styles ---
          // Ring for focus state, using your theme colors
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-purple-500 focus-visible:ring-offset-slate-900",
          "transition-all duration-300", // Smooth transition for focus effect
          
          // --- File Input Specific Styles ---
          // Special styles for file input types to make them look good
          "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-white/80 hover:file:text-white",

          // --- Disabled State ---
          "disabled:cursor-not-allowed disabled:opacity-50",

          // Allow for custom classes to be passed in and merged
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }