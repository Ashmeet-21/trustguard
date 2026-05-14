"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";

export default function Navbar() {
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();

  const links = [
    { href: "/", label: "Home" },
    { href: "/verify", label: "Verify" },
    { href: "/dashboard", label: "Dashboard" },
  ];

  return (
    <nav className="sticky top-0 z-50 border-b border-white/[0.04]">
      <div className="absolute inset-0 bg-[#050508]/80 backdrop-blur-2xl" />
      <div className="relative flex items-center justify-between px-8 py-3.5 max-w-7xl mx-auto">
        <Link href="/" className="flex items-center gap-2.5 group">
          {/* Animated logo mark */}
          <div className="relative w-8 h-8">
            <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-[#00d4ff] to-[#7b2ff7] opacity-80 group-hover:opacity-100 transition-opacity" />
            <div className="absolute inset-[2px] rounded-[6px] bg-[#050508] flex items-center justify-center">
              <span className="text-xs font-bold gradient-text">TG</span>
            </div>
          </div>
          <span className="text-base font-semibold text-white/90 tracking-tight">
            TrustGuard
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {links.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`relative px-4 py-2 rounded-lg text-[13px] font-medium transition-all duration-300 ${
                  isActive
                    ? "text-white"
                    : "text-white/40 hover:text-white/70"
                }`}
              >
                {isActive && (
                  <span className="absolute inset-0 rounded-lg bg-white/[0.06] border border-white/[0.08]" />
                )}
                <span className="relative">{link.label}</span>
              </Link>
            );
          })}
          <div className="w-px h-5 bg-white/[0.06] mx-2" />
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3.5 py-1.5 rounded-lg text-[13px] font-medium text-white/30 hover:text-white/60 transition-all duration-300 flex items-center gap-1.5"
          >
            API
            <svg width="10" height="10" viewBox="0 0 12 12" fill="none" className="opacity-50">
              <path d="M3.5 1.5H10.5V8.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M10.5 1.5L1.5 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </a>
          <div className="w-px h-5 bg-white/[0.06] mx-2" />
          {!loading && (
            user ? (
              <div className="flex items-center gap-3">
                <span className="text-[12px] text-white/30 max-w-[140px] truncate">
                  {user.full_name || user.email}
                </span>
                <button
                  onClick={logout}
                  className="px-3.5 py-1.5 rounded-lg text-[13px] font-medium text-white/30 hover:text-white/60 transition-all duration-300 border border-white/[0.06] hover:border-white/[0.12]"
                >
                  Logout
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className={`relative px-4 py-2 rounded-lg text-[13px] font-medium transition-all duration-300 ${
                  pathname === "/login"
                    ? "text-white"
                    : "text-white/40 hover:text-white/70"
                }`}
              >
                {pathname === "/login" && (
                  <span className="absolute inset-0 rounded-lg bg-white/[0.06] border border-white/[0.08]" />
                )}
                <span className="relative">Login</span>
              </Link>
            )
          )}
        </div>
      </div>
    </nav>
  );
}
