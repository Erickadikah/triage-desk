import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";
import { HTMLAttributes } from "react";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-muted text-muted-foreground",
        destructive: "border-transparent bg-destructive text-white",
        outline: "text-foreground",
        high: "border-transparent bg-red-100 text-red-800",
        medium: "border-transparent bg-yellow-100 text-yellow-800",
        low: "border-transparent bg-green-100 text-green-800",
        open: "border-transparent bg-blue-100 text-blue-800",
        "in-progress": "border-transparent bg-purple-100 text-purple-800",
        resolved: "border-transparent bg-gray-100 text-gray-800",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
