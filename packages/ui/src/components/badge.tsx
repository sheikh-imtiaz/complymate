import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../lib";

const badgeVariants = cva("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", {
  variants: {
    tone: {
      neutral: "bg-slate-100 text-slate-700",
      info: "bg-brand-50 text-brand-700",
      success: "bg-green-50 text-risk-low",
      warning: "bg-amber-50 text-risk-medium",
      danger: "bg-red-50 text-risk-high",
    },
  },
  defaultVariants: { tone: "neutral" },
});

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
