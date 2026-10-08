"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";

type Mode = "login" | "register";

function Field({
  id, label, hint, ...input
}: { id: string; label: string; hint?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-ink mb-1.5">
        {label}
      </label>
      <input id={id} className="field" aria-describedby={hint ? `${id}-hint` : undefined} {...input} />
      {hint && (
        <p id={`${id}-hint`} className="mt-1.5 text-sm text-ink-faint">
          {hint}
        </p>
      )}
    </div>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const { login, register, user } = useAuth();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) router.replace("/verify");
  }, [user, router]);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (mode === "register" && password !== confirmPassword) {
      setError("The two passwords don’t match.");
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, fullName);
      router.push("/verify");
    } catch (err) {
      setError(err instanceof Error ? err.message : mode === "login" ? "Sign-in failed." : "Account could not be created.");
    } finally {
      setSubmitting(false);
    }
  };

  const isLogin = mode === "login";

  return (
    <div className="max-w-6xl mx-auto px-6 py-14 md:py-20 grid md:grid-cols-[1fr_26rem] gap-12 md:gap-20">
      <div className="max-w-md md:pt-4">
        <h1 className="text-[2rem] md:text-[2.5rem] font-bold leading-tight tracking-[-0.02em] text-ink">
          {isLogin ? "Sign in to run a verification" : "Create an account"}
        </h1>
        <p className="mt-4 text-ink-soft">
          An account keeps your verification records private to you. Your selfie and voice sample are
          deleted from TrustGuard’s server as soon as the checks finish, and only the scores and
          decision are kept. The face check sends your selfie to a model hosted on HuggingFace.
        </p>
      </div>

      <div className="sheet p-6 sm:p-8">
        <form onSubmit={handleSubmit} className="space-y-5" noValidate={false}>
          {error && (
            <p className="note note-fail" role="alert">
              <span>{error}</span>
            </p>
          )}

          {!isLogin && (
            <Field id="name" label="Full name" type="text" required autoComplete="name"
              value={fullName} onChange={(e) => setFullName(e.target.value)} />
          )}
          <Field id="email" label="Email" type="email" required autoComplete="email"
            value={email} onChange={(e) => setEmail(e.target.value)} />
          <Field id="password" label="Password" type="password" required
            autoComplete={isLogin ? "current-password" : "new-password"}
            hint={isLogin ? undefined : "At least 12 characters, with an uppercase letter, a lowercase letter, a number and a symbol."}
            value={password} onChange={(e) => setPassword(e.target.value)} />
          {!isLogin && (
            <Field id="confirm" label="Confirm password" type="password" required autoComplete="new-password"
              value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
          )}

          <button type="submit" disabled={submitting} className="btn w-full">
            {submitting ? (isLogin ? "Signing in…" : "Creating account…") : isLogin ? "Sign in" : "Create account"}
          </button>
        </form>

        <p className="mt-6 pt-5 border-t border-rule text-sm text-ink-soft">
          {isLogin ? "No account yet? " : "Already have an account? "}
          <button type="button" className="link font-medium" onClick={() => switchMode(isLogin ? "register" : "login")}>
            {isLogin ? "Create one" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
