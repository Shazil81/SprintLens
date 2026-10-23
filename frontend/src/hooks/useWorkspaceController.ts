import { closeDialogAnimated } from "../utils/dialogMotion";
import React, { useEffect, useRef, useState } from "react";
import {
  request,
  signOut,
  listAll,
  type User,
  type Member,
  type Project,
  type ApiTask,
} from "../api";
import { type Task, type Status, type Audit } from "../data";
import { dateKey, type View } from "../utils/workspace";

/** Owns workspace data, filters, form state, and API mutations. */
export function useWorkspaceController(user: User, onLogout: () => void) {
  // Keep server resources separate from temporary UI controls and form values.
  const [data, setData] = useState<{ tasks: Task[]; audit: Audit[] }>({
    tasks: [],
    audit: [],
  });
  const [projects, setProjects] = useState<Project[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [detailTaskId, setDetailTaskId] = useState<string | null>(null);
  const people = members.map((m) => m.name);
  const role = user.role === "Admin" ? "Manager" : user.role;
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [formProject, setFormProject] = useState("");
  const [formError, setFormError] = useState("");
  const [formAssignee, setFormAssignee] = useState("");
  const eligibleMembers = members.filter((m) =>
    projects
      .find((p) => String(p.id) === formProject)
      ?.member_ids.includes(m.id),
  );
  // Fetch independent resources together, then map API IDs to display values.
  async function reload() {
    const [tasks, audit, projectList, memberList] = await Promise.all([
      listAll<ApiTask>("tasks/"),
      listAll<Audit>("audit-events/"),
      listAll<Project>("projects/"),
      listAll<Member>("members/"),
    ]);
    setData({
      tasks: tasks.map((t) => ({
        ...t,
        apiId: t.id,
        id: t.code,
        projectId: t.project,
        assigneeId: t.assignee,
        project: t.project_name,
        assignee: t.assignee_name,
        status: t.status as Status,
      })),
      audit,
    });
    setProjects(projectList);
    setMembers(memberList);
  }
  useEffect(() => {
    reload()
      .catch((e) => setNotice(e.message))
      .finally(() => setLoading(false));
  }, []);
  // Refresh all panels together when the user asks for the latest server state.
  async function refresh() {
    setLoading(true);
    try {
      await reload();
      setNotice("Workspace refreshed.");
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Refresh failed.");
    } finally {
      setLoading(false);
    }
  }
  // Clear the server session before asking App to show the login screen.
  async function logout() {
    try {
      await signOut();
      onLogout();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Sign-out failed.");
    }
  }
  // Reset project-dependent form selections before opening the native dialog.
  function openTask() {
    const p = projects[0];
    setFormProject(p ? String(p.id) : "");
    setFormAssignee(p?.member_ids[0] ? String(p.member_ids[0]) : "");
    setFormError("");
    dialog.current?.showModal();
  }
  const [view, setView] = useState<View>("Overview");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All statuses");
  const [projectFilter, setProjectFilter] = useState("All projects");
  const [notice, setNotice] = useState("");
  const [help, setHelp] = useState(false);
  const [selectedDay, setSelectedDay] = useState(dateKey(new Date()));
  const week = Array.from({ length: 7 }, (_, i) => {
    const day = new Date();
    day.setDate(day.getDate() + i);
    return day;
  });
  const dialog = useRef<HTMLDialogElement>(null);
  const creator = useRef<HTMLButtonElement>(null);
  // These filters control display; authorization is still enforced by Django.
  const scoped = data.tasks.filter(
    (t) => role === "Manager" || t.assigneeId === user.membership_id,
  );
  const visible = scoped.filter(
    (t) =>
      `${t.id} ${t.title} ${t.project} ${t.assignee}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (filter === "All statuses" || t.status === filter) &&
      (projectFilter === "All projects" ||
        String(t.projectId) === projectFilter),
  );
  const done = scoped.filter((t) => t.status === "Done").length;
  const blocked = scoped.filter((t) => t.status === "Blocked");
  const review = scoped.filter((t) => t.status === "In review").length;
  // Reset filters when switching sections so old searches do not hide new content.
  function go(next: View) {
    setView(next);
    window.scrollTo({ top: 0, behavior: "instant" });
    setQuery("");
    setFilter("All statuses");
    setProjectFilter("All projects");
  }
  // Send the current version so the server can reject stale edits.
  async function changeStatus(task: Task, status: Status) {
    if (task.status === status || busy) return;
    setBusy(true);
    try {
      await request("tasks/" + task.apiId + "/", {
        method: "PATCH",
        body: JSON.stringify({ status, version: task.version }),
      });
      await reload();
      setNotice(task.id + " updated to " + status + ".");
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Update failed.");
      await reload().catch(() => {});
    } finally {
      setBusy(false);
    }
  }
  // Persist the task first; reload also retrieves the server-generated audit event.
  async function createTask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setBusy(true);
    setFormError("");
    try {
      await request("tasks/", {
        method: "POST",
        body: JSON.stringify({
          title: String(form.get("title")).trim(),
          project: Number(form.get("project")),
          assignee: Number(form.get("assignee")),
          priority: form.get("priority"),
          due: form.get("due"),
          acceptance_criteria: form.get("criteria"),
        }),
      });
      formElement.reset();
      void closeDialogAnimated(dialog.current);
      go("Tasks");
      setNotice("Task saved. Refreshing workspace…");
      await reload();
      setNotice("Task created and audit event recorded.");
    } catch (e) {
      const message = e instanceof Error ? e.message : "Task creation failed.";
      if (dialog.current?.open) setFormError(message);
      else setNotice(message);
    } finally {
      setBusy(false);
    }
  }
  // Open the authenticated report workflow so preview and downloads use the same server snapshot.
  function exportReport() {
    go("Reports");
  }
  return {
    user,
    data,
    projects,
    members,
    people,
    role,
    busy,
    loading,
    formProject,
    setFormProject,
    formError,
    formAssignee,
    setFormAssignee,
    eligibleMembers,
    refresh,
    logout,
    openTask,
    view,
    setView,
    query,
    setQuery,
    filter,
    setFilter,
    projectFilter,
    setProjectFilter,
    notice,
    setNotice,
    help,
    setHelp,
    selectedDay,
    setSelectedDay,
    week,
    dialog,
    creator,
    scoped,
    visible,
    done,
    blocked,
    review,
    go,
    changeStatus,
    createTask,
    exportReport,
    detailTaskId,
    setDetailTaskId,
    reload,
  };
}
