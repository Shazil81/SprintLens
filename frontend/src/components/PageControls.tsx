export function PageControls({ page, previous, next, disabled, onChange }: {
  page: number; previous: boolean; next: boolean; disabled: boolean; onChange: (page: number) => void;
}) {
  return <nav className="page-controls" aria-label="Result pages">
    <button className="button secondary" disabled={disabled || !previous} onClick={() => onChange(page - 1)}>Previous</button>
    <span aria-live="polite">Page {page}</span>
    <button className="button secondary" disabled={disabled || !next} onClick={() => onChange(page + 1)}>Next</button>
  </nav>;
}
