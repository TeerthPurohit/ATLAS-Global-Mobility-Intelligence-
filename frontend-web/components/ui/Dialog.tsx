"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
}

export function Dialog({ open, onClose, title, children, className }: DialogProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className={cn(
          "w-full rounded-sm border border-surface-border bg-surface-0 p-8 shadow-2xl",
          className
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <div className="flex items-center justify-between mb-6 pb-6 border-b border-surface-border">
            <h2 className="font-section-lg text-ink-primary">{title}</h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-surface-1 rounded-sm transition-colors"
              aria-label="Close dialog"
            >
              <X className="h-5 w-5 text-ink-secondary" />
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
