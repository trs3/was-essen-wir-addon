export function PlanLegend({includePast = false}: {includePast?: boolean}) {
  return <div className="plan-legend" aria-label="Planungsstatus">
    <span data-state="suggested">Vorschlag</span>
    <span data-state="confirmed">Eingeplant</span>
    {includePast && <span data-state="overdue">Vergangen · noch nicht als gekocht erfasst</span>}
    <span data-state="cooked">Gekocht</span>
    <span data-state="empty">Bewusst frei</span>
  </div>;
}
