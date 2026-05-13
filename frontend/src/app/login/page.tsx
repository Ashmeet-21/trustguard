"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";

export default function LoginPage() {
  const router = useRouter();
  const { login, register, user } = useAuth();

  const [tab, setTab] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // If already logged in, redirect
  useEffect(() => {
    if (user) router.replace("/verify");
  }, [user, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/verify");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setSubmitting(true);
    try {
      await register(email, password, fullName);
      router.push("/verify");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-6">
      <div className="w-full max-w-md fade-up">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="relative w-12 h-12 mx-auto mb-4">
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-[#00d4ff] to-[#7b2ff7] opacity-80" />
            <div className="absolute inset-[2px] rounded-[10px] bg-[#050508] flex items-center justify-center">
              <span className="text-sm font-bold gradient-text">TG</span>
            </div>
          </div>
          <h1 className="text-2xl font-bold text-white/90 tracking-tight">
            {tab === "login" ? "Welcome back" : "Create account"}
          </h1>
          <p className="text-white/25 text-sm mt-1">
            {tab === "login"
              ? "Sign in to access your verification history"
              : "Get started with TrustGuard"}
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="flex rounded-xl p-1 mb-6 bg-white/[0.03] border border-white/[0.06]">
          <button
            onClick={() => { setTab("login"); setError(null); }}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${
              tab === "login"
                ? "bg-white/[0.08] text-white border border-white/[0.08]"
                : "text-white/30 hover:text-white/50"
            }`}
          >
            Login
          </button>
          <button
            onClick={() => { setTab("register"); setError(null); }}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${
              tab === "register"
                ? "bg-white/[0.08] text-white border border-white/[0.08]"
                : "text-white/30 hover:text-white/50"
            }`}
          >
            Register
          </button>
        </div>

        {/* Error */}
        {error && (
          <div
            className="glass rounded-xl p-3 mb-4 text-sm"
            style={{
              background: "rgba(248, 113, 113, 0.04)",
              borderColor: "rgba(248, 113, 113, 0.15)",
            }}
          >
            <span className="text-[#f87171]/80">{error}</span>
          </div>
        )}

        {/* Form */}
        <div className="glass rounded-2xl p-6">
          {tab === "login" ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="text-[11px] uppercase tracking-[0.15em] text-white/20 mb-1.5 block">
                  Email
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-white/80 placeholder-white/15 focus:outline-none focus:border-[#00d4ff]/30 transition-colors"
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label className="text-[11px] uppercase tracking-[0.15em] text-white/20 mb-1.5 block">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-white/80 placeholder-white/15 focus:outline-none focus:border-[#00d4ff]/30 transition-colors"
                  placeholder="Enter your password"
                />
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="w-full btn-glow text-white py-3 rounded-xl text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed mt-2"
              >
                {submitting ? "Signing in..." : "Sign In"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="text-[11px] uppercase tracking-[0.15em] text-white/20 mb-1.5 block">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-white/80 placeholder-white/15 focus:outline-none focus:border-[#00d4ff]/30 transition-colors"
                  placeholder="Your full name"
                />
              </div>
              <div>
                <label className="text-[11px] uppercase tracking-[0.15em] text-white/20 mb-1.5 block">
                  Email
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-white/80 placeholder-white/15 focus:outline-none focus:border-[#00d4ff]/30 transition-colors"
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label className="text-[11px] uppercase tracking-[0.15em] text-white/20 mb-1.5 block">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-white/80 placeholder-white/15 focus:outline-none focus:border-[#00d4ff]/30 transition-colors"
                  placeholder="Min 12 chars, upper, lower, digit, special"
                />
              </div>
              <div>
                <label className="text-[11px] uppercase tracking-[0.15em] text-white/20 mb-1.5 block">
                  Confirm Password
                </label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-white/80 placeholder-white/15 focus:outline-none focus:border-[#00d4ff]/30 transition-colors"
                  placeholder="Re-enter your password"
                />
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="w-full btn-glow text-white py-3 rounded-xl text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed mt-2"
              >
                {submitting ? "Creating account..." : "Create Account"}
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-[11px] text-white/10 mt-6">
          {tab === "login"
            ? "Don't have an account? Click Register above."
            : "Password: 12+ chars with uppercase, lowercase, digit, and special character."}
        </p>
      </div>
    </div>
  );
}
