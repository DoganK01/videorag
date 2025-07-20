import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

// --- Advanced Badge Variants Definition ---
// We define a comprehensive set of visual styles for our badges.
// This includes variants for job status, general purposes, and a special gradient effect.
const badgeVariants = cva(
  // Base classes applied to all badges for consistency
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        // Default style - a subtle, secondary look for general tags
        default:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",

        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        
        // Status: Completed (matches your green theme)
        completed:
          "border-transparent bg-green-500/20 text-green-300",
          
        // Status: Processing (matches your blue theme)
        processing:
          "border-transparent bg-blue-500/20 text-blue-300",

        // Status: Pending (matches your yellow theme)
        pending:
          "border-transparent bg-yellow-500/20 text-yellow-300",

        // Status: Error (matches your red theme)
        error:
          "border-transparent bg-red-500/20 text-red-400",
          
        // Outline style for a more subtle look
        outline: "text-foreground",

        // --- Custom Gradient Variant ---
        // This variant will apply your desired purple-to-blue gradient.
        gradient:
          "bg-gradient-to-r from-purple-500 to-blue-500 text-white border-transparent"
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

// Define the props interface for our component
export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

// --- The Badge Component ---
function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }