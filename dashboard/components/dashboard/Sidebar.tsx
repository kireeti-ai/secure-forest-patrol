"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import type { ReactNode } from "react";
import { session } from "../../lib/rfidApi";
import { ForestLogo } from "../ui/ForestLogo";

type SidebarProps = {
  open: boolean;
  onClose: () => void;
};

type NavigationItem = {
  label: string;
  href: string;
  icon: string;
};

const forestOperations: NavigationItem[] = [
  { label: "Overview", href: "/dashboard", icon: "grid" },
  { label: "Checkpoints", href: "/dashboard/checkpoints", icon: "checkpoint" },
  { label: "Patrol Verification", href: "/dashboard/patrols", icon: "patrol" },
  { label: "Patrol Officers", href: "/dashboard/officers", icon: "officer" },
  { label: "Acoustic Threat Events", href: "/dashboard/acoustic-events", icon: "acoustic" },
  { label: "Ledger Integrity", href: "/dashboard/ledger", icon: "ledger" },
];

const systemInfrastructure: NavigationItem[] = [
  { label: "Gateway Status", href: "/dashboard/gateway", icon: "gateway" },
  { label: "Field Nodes", href: "/dashboard/nodes", icon: "node" },
  { label: "Sync History", href: "/dashboard/sync-history", icon: "sync" },
  { label: "System Status", href: "/dashboard/system-status", icon: "status" },
];

function NavigationIcon({ name }: { name: string }) {
  const common = { fill: "none", stroke: "currentColor", strokeLinecap: "round" as const, strokeLinejoin: "round" as const, strokeWidth: 1.8 };
  const paths: Record<string, ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    checkpoint: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><circle cx="12" cy="11" r="3" /></>,
    patrol: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></>,
    officer: <><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /><path d="M12 11v4" /></>,
    acoustic: <><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="22" /></>,
    ledger: <><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></>,
    gateway: <><path d="M5 20h14M7 17h10M9 14h6M12 4v10M8 8a6 6 0 0 1 8 0M5 5a10 10 0 0 1 14 0" /></>,
    node: <><rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" /><line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" /></>,
    sync: <><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" /></>,
    status: <><circle cx="12" cy="12" r="9" /><path d="m8 12 3 3 5-6" /></>,
    user: <><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></>,
    history: <><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 4v5h5M12 7v5l3 2" /></>,
  };

  return <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true" {...common}>{paths[name] ?? paths.grid}</svg>;
}

function NavigationGroup({ items }: { items: NavigationItem[] }) {
  const pathname = usePathname();

  return (
    <nav className="sidebar-nav" aria-label="Dashboard navigation">
      {items.map((item) => {
        const active = item.href === "/dashboard"
          ? pathname === "/dashboard"
          : pathname === item.href || pathname.startsWith(`${item.href}/`);

        return (
          <Link
            className={`nav-item${active ? " nav-item-active" : ""}`}
            href={item.href}
            aria-current={active ? "page" : undefined}
            key={item.label}
          >
            <NavigationIcon name={item.icon} />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const currentSession = session();
  const rfidNavigation: NavigationItem[] = currentSession?.user.role === "OFFICER"
    ? [{ label: "Live RFID Events", href: "/dashboard/rfid-events", icon: "history" }]
    : currentSession?.user.role === "EMPLOYEE"
      ? [{ label: "My Attendance", href: "/dashboard/my-attendance", icon: "user" }]
      : [];
  return (
    <>
      <button
        className={`sidebar-overlay${open ? " sidebar-overlay-visible" : ""}`}
        type="button"
        aria-label="Close navigation"
        onClick={onClose}
      />
      <aside className={`sidebar${open ? " sidebar-open" : ""}`} aria-label="Forest Patrol Navigation">
        <div className="sidebar-brand">
          <span className="brand-lockup">
            <ForestLogo className="brand-mark" />
            <span className="brand-name">SFP</span>
          </span>
          <span className="brand-subtitle">SECURE FOREST PATROL</span>
        </div>

        <div className="sidebar-groups">
          <div className="sidebar-section-label">OPERATIONS</div>
          <NavigationGroup items={forestOperations} />
          {rfidNavigation.length > 0 && <><div className="sidebar-divider" /><div className="sidebar-section-label">RFID ATTENDANCE</div><NavigationGroup items={rfidNavigation} /></>}
          <div className="sidebar-divider" />
          <div className="sidebar-section-label">INFRASTRUCTURE</div>
          <NavigationGroup items={systemInfrastructure} />
        </div>
      </aside>
    </>
  );
}
