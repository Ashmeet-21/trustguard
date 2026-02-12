"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();

  const links = [
    { href: "/", label: "Home" },
    { href: "/verify", label: "Verify" },
    { href: "/dashboard", label: "Dashboard" },
  ];

  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between px-8 py-4 border-b border-[#1a1a1a] bg-[#0a0a0a]/90 backdrop-blur-md">
      <Link href="/" className="text-xl font-bold gradient-text">
        TrustGuard
      </Link>

      <div className="flex gap-2">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`px-4 py-2 rounded-lg text-sm transition-all ${
              pathname === link.href
                ? "text-white bg-[#1a1a1a]"
                : "text-[#999] hover:text-white hover:bg-[#1a1a1a]"
            }`}
          >
            {link.label}
          </Link>
        ))}
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 rounded-lg text-sm text-[#999] hover:text-white hover:bg-[#1a1a1a] transition-all"
        >
          API Docs
        </a>
      </div>
    </nav>
  );
}
