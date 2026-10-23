import { useState } from "react";
import { Zap, CircleHelp, LogOut, ChevronDown } from "lucide-react";
import { Topbar } from "./Topbar";
import { nav } from "../utils/workspace";
import { useWorkspace } from "../hooks/useWorkspace";

const groups = [
  { label: "Projects", items: ["Projects", "Tasks", "Planning"] },
  { label: "People", items: ["Team", "Reviews", "Growth", "Evaluation"] },
  { label: "Insights", items: ["Analytics", "Insights", "Reports"] },
  { label: "Resources", items: ["Knowledge", "GitHub", "Audit trail"] },
];
/** Hover, focus and click disclose related destinations without changing pages. */
export function Navbar() {
  const { view, go, help, setHelp, logout } = useWorkspace();
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  return (
    <div className="workspace-navbar">
      <button className="navbar-brand" aria-label="SprintLens home" onClick={() => go("Overview")}>
        <Zap size={22} fill="currentColor" /><span>SprintLens</span>
      </button>
      <nav className="navbar-links" aria-label="Main navigation">
        <button className={`nav-group-trigger ${view === "Overview" ? "active" : ""}`}
          aria-current={view === "Overview" ? "page" : undefined} onClick={() => { go("Overview"); setOpenGroup(null); }}>
          <Zap size={18} /> Overview
        </button>
        {groups.map((group) => {
          const Icon = nav.find((item) => item.name === group.items[0])!.icon;
          const expanded = openGroup === group.label;
          return <div className="nav-group" key={group.label}
            onMouseEnter={() => setOpenGroup(group.label)} onMouseLeave={() => setOpenGroup(null)}
            onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpenGroup(null); }}
            onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); event.currentTarget.querySelector<HTMLButtonElement>(".nav-group-trigger")?.focus(); setOpenGroup(null); } }}>
            <button className={`nav-group-trigger ${group.items.includes(view) ? "active" : ""}`}
              aria-expanded={expanded} aria-controls={`nav-group-${group.label}`}
              onFocus={() => setOpenGroup(group.label)}
              onClick={(event) => { if (event.detail !== 0) setOpenGroup(group.label); else setOpenGroup(expanded ? null : group.label); }}>
              <Icon size={18}/><span>{group.label}</span><ChevronDown className="nav-group-chevron" size={13}/>
            </button>
            <div className="nav-group-panel" id={`nav-group-${group.label}`} data-open={expanded} aria-hidden={!expanded} inert={!expanded}>
              <span className="nav-group-caption">{group.label}</span>
              {group.items.map((name) => {
                const item = nav.find((entry) => entry.name === name)!;
                const ItemIcon = item.icon;
                return <button key={name} aria-current={view === name ? "page" : undefined}
                  className={view === name ? "active" : ""}
                  onClick={() => { go(item.name); setOpenGroup(null); }}>
                  <ItemIcon size={17}/><span>{name}</span>
                </button>;
              })}
            </div>
          </div>;
        })}
      </nav>
      <div className="navbar-account-actions">
      <Topbar />
      <div className="navbar-utilities">
        <button className="nav-icon" aria-label="About this workspace" onClick={() => setHelp(!help)}>
          <CircleHelp size={19}/><span className="nav-tooltip" aria-hidden="true">Help</span>
        </button>
        <button className="nav-icon logout-icon" aria-label="Sign out" onClick={logout}>
          <LogOut size={19}/><span className="nav-tooltip" aria-hidden="true">Sign out</span>
        </button>
      </div>
      </div>
    </div>
  );
}
