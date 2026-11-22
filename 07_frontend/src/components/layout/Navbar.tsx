import { Menu, X } from "lucide-react";
import { useState } from "react";
import { Link, NavLink } from "react-router-dom";

import { Logo } from "../common/Logo";

const navItems = [
  { to: "/", label: "Beranda", end: true },
  { to: "/diagnosis", label: "Diagnosis" },
  { to: "/riwayat", label: "Riwayat" },
  { to: "/knowledge-base", label: "Knowledge Base" },
];

function linkClass({ isActive }: { isActive: boolean }): string {
  return `rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
    isActive
      ? "bg-surface-low text-primary"
      : "text-muted hover:bg-surface-low hover:text-foreground"
  }`;
}

export function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="no-print sticky top-0 z-50 border-b border-border bg-surface/90 backdrop-blur-xl">
      <div className="container-page flex h-20 items-center justify-between gap-4">
        <Logo />
        <nav className="hidden items-center gap-1 md:flex" aria-label="Navigasi utama">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link to="/diagnosis" className="btn-primary hidden sm:inline-flex">
            Mulai Diagnosis
          </Link>
          <button
            type="button"
            className="btn-ghost h-11 w-11 p-0 md:hidden"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            aria-label={open ? "Tutup menu" : "Buka menu"}
          >
            {open ? (
              <X className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Menu className="h-5 w-5" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>
      {open && (
        <nav
          className="border-t border-border bg-surface px-4 pb-4 pt-2 md:hidden"
          aria-label="Navigasi mobile"
        >
          <div className="flex flex-col gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={linkClass}
                onClick={() => setOpen(false)}
              >
                {item.label}
              </NavLink>
            ))}
            <Link
              to="/diagnosis"
              className="btn-primary mt-2"
              onClick={() => setOpen(false)}
            >
              Mulai Diagnosis
            </Link>
          </div>
        </nav>
      )}
    </header>
  );
}
