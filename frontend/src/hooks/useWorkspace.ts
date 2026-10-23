import { createContext, useContext } from "react";
import type { useWorkspaceController } from "./useWorkspaceController";

// One typed context shares the controller without passing the same props through every panel.
export const WorkspaceContext = createContext<ReturnType<
  typeof useWorkspaceController
> | null>(null);
export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context)
    throw new Error("Workspace components require a Workspace provider.");
  return context;
}
