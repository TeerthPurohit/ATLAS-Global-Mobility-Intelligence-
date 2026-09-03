"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Compass, History, Settings, Home } from "lucide-react";
import { Dialog } from "@/components/ui/Dialog";
import { cn } from "@/lib/utils";

const commands = [
  { href: "/journey", label: "Journey", icon: Compass },
  { href: "/history", label: "History", icon: History },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/", label: "Landing page", icon: Home },
];

// Ctrl+K / Cmd+K palette, available shell-wide (mounted once in layout.tsx).
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  function go(href: string) {
    setOpen(false);
    router.push(href);
  }

  return (
    <Dialog open={open} onClose={() => setOpen(false)} title="Go to" className="max-w-sm p-2">
      <ul className="flex flex-col gap-1">
        {commands.map(({ href, label, icon: Icon }) => (
          <li key={href}>
            <button
              type="button"
              onClick={() => go(href)}
              className={cn(
                "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-ink-secondary",
                "hover:bg-surface-2 hover:text-ink-primary focus:bg-surface-2 focus:text-ink-primary focus:outline-none"
              )}
            >
              <Icon className="h-4 w-4 text-brass" />
              {label}
            </button>
          </li>
        ))}
      </ul>
    </Dialog>
  );
}
