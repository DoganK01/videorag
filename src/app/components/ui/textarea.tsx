import * as React from "react"

import { cn } from "@/lib/utils"

// Define the props interface for our component, extending standard textarea attributes.
export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

// --- The Textarea Component ---
// It uses React.forwardRef to correctly pass down refs.
const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          // --- Base Styles ---
          // Layout, typography, and background to match your Input component.
          "flex min-h-[80px] w-full rounded-md border px-3 py-2 text-sm",
          "bg-black/20 backdrop-blur-sm border-white/20", // Glassmorphism effect
          "placeholder:text-white/50", // Style for placeholder text

          // --- Interaction & Focus Styles ---
          // A vibrant ring on focus, matching your theme's purple/blue palette.
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-purple-500 focus-visible:ring-offset-slate-900",
          "transition-colors duration-300",

          // --- Custom Scrollbar Styling ---
          // These classes style the scrollbar to fit the dark theme.
          "scrollbar-thin scrollbar-thumb-white/30 scrollbar-track-white/10 hover:scrollbar-thumb-white/50",

          // --- Behavior ---
          // Prevents the user from resizing the textarea, maintaining layout integrity.
          "resize-none",

          // --- Disabled State ---
          "disabled:cursor-not-allowed disabled:opacity-50",

          // Allow for custom classes to be passed in and merged.
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export { Textarea }