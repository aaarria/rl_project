"use client";

import {
  BookOpen,
  CalendarClock,
  Droplets,
  FlaskConical,
  GitCompare,
  Home,
  LayoutDashboard,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { API_URL } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Home", icon: Home },
  { href: "/plan", label: "Plan a Drive", icon: CalendarClock },
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/inventory", label: "Inventory", icon: Droplets },
  { href: "/compare", label: "Policies", icon: GitCompare },
  { href: "/lab", label: "Simulation Lab", icon: FlaskConical },
  { href: "/data-quality", label: "Data Quality", icon: ShieldCheck },
  { href: "/methodology", label: "Methodology", icon: BookOpen },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex gap-1 md:flex-col">
      {NAV.map((item) => {
        const active =
          item.href === "/"
            ? pathname === "/"
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap border-b-2 px-3 py-2 text-sm md:border-b-0 md:border-l-2 md:px-4",
              active
                ? "border-burgundy text-white md:bg-white/5"
                : "border-transparent text-white/65 hover:text-white",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/health`)
      .then((response) => {
        if (!cancelled) setOnline(response.ok);
      })
      .catch(() => {
        if (!cancelled) setOnline(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-paper text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-black/20 bg-ink text-paper md:flex">
        <div className="px-5 pb-4 pt-6">
          <Link href="/" className="block">
            <p className="font-serif text-xl leading-tight">Adaptive scheduling</p>
            <p className="mt-1 text-xs text-white/55">Plan donation drives</p>
          </Link>
        </div>
        <NavLinks />
        <div className="mt-auto space-y-2 px-5 py-5 text-xs text-white/55">
          <p className="flex items-center gap-2">
            <span className={cn("h-1.5 w-1.5 rounded-full", online ? "bg-emerald-300" : "bg-burgundy")} />
            {online == null ? "Checking API" : online ? "API connected" : "API unreachable"}
          </p>
          <p>Simulated stock and turnout. Not a clinical scheduling system.</p>
        </div>
      </aside>
      <div className="md:pl-60">
        <header className="sticky top-0 z-20 border-b border-line bg-ink text-paper md:hidden">
          <div className="px-4 py-3">
            <p className="font-serif text-lg leading-none">Adaptive scheduling</p>
            <p className="mt-1 text-[11px] text-white/55">Plan donation drives</p>
          </div>
          <div className="overflow-x-auto px-2 pb-2">
            <NavLinks />
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}
