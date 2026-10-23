export type Assessment = {
  rubric: Record<string, string>;
  updated_at: string;
  evidence_snapshot: {
    captured_at: string;
    period_start: string;
    period_end: string;
    tasks: {
      id: string;
      code: string;
      title: string;
      assignee: string;
      status: string;
      due: string;
      acceptance_criteria: string;
      complexity: string;
      complexity_context: string;
      blocked_hours_in_period: number;
      links: { source: string; url: string; at: string }[];
    }[];
  };
};
export type Analytics = {
  period: { start: string; end: string; days: number };
  snapshot: {
    projects: number;
    tasks: number;
    open: number;
    done: number;
    overdue: number;
    blocked: number;
  };
  delivery: {
    completion_events: number;
    unique_completed_tasks: number;
    median_start_to_accept_hours: number | null;
    timed_events: number;
    blocked_task_hours: number;
    linked_evidence_tasks: number;
  };
  trend: { date: string; completions: number }[];
  projects: {
    id: number;
    name: string;
    due: string;
    total: number;
    done: number;
    open: number;
    risk_count: number;
    status: string;
    past_deadline: boolean;
  }[];
  workload: {
    member_id: number;
    name: string;
    open: number;
    overdue: number;
    blocked: number;
    complexity: Record<string, number>;
  }[];
  risks: {
    task_id: string;
    code: string;
    title: string;
    project: string;
    assignee: string;
    due: string;
    severity: string;
    signals: string[];
  }[];
  risk_total: number;
  milestones: {
    id: number;
    title: string;
    project: string;
    due: string;
    open_tasks: number;
    overdue: boolean;
  }[];
  recurring_blockers: {
    project_id: number;
    description: string;
    task_count: number;
  }[];
  notes: string[];
};
export type KnowledgeSummary = {
  id: number;
  project: number;
  author: number;
  author_name: string;
  title: string;
  summary: string;
  tags: string[];
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
};
export type KnowledgeArticle = KnowledgeSummary & { content: string };
export type ArticleRevision = {
  id: number;
  version: number;
  editor_name: string;
  at: string;
  snapshot: Pick<
    KnowledgeArticle,
    "title" | "summary" | "content" | "tags" | "status"
  >;
};
