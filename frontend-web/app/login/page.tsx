"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { NycOrbit } from "@/components/login/NycOrbit";
import { useAuth } from "@/context/AuthContext";
import { login } from "@/lib/api";
import { ArrowRight, Compass, LockKeyhole } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      await refresh();
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto grid min-h-[calc(100dvh-8rem)] max-w-6xl items-center gap-10 py-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
      <div className="hidden min-h-[38rem] lg:block">
        <NycOrbit className="h-full" />
      </div>

      <div className="mx-auto flex w-full max-w-[30rem] flex-col gap-7">
        <section className="flex flex-col gap-4">
          <div className="flex items-center gap-2 font-label-sm text-brass">
            <Compass className="h-4 w-4" />
            <span>NYC ride intelligence</span>
          </div>
          <h1 className="max-w-md font-display-lg text-ink-primary sm:text-[3.25rem] sm:leading-[1.04]">See the city in motion.</h1>
          <p className="max-w-sm font-body-md text-ink-secondary">Sign in to explore demand, fares, and journeys grounded in real TLC trip records.</p>
        </section>

        <div className="rounded-2xl border border-surface-border bg-surface-1 p-7 shadow-[0_24px_60px_-32px_rgba(28,27,51,0.38)] sm:p-8">
          <div className="mb-7 flex items-start justify-between gap-4">
            <div>
              <p className="font-label-sm text-ink-muted">Account access</p>
              <h2 className="mt-2 font-section-lg text-ink-primary">Welcome back</h2>
            </div>
            <div className="rounded-xl bg-brass/10 p-3 text-brass"><LockKeyhole className="h-5 w-5" /></div>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div className="flex flex-col gap-2">
              <label htmlFor="email" className="font-section-md text-ink-primary">Email</label>
              <Input id="email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor="password" className="font-section-md text-ink-primary">Password</label>
              <Input id="password" type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>

            {error && <p className="font-body-sm text-danger">{error}</p>}

            <Button type="submit" disabled={submitting} className="mt-1 w-full gap-2">
              {submitting ? "Signing in..." : "Continue to ATLAS"}
              {!submitting && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          <p className="font-body-sm text-ink-secondary mt-6">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="text-brass hover:underline">
              Sign up
            </Link>
          </p>
        </div>
        <p className="font-label-sm text-ink-muted">Private workspace · NYC TLC data · Built for exploration</p>
      </div>
    </div>
  );
}
