import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

// --- Advanced Button Variants Definition ---
// This defines all the button styles, including custom gradients and refined interactions.
const buttonVariants = cva(
  // Base classes for all buttons: consistent typography, layout, and focus states.
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-semibold ring-offset-background transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        // Default style: A solid, primary button. We'll make this a gradient.
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        
        // --- CUSTOM GRADIENT VARIANTS ---
        "gradient-primary": // For primary actions like "Start Querying"
          "bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg hover:from-blue-600 hover:to-purple-700 transform hover:scale-105",
        "gradient-secondary": // For actions like "Start Indexing"
          "bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-lg hover:from-purple-600 hover:to-pink-700 transform hover:scale-105",
        // --------------------------------

        // Destructive style for delete/error actions
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
          
        // Outline style: A button with a border
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
          
        // Secondary style: A less prominent button
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
          
        // Ghost style: A button with no background or border, for subtle actions.
        // We'll add a subtle hover effect to match your UI.
        ghost: "hover:bg-accent/20 hover:text-accent-foreground",
        
        // Link style: A simple text link that looks like a button
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8", // A larger size for hero buttons
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

// Define the props interface for our component, including `asChild`
export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

// --- The Button Component ---
// It uses `React.forwardRef` to correctly pass down refs.
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    // If `asChild` is true, it renders the child component with the button's classes.
    // Otherwise, it renders a standard <button> element.
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }