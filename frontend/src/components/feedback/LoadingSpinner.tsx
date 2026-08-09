/**
 * src/components/feedback/LoadingSpinner.tsx
 *
 * Reusable loading spinner with optional full-page mode.
 *
 * Usage:
 *   <LoadingSpinner />                  — inline spinner
 *   <LoadingSpinner fullPage />         — centered on full viewport
 *   <LoadingSpinner size="lg" label="Loading repositories..." />
 */
import { Loader2 } from "lucide-react";
import { cn } from "@/utils/cn";

type SpinnerSize = "sm" | "md" | "lg";

interface LoadingSpinnerProps {
  /** Display centered over the full viewport */
  fullPage?: boolean;
  /** Size of the spinner */
  size?: SpinnerSize;
  /** Optional label shown below the spinner */
  label?: string;
  /** Additional CSS classes */
  className?: string;
}

const SIZE_CLASSES: Record<SpinnerSize, string> = {
  sm: "h-4 w-4",
  md: "h-6 w-6",
  lg: "h-10 w-10",
};

export function LoadingSpinner({
  fullPage = false,
  size = "md",
  label,
  className,
}: LoadingSpinnerProps) {
  const spinner = (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3",
        fullPage && "h-full min-h-[50vh]",
        className
      )}
      role="status"
      aria-label={label ?? "Loading..."}
    >
      <Loader2
        className={cn(
          "animate-spin text-primary",
          SIZE_CLASSES[size]
        )}
      />
      {label && (
        <p className="text-sm text-muted-foreground animate-pulse">{label}</p>
      )}
    </div>
  );

  return spinner;
}
