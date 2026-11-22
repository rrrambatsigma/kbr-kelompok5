import { BookOpen, History, Home, Info, Stethoscope } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { Footer } from "../components/layout/Footer";
import { Logo } from "../components/common/Logo";

const items = [
  { to: "/", label: "Beranda", icon: Home, end: true },
  { to: "/diagnosis", label: "Diagnosis", icon: Stethoscope },
  { to: "/riwayat", label: "Riwayat", icon: History },
  { to: "/knowledge-base", label: "Knowledge Base", icon: BookOpen },
  { to: "/#tentang", label: "Tentang Kami", icon: Info },
];

export function AppShell() {
  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <div className="flex flex-1 flex-col lg:flex-row">
        <aside className="no-print border-b border-border bg-surface-low lg:min-h-screen lg:w-[17rem] lg:shrink-0 lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between gap-4 px-4 py-4 lg:flex-col lg:items-start lg:px-6 lg:py-7">
            <Logo />
            <nav
              className="hidden flex-col gap-1 lg:flex lg:w-full"
              aria-label="Navigasi aplikasi"
            >
              {items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `sidebar-link ${isActive ? "is-active" : ""}`
                    }
                  >
                    <Icon className="h-5 w-5" aria-hidden="true" />
                    {item.label}
                  </NavLink>
                );
              })}
            </nav>
          </div>
          <nav
            className="hide-scrollbar flex gap-2 overflow-x-auto px-4 pb-3 lg:hidden"
            aria-label="Navigasi aplikasi mobile"
          >
            {items.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className="flex min-h-11 shrink-0 items-center gap-2 rounded-xl border border-border bg-white px-3 text-xs font-semibold text-muted"
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        className={`h-4 w-4 ${
                          isActive ? "text-primary" : ""
                        }`}
                        aria-hidden="true"
                      />
                      <span className={isActive ? "text-primary" : ""}>
                        {item.label}
                      </span>
                    </>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </aside>
        <div className="flex min-w-0 flex-1 flex-col">
          <main className="flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-9">
            <Outlet />
          </main>
          <Footer />
        </div>
      </div>
    </div>
  );
}
