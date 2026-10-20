import * as React from "react";

import { cn } from "@/lib/utils";

export function Input({ className, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-md border border-line bg-white px-2.5 text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-burgundy/30",
        className,
      )}
      {...props}
    />
  );
}

export function Select({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-9 w-full rounded-md border border-line bg-white px-2 text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-burgundy/30",
        className,
      )}
      {...props}
    />
  );
}

export function Label({ className, ...props }: React.ComponentProps<"label">) {
  return (
    <label
      className={cn("text-[11px] font-medium uppercase tracking-[0.14em] text-muted", className)}
      {...props}
    />
  );
}
