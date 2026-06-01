import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-accent/15 text-blue-300 ring-1 ring-accent/20",
        success: "bg-success/15 text-emerald-300 ring-1 ring-success/20",
        warning: "bg-warning/15 text-amber-300 ring-1 ring-warning/20",
        muted: "bg-white/5 text-text-secondary ring-1 ring-white/10",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
