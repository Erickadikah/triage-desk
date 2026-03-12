"use client";

import { cn } from "@/lib/utils";
import { useState, useRef, useEffect } from "react";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  className?: string;
  size?: "default" | "sm";
}

function Select({ value, onChange, options, placeholder, className, size = "default" }: SelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const selected = options.find((o) => o.value === value);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={ref} className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "flex w-full items-center justify-between rounded-md border border-border bg-background text-sm cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50",
          size === "sm" ? "h-7 px-2 py-1 text-xs" : "h-10 px-3 py-2",
          !selected && "text-muted-foreground"
        )}
      >
        <span className="truncate">{selected ? selected.label : placeholder || "Select..."}</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={cn("shrink-0 ml-2 text-muted-foreground transition-transform", open && "rotate-180")}
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-border bg-background shadow-lg animate-in fade-in-0 zoom-in-95 duration-100">
          <div className="py-1">
            {options.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center hover:bg-muted transition-colors cursor-pointer",
                  size === "sm" ? "px-2 py-1.5 text-xs" : "px-3 py-2 text-sm",
                  option.value === value && "bg-muted font-medium"
                )}
              >
                {option.value === value && (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="mr-2 shrink-0"
                  >
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                )}
                <span className={option.value !== value ? "ml-6" : ""}>{option.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export { Select };
export type { SelectOption, SelectProps };
