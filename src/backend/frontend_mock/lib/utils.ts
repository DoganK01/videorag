import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * A utility function to conditionally and intelligently merge Tailwind CSS classes.
 * It combines the functionality of `clsx` (for conditional classes) and
 * `tailwind-merge` (for resolving conflicting Tailwind utility classes).
 *
 * This is the standard utility function used by shadcn/ui.
 *
 * @param inputs - A list of class values (strings, objects, arrays).
 * @returns A single, clean string of non-conflicting class names.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}