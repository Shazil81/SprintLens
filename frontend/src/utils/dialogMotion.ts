// Keep the native modal open during dismissal so focus and backdrop stay intact.
const closingDialogs = new WeakSet<HTMLDialogElement>();
export async function closeDialogAnimated(dialog: HTMLDialogElement | null) {
  if (!dialog?.open || closingDialogs.has(dialog)) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || !dialog.animate) {
    dialog.close();
    return;
  }
  closingDialogs.add(dialog);
  const animation = dialog.animate(
    [{ opacity: 1, transform: "translateY(0) scale(1)" },
     { opacity: 0, transform: "translateY(8px) scale(.98)" }],
    { duration: 160, easing: "ease-in", fill: "forwards" },
  );
  try { await animation.finished; } catch { /* Cancellation still completes dismissal. */ }
  finally {
    if (dialog.open) dialog.close();
    animation.cancel();
    closingDialogs.delete(dialog);
  }
}
