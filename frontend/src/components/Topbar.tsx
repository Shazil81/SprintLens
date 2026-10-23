import { Bell, RefreshCw } from "lucide-react";
import { initials } from "../utils/workspace";
import { useWorkspace } from "../hooks/useWorkspace";
/** Provides inbox, refresh and account controls in the navigation header. */
export function Topbar() {
 const { refresh, loading, user, go } = useWorkspace();
 return <div className="topbar">
 <div className="top-actions"><button className="round-action" aria-label="Notifications" title="Notifications" onClick={() => go("Notifications")}><Bell size={19}/></button><button className="round-action" aria-label="Refresh workspace" title="Refresh workspace" onClick={refresh} disabled={loading}><RefreshCw size={18}/></button><button type="button" className="header-person profile-trigger" aria-label="Open my profile" title="My profile" onClick={() => go("Profile")}><span className="avatar">{initials(user.name)}</span><div><b>{user.name}</b><small>{user.role} · {user.organization.name}</small></div></button></div></div>;
}
