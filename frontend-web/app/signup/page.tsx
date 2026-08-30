"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { NycOrbit } from "@/components/login/NycOrbit";
import { useAuth } from "@/context/AuthContext";
import { signup } from "@/lib/api";
import { UserPlus } from "lucide-react";

export default function SignupPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setSubmitting(true);
    try {
      await signup(email, password);
      await refresh();
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-10 lg:grid-cols-2 lg:items-center">
      <NycOrbit className="hidden lg:block" />

      <div className="mx-auto flex w-full max-w-md flex-col gap-8">
        <section className="flex flex-col gap-3">
          <span className="font-label-sm text-brass tracking-wider">Account</span>
          <h1 className="font-display-lg text-ink-primary">Sign up</h1>
        </section>

        <Card className="p-8">
          <div className="flex items-start gap-4 mb-6">
            <div className="p-3 bg-brass/10 rounded-sm">
              <UserPlus className="h-5 w-5 text-brass" />
            </div>
            <CardTitle className="font-section-lg">Create an account</CardTitle>
          </div>

          <div className="separator-line mb-6" />

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div className="flex flex-col gap-2">
              <label htmlFor="email" className="font-section-md text-ink-primary">Email</label>
              <Input id="email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor="password" className="font-section-md text-ink-primary">Password</label>
              <Input id="password" type="password" required minLength={8} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <p className="font-body-sm text-ink-secondary">At least 8 characters</p>
            </div>

            {error && <p className="font-body-sm text-danger">{error}</p>}

            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? "Creating account..." : "Sign up"}
            </Button>
          </form>

          <p className="font-body-sm text-ink-secondary mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-brass hover:underline">
              Log in
            </Link>
          </p>
        </Card>
      </div>
    </div>
  );
}
