import {
  LayoutDashboard,
  FolderKanban,
  ListTodo,
  Users,
  ShieldCheck,
  CalendarRange,
  MessagesSquare,
  TrendingUp,
  Github,
  Bell,
  BarChart3,
  Scale,
  BookOpen,
  Sparkles,
  FileText,
} from "lucide-react";

// Shared view definitions and pure formatters keep rendering components small.
export type View =
  | "Insights"
  | "Reports"
  | "Analytics"
  | "Evaluation"
  | "Knowledge"
  | "Overview"
  | "Projects"
  | "Tasks"
  | "Planning"
  | "Reviews"
  | "Growth"
  | "GitHub"
  | "Notifications"
  | "Team"
  | "Audit trail";
export const nav = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Projects", icon: FolderKanban },
  { name: "Tasks", icon: ListTodo },
  { name: "Planning", icon: CalendarRange },
  { name: "Reviews", icon: MessagesSquare },
  { name: "Growth", icon: TrendingUp },
  { name: "Analytics", icon: BarChart3 },
  { name: "Evaluation", icon: Scale },
  { name: "Knowledge", icon: BookOpen },
  { name: "Insights", icon: Sparkles },
  { name: "Reports", icon: FileText },
  { name: "GitHub", icon: Github },
  { name: "Notifications", icon: Bell },
  { name: "Team", icon: Users },
  { name: "Audit trail", icon: ShieldCheck },
] as const;
// Build compact avatar labels from a person's display name.
export const initials = (name: string) =>
  name
    .split(" ")
    .map((n) => n[0])
    .join("");
// Map status labels to the CSS class names used by badges and deadline markers.
export const slug = (value: string) => value.toLowerCase().replaceAll(" ", "-");
// Produce a local date-only key without converting midnight to another timezone.
export const dateKey = (date: Date) =>
  [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
// Disable impossible UI transitions; Django independently enforces the same rules.
export const transitionMap: Record<string, string[]> = {
  "To do": ["In progress", "Blocked"],
  "In progress": ["To do", "In review", "Blocked"],
  "In review": ["In progress", "Done", "Blocked"],
  Blocked: ["To do", "In progress"],
  Done: ["In progress"],
};
