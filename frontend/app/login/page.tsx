"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { NycOrbit } from "@/components/login/NycOrbit";
import { useAuth } from "@/context/AuthContext";
import { login, signup, loginAsDemo } from "@/lib/api";
import { ArrowRight, Compass, LockKeyhole, Zap } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "signup" && password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(email, password);
      }
      await refresh();
      router.push("/");
    } catch (err) {
      const msg = err instanceof Error ? err.message : `${mode === "login" ? "Login" : "Sign up"} failed`;
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDemoAccess() {
    setError(null);
    setDemoLoading(true);
    try {
      await loginAsDemo();
      await refresh();
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Instant demo access failed");
      setDemoLoading(false);
    }
  }

  return (
    <div className="relative mx-auto flex min-h-[calc(100dvh-5rem)] max-w-6xl items-center justify-center px-4 py-8">
      {/* Ambient background lighting */}
      <div className="pointer-events-none absolute -left-20 top-1/4 h-80 w-80 rounded-full bg-brass/10 blur-[90px]" />
      <div className="pointer-events-none absolute -right-20 bottom-1/4 h-80 w-80 rounded-full bg-accent-primary/10 blur-[90px]" />

      <div className="grid w-full items-center gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
        {/* Left Column: 3D Globe */}
        <div className="hidden items-center justify-center lg:flex">
          <NycOrbit />
        </div>

        {/* Right Column: Clean Auth Console */}
        <div className="mx-auto flex w-full max-w-md flex-col gap-6">
          {/* Header */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-brass">
              <Compass className="h-4 w-4" />
              <span>NYC Ride Intelligence</span>
            </div>
            <h1 className="font-display-lg text-3xl font-extrabold text-ink-primary sm:text-4xl">
              See the city in motion.
            </h1>
            <p className="font-body-md text-sm text-ink-secondary">
              Sign in to explore demand, fares, and journeys grounded in real TLC records.
            </p>
          </div>

          {/* Form Card */}
          <div className="rounded-3xl border border-surface-border bg-surface-1/95 p-7 shadow-[0_24px_60px_-24px_rgba(28,27,51,0.2)] backdrop-blur-xl sm:p-8">
            {/* Quick Demo Access Button */}
            <Button
              type="button"
              variant="primary"
              disabled={demoLoading || submitting}
              onClick={handleDemoAccess}
              className="mb-5 w-full gap-2 py-2.5 font-medium shadow-sm transition-transform active:scale-[0.98]"
            >
              <Zap className="h-4 w-4 fill-current text-white" />
              {demoLoading ? "Entering ATLAS..." : "⚡ 1-Click Instant Demo"}
            </Button>

            {/* Divider */}
            <div className="relative my-4 flex items-center justify-center">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-surface-border" />
              </div>
              <span className="relative bg-surface-1 px-3 text-xs uppercase tracking-wider text-ink-muted">
                or continue with email
              </span>
            </div>

            {/* Tab Mode Switcher */}
            <div className="mb-5 flex rounded-xl border border-surface-border bg-surface-0/60 p-1">
              <button
                type="button"
                onClick={() => {
                  setMode("login");
                  setError(null);
                }}
                className={`flex-1 rounded-lg py-2 text-center text-xs font-semibold transition-all ${
                  mode === "login"
                    ? "bg-surface-1 text-ink-primary shadow-xs"
                    : "text-ink-secondary hover:text-ink-primary"
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode("signup");
                  setError(null);
                }}
                className={`flex-1 rounded-lg py-2 text-center text-xs font-semibold transition-all ${
                  mode === "signup"
                    ? "bg-surface-1 text-ink-primary shadow-xs"
                    : "text-ink-secondary hover:text-ink-primary"
                }`}
              >
                Create Account
              </button>
            </div>

            {/* Title */}
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-ink-primary">
                  {mode === "login" ? "Welcome back" : "Create your account"}
                </h2>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brass/10 text-brass">
                <LockKeyhole className="h-4 w-4" />
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="email" className="text-xs font-semibold text-ink-primary">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  required
                  placeholder="analyst@domain.com"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="password" className="text-xs font-semibold text-ink-primary">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  required
                  placeholder={mode === "signup" ? "Min 8 characters" : "••••••••"}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              {error && (
                <div className="flex items-start gap-2 rounded-xl border border-danger/30 bg-danger/10 p-3 text-xs text-danger">
                  <p className="flex-1">{error}</p>
                </div>
              )}

              <Button
                type="submit"
                disabled={submitting || demoLoading}
                className="mt-2 w-full gap-2 py-2.5 font-semibold"
              >
                {submitting ? (
                  mode === "login" ? "Signing in..." : "Creating Account..."
                ) : (
                  <>
                    <span>{mode === "login" ? "Continue to ATLAS" : "Sign Up & Continue"}</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </form>
          </div>

          <p className="text-center text-xs text-ink-muted">
            Private workspace · NYC TLC data · Ground truth only
          </p>
        </div>
      </div>
    </div>
  );
}
