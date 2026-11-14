import {useState} from 'react';
import {planState} from './planState';
import {PlanLegend} from './PlanLegend';

type Plan = {day: string; dish_id: number|null; status: string};
type CookingEvent = {id: number; day: string; dish_id: number; version: number};
type Props = {
  today: string;
  plans: Plan[];
  history: CookingEvent[];
  dishes: {id: number; name: string}[];
  busy: boolean;
  onCook: (day: string, dishId: number) => void;
  onChoose: (day: string, event?: CookingEvent) => void;
  onDelete: (event: CookingEvent) => void;
  onAdd: () => void;
};

function previousDay(day: string, offset: number) {
  const date = new Date(day + 'T12:00:00Z');
  date.setUTCDate(date.getUTCDate() - offset);
  return date.toISOString().slice(0, 10);
}

const statusLabels: Record<string, string> = {
  suggested: 'Vorschlag · noch nicht als gekocht erfasst',
  confirmed: 'Eingeplant · noch nicht als gekocht erfasst',
  fixed: 'Eingeplant · noch nicht als gekocht erfasst',
};

export function CookingHistory({today, plans, history, dishes, busy, onCook, onChoose, onDelete, onAdd}: Props) {
  const [visibleDays, setVisibleDays] = useState(7);
  const plansByDay = new Map(plans.map(plan => [plan.day, plan]));
  const historyByDay = new Map(history.map(event => [event.day, event]));
  const dishesById = new Map(dishes.map(dish => [dish.id, dish]));

  const renderedDays = Array.from({length: visibleDays}, (_, index) => previousDay(today, index)).map(day => {
      const plan = plansByDay.get(day), event = historyByDay.get(day);
      const proposed = plan?.dish_id ? dishesById.get(plan.dish_id) : undefined;
      const actual = event ? dishesById.get(event.dish_id) : undefined;
      const date = new Date(day + 'T12:00:00').toLocaleDateString('de-DE', {weekday: 'short', day: 'numeric', month: 'short', year: 'numeric'});
      return <div className="history-row" data-state={planState(day, today, plan?.status, !!event)} key={day}>
        <div className="history-day">
          <time dateTime={day}>{date}</time>
          <strong>{event ? actual?.name || 'Unbekanntes Gericht' : proposed?.name || (plan?.status === 'empty' ? 'Bewusst frei' : 'Kein Vorschlag gespeichert')}</strong>
          <div className="history-meta"><span className={'history-status status ' + (event ? 'cooked' : plan?.status || '')}>
            {event ? '✓ Gekocht' : proposed ? statusLabels[plan?.status || ''] || 'Noch nicht als gekocht erfasst' : 'Noch nicht als gekocht erfasst'}
          </span>
          {event && proposed && proposed.id !== event.dish_id && <span className="history-planned">Geplant: {proposed.name}</span>}</div>
        </div>
        <div className="history-actions">
          {event ? <>
            <button disabled={busy} aria-label={`Kochereignis vom ${date} bearbeiten`} onClick={() => onChoose(day, event)}>Ändern</button>
            <button className="day-symbol" title="Kochereignis löschen" disabled={busy} aria-label={`Kochereignis vom ${date} löschen`} onClick={() => onDelete(event)}><svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/></svg></button>
          </> : <>
            {proposed && <button className="day-symbol" title="Als gekocht speichern" aria-label={`${date}: Als gekocht speichern`} disabled={busy} onClick={() => onCook(day, proposed.id)}><span aria-hidden="true">✓</span></button>}
            <button disabled={busy} onClick={() => onChoose(day)}>{proposed ? 'Etwas anderes gekocht' : 'Gericht nachtragen'}</button>
          </>}
        </div>
      </div>;
    });

  return <section className="card cooking-history">
    <div className="section-title"><h3>Eure vergangenen Tage</h3><button disabled={busy} onClick={onAdd}>＋ Nachtragen</button></div>
    <p>Vorschläge und tatsächlich gekochte Gerichte Tag für Tag. Mit „Gekocht“ bestätigt ihr direkt, was auf dem Tisch stand. Nur erfasste Kochereignisse zählen für die Statistik.</p>
    <PlanLegend includePast/>
    {renderedDays.slice(0, 7)}
    <details className="history-older" onToggle={event => {const open = event.currentTarget.open; setVisibleDays(count => open ? Math.max(count, 37) : 7);}}>
      <summary>Ältere Tage anzeigen</summary>
      {renderedDays.slice(7)}
      <button className="history-more" onClick={() => setVisibleDays(count => count + 30)}>30 weitere Tage anzeigen</button>
    </details>
  </section>;
}
