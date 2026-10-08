"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";

const LINKS = [
  { href: "/verify", label: "Verify" },
  { href: "/dashboard", label: "Dashboard" },
];

/** Wordmark: a small seal (two concentric rings + check) next to the name */
function Seal() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="7.5" fill="none" stroke="currentColor" strokeWidth="0.75" strokeDasharray="1.2 1.6" />
      <path d="M8.5 12.2l2.3 2.3 4.7-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Navbar() {
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();

  return (
    <header className="border-b border-rule bg-paper">
      <nav className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-4" aria-label="Main">
        <Link href="/" className="flex items-center gap-2 text-seal font-semibold text-[1.0625rem] tracking-tight">
          <Seal />
          <span className="text-ink">TrustGuard</span>
        </Link>

        <div className="flex items-center gap-1 sm:gap-2 text-[0.9375rem]">
          {LINKS.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`px-3 py-2 rounded ${
                  active ? "text-ink font-semibold" : "text-ink-soft hover:text-ink"
                }`}
              >
                {link.label}
              </Link>
            );
          })}

          <span className="w-px h-5 bg-rule mx-1 sm:mx-2" aria-hidden="true" />

          {!loading &&
            (user ? (
              <div className="flex items-center gap-3">
                <span className="hidden md:inline text-sm text-ink-faint max-w-[12rem] truncate">
                  {user.full_name || user.email}
                </span>
                <button onClick={logout} className="px-3 py-2 rounded text-ink-soft hover:text-ink">
                  Sign out
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                aria-current={pathname === "/login" ? "page" : undefined}
                className={`px-3 py-2 rounded ${
                  pathname === "/login" ? "text-ink font-semibold" : "text-ink-soft hover:text-ink"
                }`}
              >
                Sign in
              </Link>
            ))}
        </div>
      </nav>
    </header>
  );
}
