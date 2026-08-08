"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
}

// ponytail: no focus trap / portal, add if a real modal-heavy flow needs it.
export function Dialog({ open, onClose, title, children, className }: DialogProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className={cn(
          "w-full max-w-md rounded-2xl border border-surface-border bg-surface-0 p-6 shadow-lg",
          className
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {title && <h2 className="mb-3 text-sm font-semibold text-ink-primary">{title}</h2>}
        {children}
      </div>
    </div>
  );
}
