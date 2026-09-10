import type { ReactNode } from "react";

import { ConnectionBadge } from "../common/ConnectionBadge";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen min-h-screen w-full bg-bg text-slate-100">
      <a
        href="#lad-main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-accent focus:px-3 focus:py-2 focus:text-white"
      >
        İçeriğe geç
      </a>
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-end border-b border-slate-800 bg-surface/40 px-6 py-3">
          <ConnectionBadge />
        </header>
        <main id="lad-main-content" className="flex-1 overflow-y-auto px-8 py-6">
          {children}
        </main>
      </div>
    </div>
  );
}
