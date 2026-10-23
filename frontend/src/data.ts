export const statuses = [
  "To do",
  "In progress",
  "In review",
  "Blocked",
  "Done",
] as const;
export type Status = (typeof statuses)[number];
export type Task = {
  id: string;
  apiId?: string;
  projectId?: number;
  assigneeId?: number;
  version?: number;
  milestone?: number | null;
  title: string;
  project: string;
  assignee: string;
  status: Status;
  priority: string;
  due: string;
};
export type Audit = { id: string; actor: string; text: string; at: string };
