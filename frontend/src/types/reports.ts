export type ProjectSnapshot = {
  schema_version: number;
  captured_at: string;
  project: { name: string; code: string; due: string };
  period: { start: string; end: string; days: number };
  current: {
    total: number;
    done: number;
    open: number;
    blocked: number;
    overdue: number;
  };
  observed: {
    completion_events: number;
    unique_completed_tasks: number;
    work_updates: number;
    github_activities: number;
    recurring_blocker_groups: number;
  };
  tasks: {
    code: string;
    title: string;
    status: string;
    due: string;
    signals: string[];
  }[];
  omitted_tasks: number;
  milestones: { title: string; kind: string; start: string; due: string }[];
  limitations: string[];
};
export type ProjectReport = {
  id: string;
  project: number;
  creator: number;
  title: string;
  summary: string;
  achievements: string;
  risks: string;
  next_steps: string;
  snapshot: ProjectSnapshot;
  status: "Draft" | "Published";
  version: number;
  created_at: string;
  published_at: string | null;
};
export type InsightOutput = {
  summary: string;
  findings: { kind: string; text: string; evidence_ids: string[] }[];
  limitations: string[];
};
export type InsightRun = {
  id: string;
  project: number;
  creator: number;
  provider: string;
  model: string;
  status: "Prepared" | "Generating" | "Ready" | "Failed";
  input_snapshot: {
    period: ProjectSnapshot["period"];
    captured_at: string;
    evidence: Record<string, unknown>;
    limitations: string[];
    omitted_tasks: number;
  };
  input_hash: string;
  output: InsightOutput | Record<string, never>;
  error: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};
export type AIConfiguration = {
  provider: string;
  model: string;
  configured: boolean;
  daily_limit: number;
  message: string;
};
