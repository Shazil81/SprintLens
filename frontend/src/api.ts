export type User = {
  id: number;
  name: string;
  username: string;
  role: "Manager" | "Developer" | "Admin";
  membership_id: number;
  organization: { id: number; name: string };
};
export type Member = {
  id: number;
  user_id: number;
  name: string;
  role: User["role"];
};
export type Project = {
  id: number;
  name: string;
  code: string;
  description: string;
  due: string;
  color: string;
  member_ids: number[];
  reviewer_ids: number[];
  version: number;
  team?: string;
};
export type ApiTask = {
  complexity: string;
  complexity_context: string;
  id: string;
  code: string;
  title: string;
  project: number;
  project_name: string;
  assignee: number;
  assignee_name: string;
  status: string;
  priority: string;
  due: string;
  version: number;
  acceptance_criteria: string;
  milestone: number | null;
  dependency_ids: string[];
};
export type Milestone = {
  id: number;
  project: number;
  title: string;
  kind: "Milestone" | "Sprint";
  start: string;
  due: string;
  version: number;
  completed: number;
  total: number;
};
export type Review = {
  assessment: import("./types/insights").Assessment | null;
  id: number;
  project: number;
  subject: number;
  subject_name: string;
  reviewer: number;
  reviewer_name: string;
  cycle: string;
  period_start: string;
  period_end: string;
  strengths: string;
  improvements: string;
  collaboration: string;
  delivery_context: string;
  status: "Draft" | "Published" | "Responded";
  version: number;
  responses: {
    id: number;
    body: string;
    author_name: string;
    created_at: string;
  }[];
};
export type Goal = {
  id: number;
  project: number;
  owner: number;
  owner_name: string;
  title: string;
  skill: string;
  target_date: string;
  status: string;
  version: number;
  entries: {
    id: number;
    author_name: string;
    kind: string;
    body: string;
    created_at: string;
  }[];
};
export type GitConnection = {
  id: string;
  project: number;
  repository: string;
  enabled: boolean;
  event_count: number;
  delivery_count: number;
  last_delivery_at: string | null;
};
export type GitActivity = {
  id: number;
  project: number;
  repository: string;
  task: string | null;
  event: string;
  title: string;
  actor: string;
  url: string;
  at: string;
};
export type InboxItem = {
  id: number;
  project: number;
  kind: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
};
export type WorkUpdate = {
  id: number;
  author: string;
  kind: "Update" | "Feedback";
  body: string;
  evidence_url: string;
  created_at: string;
};
export type Blocker = {
  id: number;
  reporter: string;
  reporter_user_id: number;
  owner: number;
  owner_name: string;
  reason: string;
  opened_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution: string;
};
let csrfToken = "";
function currentCsrfToken() {
  // Django's CSRF cookie is readable by design; the authentication cookie remains HttpOnly.
  // Read it for each request so hot reloads and login token rotation cannot leave a stale header.
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith("sprintlens_csrftoken="));
  return cookie ? cookie.slice("sprintlens_csrftoken=".length) : csrfToken;
}
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = currentCsrfToken();
  let response: Response;
  try {
    response = await fetch(`/api/v1/${path}`, {
      ...options,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "X-CSRFToken": token } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Cannot reach the server. Check that the backend is running.",
      0,
    );
  }
  const content = await response.text();
  let value;
  try {
    value = content ? JSON.parse(content) : {};
  } catch {
    throw new ApiError(
      "The API did not return JSON. Check the backend and API proxy.",
      response.status,
    );
  }
  if (!response.ok) {
    const message =
      value.detail ||
      Object.entries(value)
        .map(
          ([key, item]) =>
            `${key}: ${Array.isArray(item) ? item.join(" ") : item}`,
        )
        .join(" · ");
    throw new ApiError(
      message || "Request failed. Please try again.",
      response.status,
    );
  }
  if (value.csrfToken) csrfToken = value.csrfToken;
  return value as T;
}
export const session = () => request<{ user: User | null }>("auth/session/");
export const signIn = async (username: string, password: string) => {
  // Refresh the CSRF cookie before authentication after long idle periods or cookie changes.
  await session();
  return request<{ user: User }>("auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
};
export const signOut = () =>
  request("auth/logout/", { method: "POST", body: "{}" });

export async function listAll<T>(path: string): Promise<T[]> {
  const values: T[] = [];
  let page = 1;
  // Read every page so workspace metrics do not silently describe only page one.
  while (true) {
    const result = await request<{ results: T[]; next: string | null }>(
      `${path}${path.includes("?") ? "&" : "?"}page=${page}`,
    );
    values.push(...result.results);
    if (!result.next) return values;
    page += 1;
  }
}
