import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { Car, Gauge, Home, MessageSquare } from "lucide-react";
import { SimulationBadge } from "./ui";

const TABS = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/ask", label: "Ask", icon: MessageSquare, end: false },
  { to: "/drive", label: "Drive", icon: Gauge, end: false },
  { to: "/vehicle", label: "Vehicle", icon: Car, end: false },
] as const;

export function AppShell({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <span className="brand">VehicleGPT</span>
          {title ? <span className="app-header__title">{title}</span> : null}
        </div>
        <div className="app-header__vehicle">
          <span className="app-header__name">VehicleGPT EV Demo</span>
          <span className="app-header__status">DEMO VEHICLE</span>
        </div>
        <SimulationBadge />
      </header>
      <main id="main" className="app-main" tabIndex={-1}>
        {children}
      </main>
      <nav className="bottom-nav" aria-label="Primary">
        {TABS.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className="bottom-nav__item">
            <Icon size={22} strokeWidth={1.75} aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
