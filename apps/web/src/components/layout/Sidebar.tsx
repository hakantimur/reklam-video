import { NavLink } from "react-router-dom";

interface NavItem {
  to: string;
  label: string;
}

// Spec §5.1: "Sol menü: Projeler, Stüdyo, Malzemeler, İşler, Ayarlar."
const NAV_ITEMS: NavItem[] = [
  { to: "/projeler", label: "Projeler" },
  { to: "/studyo", label: "Stüdyo" },
  { to: "/malzemeler", label: "Malzemeler" },
  { to: "/isler", label: "İşler" },
  { to: "/ayarlar", label: "Ayarlar" },
];

export function Sidebar() {
  return (
    <nav
      aria-label="Ana gezinme"
      className="flex h-full w-56 shrink-0 flex-col gap-1 border-r border-slate-800 bg-surface/60 p-3"
    >
      <div className="mb-4 px-2 pt-1">
        <p className="text-sm font-semibold tracking-wide text-slate-100">
          Local Ad Director
        </p>
      </div>
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            [
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-accent/20 text-accent"
                : "text-slate-300 hover:bg-slate-800 hover:text-slate-100",
            ].join(" ")
          }
        >
          {({ isActive }) => (
            <span className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className={`h-1.5 w-1.5 rounded-full ${isActive ? "bg-accent" : "bg-slate-600"}`}
              />
              {item.label}
              {isActive ? <span className="sr-only"> (aktif sayfa)</span> : null}
            </span>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
