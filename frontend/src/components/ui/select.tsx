import { cn } from "@/lib/utils";
import { SelectHTMLAttributes, forwardRef } from "react";

const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(({ className, ...props }, ref) => (
  <select
    className={cn(
      "flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50",
      className
    )}
    ref={ref}
    {...props}
  />
));
Select.displayName = "Select";

export { Select };
