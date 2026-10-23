import { useEffect, useState } from "react";
import { request } from "../api";
import type { Analytics } from "../types/insights";

/** Ignore late responses when filters change or the view unmounts. */
export function useAnalytics(project: string, days: string) {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setData(null);
    request<Analytics>(
      `analytics/?days=${days}${project ? `&project=${project}` : ""}`,
    )
      .then((value) => {
        if (active) setData(value);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [project, days, revision]);
  return { data, error, loading, refresh: () => setRevision((v) => v + 1) };
}
