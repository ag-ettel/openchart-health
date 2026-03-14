// Annotation rendered at a trend chart period boundary.
// Always visible. Never tooltip-only.
// Obligations: see CLAUDE.md: Frontend Specification: Components: MethodologyChangeFlag

export function MethodologyChangeFlag(): JSX.Element {
  return (
    <div className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
      CMS methodology changed at this point. Values before and after may not be
      directly comparable.
    </div>
  );
}
