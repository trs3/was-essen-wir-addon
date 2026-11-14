const dateLabel = (day: string) => new Date(day + 'T12:00:00').toLocaleDateString('de-DE', {
  weekday: 'long', day: 'numeric', month: 'long',
});

export function conflictTiming(day: string, today: string): string {
  const days = Math.round((Date.parse(day + 'T12:00:00Z') - Date.parse(today + 'T12:00:00Z')) / 86400000);
  const label = dateLabel(day);
  if (days < 0) return `Am ${label} war es außerdem eingeplant.`;
  if (days === 0) return `Heute (${label}) ist es noch einmal eingeplant.`;
  if (days === 1) return `Morgen (${label}) ist es noch einmal eingeplant.`;
  return `In ${days} Tagen (${label}) ist es noch einmal eingeplant.`;
}

export function CookingConflictDialog({dishName, cookedDay, plannedDay, today, busy, error, onReplace, onKeep}: {
  dishName: string; cookedDay: string; plannedDay: string; today: string;
  busy: boolean; error: string; onReplace: () => void; onKeep: () => void;
}) {
  return <div className="modal-backdrop">
    <section className="modal cooking-conflict" role="dialog" aria-modal="true" aria-labelledby="cooking-conflict-title" aria-describedby="cooking-conflict-description">
      <div className="section-title"><h2 id="cooking-conflict-title">Noch einmal eingeplant</h2></div>
      <div id="cooking-conflict-description">
        <p>Du hast <strong>„{dishName}“</strong> am {dateLabel(cookedDay)} gekocht.</p>
        <p>{conflictTiming(plannedDay, today)}</p>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="cooking-conflict-actions">
        <button type="button" className="primary" disabled={busy} onClick={onReplace}>Neuen Vorschlag machen</button>
        <button type="button" disabled={busy} onClick={onKeep}>Passt</button>
      </div>
    </section>
  </div>;
}
