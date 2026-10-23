import { useLayoutEffect, useRef } from "react";

/** Animate view changes without remounting content or replaying on data refresh. */
export function usePageTransition(view: string) {
  const pageRef = useRef<HTMLElement>(null);
  useLayoutEffect(() => {
    const element = pageRef.current;
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!element || preference.matches || typeof element.animate !== "function") return;
    const animation = element.animate(
      [
        { opacity: 0, transform: "translateY(10px)" },
        { opacity: 1, transform: "translateY(0)" },
      ],
      { duration: 240, easing: "cubic-bezier(0.22, 1, 0.36, 1)" },
    );
    const stopForReducedMotion = () => { if (preference.matches) animation.cancel(); };
    preference.addEventListener("change", stopForReducedMotion);
    // Rapid navigation cancels the previous animation instead of queuing effects.
    return () => {
      animation.cancel();
      preference.removeEventListener("change", stopForReducedMotion);
    };
  }, [view]);
  return pageRef;
}
