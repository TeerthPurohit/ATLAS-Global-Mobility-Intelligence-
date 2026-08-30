"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

const PUBLIC_ROUTES = new Set(["/login", "/signup"]);

/** Every route except /login and /signup requires a session -- the backend
 * enforces this on every data endpoint (backend/main.py's _REQUIRE_SESSION),
 * this just avoids rendering a protected page (and firing its now-401'd API
 * calls) before bouncing to /login. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isPublicRoute = PUBLIC_ROUTES.has(pathname);

  useEffect(() => {
    if (!loading && !user && !isPublicRoute) {
      router.replace("/login");
    }
  }, [loading, user, isPublicRoute, router]);

  if (isPublicRoute) return <>{children}</>;
  if (loading) {
    return (
      <div className="flex min-h-[calc(100dvh-7rem)] items-center justify-center">
        <div className="flex items-center gap-3 rounded-2xl border border-surface-border bg-surface-1 px-5 py-4 text-sm text-ink-secondary shadow-sm">
          <span className="h-2 w-2 animate-pulse rounded-full bg-brass" aria-hidden="true" />
          Checking your session...
        </div>
      </div>
    );
  }
  if (!user) return null;
  return <>{children}</>;
}
