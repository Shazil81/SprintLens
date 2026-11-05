import { useEffect, useState } from "react";
import { request } from "../api";

export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

/** Fetch one authorized page; cancel obsolete filters instead of showing stale results. */
export function usePagedData<T>(path: string, revision = 0) {
  const [state, setState] = useState<{
    path: string;
    page: Page<T> | null;
    error: string;
    loading: boolean;
  }>({ path, page: null, error: "", loading: true });
  useEffect(() => {
    const controller = new AbortController();
    setState({ path, page: null, error: "", loading: true });
    request<Page<T>>(path, { signal: controller.signal })
      .then((page) => {
        if (!controller.signal.aborted)
          setState({ path, page, error: "", loading: false });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({ path, page: null, error: error.message, loading: false });
      });
    return () => controller.abort();
  }, [path, revision]);
  return state.path === path
    ? state
    : { path, page: null, error: "", loading: true };
}
