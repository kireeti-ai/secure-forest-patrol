"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { fetchGateways } from "../../lib/api";
import { Notifications } from "./Notifications";

type TopbarProps = {
  sidebarOpen: boolean;
  onMenuClick: () => void;
};

const routeTitles: Record<string, string> = {
  "/dashboard": "Overview",
  "/dashboard/checkpoints": "Checkpoints",
  "/dashboard/patrols": "Patrols",
  "/dashboard/officers": "Officers",
  "/dashboard/acoustic-events": "Acoustic events",
  "/dashboard/ledger": "Ledger",
  "/dashboard/gateway": "Gateway",
  "/dashboard/nodes": "Field nodes",
  "/dashboard/sync-history": "Sync history",
  "/dashboard/system-status": "System status",
  "/dashboard/rfid-events": "RFID scans",
};

export function Topbar({ sidebarOpen, onMenuClick }: TopbarProps) {
  const pathname = usePathname();
  const [gatewayStatus, setGatewayStatus] = useState<"ONLINE" | "OFFLINE" | "UNKNOWN">("UNKNOWN");
  const [lastSync, setLastSync] = useState<string>("Unavailable");

  const pageTitle = routeTitles[pathname] || (pathname.startsWith("/dashboard/patrols/") ? "Patrol record" : pathname.startsWith("/dashboard/acoustic-events/") ? "Acoustic event" : "Overview");

  useEffect(() => {
    let mounted = true;

    async function checkStatus() {
      const gateways = await fetchGateways();
      if (!mounted) return;
      const gateway = gateways[0];
      if (gateway) {
        setGatewayStatus(gateway.status);
        if (!gateway.lastSeen) {
          setLastSync("Never");
        } else {
          const latestTime = new Date(gateway.lastSeen);
          const diffSeconds = Math.floor((Date.now() - latestTime.getTime()) / 1000);
          if (diffSeconds < 5) {
            setLastSync("Just now");
          } else if (diffSeconds < 60) {
            setLastSync(`${diffSeconds}s ago`);
          } else if (diffSeconds < 3600) {
            setLastSync(`${Math.floor(diffSeconds / 60)}m ago`);
          } else {
            setLastSync(`${Math.floor(diffSeconds / 3600)}h ago`);
          }
        }
      } else {
        setGatewayStatus("UNKNOWN");
        setLastSync("Never");
      }
    }

    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="topbar">
      <button
        className={`menu-button${sidebarOpen ? " menu-button-open" : ""}`}
        type="button"
        aria-label={sidebarOpen ? "Close navigation" : "Open navigation"}
        aria-expanded={sidebarOpen}
        onClick={onMenuClick}
      >
        <span aria-hidden="true" className="menu-line" />
        <span aria-hidden="true" className="menu-line" />
        <span aria-hidden="true" className="menu-line" />
      </button>

      <div className="topbar-page">{pageTitle}</div>

      <div className="topbar-meta" aria-label="Connection status">
        <div className="topbar-status">
          <span className={`status-dot${gatewayStatus === "ONLINE" ? " status-dot-online" : " status-dot-neutral"}`} aria-hidden="true" />
          <span className="topbar-meta-label">Gateway</span>
          <span className="topbar-meta-value">{gatewayStatus === "UNKNOWN" ? "unavailable" : gatewayStatus.toLowerCase()}</span>
        </div>
        <div className="topbar-sync">
          <span className="topbar-meta-label">Last packet</span>
          <span className="topbar-meta-value">{lastSync}</span>
        </div>
        <Notifications />
        <a href="https://github.com/kireeti-ai/secure-forest-patrol" target="_blank" rel="noreferrer" className="topbar-link" title="Source on GitHub">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
          </svg>
          <span>GitHub</span>
        </a>
      </div>
    </header>
  );
}
