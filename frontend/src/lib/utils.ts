import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const PRIORITY_VARIANT = {
  High: "high",
  Medium: "medium",
  Low: "low",
} as const;
