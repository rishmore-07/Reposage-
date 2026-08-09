/**
 * src/utils/cn.ts
 *
 * Utility for merging Tailwind CSS class names.
 * Combines clsx (conditional classes) with tailwind-merge (deduplication).
 *
 * Why tailwind-merge?
 * When conditionally applying Tailwind classes, conflicts arise:
 *   cn("px-4", "px-6") → "px-4 px-6" (broken — both apply)
 * tailwind-merge resolves conflicts correctly:
 *   cn("px-4", "px-6") → "px-6" (last wins)
 *
 * Usage:
 *   cn("base-class", isActive && "active-class", "always-applied")
 *   cn(buttonVariants({ size: "lg" }), className)
 */
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
