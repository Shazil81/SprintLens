import { useEffect, useState } from "react";
import { nav, type View } from "../utils/workspace";

const views: readonly string[] = [...nav.map((item) => item.name), "Profile"];

/** Hash URLs work with Vercel, Nginx and Vite without extra server routes. */
export function readView(hash: string): View {
  const name = views.find(
    (view) => `#/${view.toLowerCase().replaceAll(" ", "-")}` === hash,
  );
  return (name as View) || "Overview";
}

export function useView() {
  const [view, setView] = useState<View>(() => readView(window.location.hash));
  useEffect(() => {
    const sync = () => setView(readView(window.location.hash));
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);
  function navigate(next: View) {
    window.location.hash = `/${next.toLowerCase().replaceAll(" ", "-")}`;
    setView(next);
  }
  return [view, navigate] as const;
}
