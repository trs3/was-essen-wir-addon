import {useState} from 'react';

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
  confirmed: 'Bestätigt · noch nicht als gekocht erfasst',
  fixed: 'Fest eingeplant · noch nicht als gekocht erfasst',
};

export function CookingHistory({today, plans, history, dishes, busy, onCook, onChoose, onDelete, onAdd}: Props) {
  const [visibleDays, setVisibleDays] = useState(30);
  const plansByDay = new Map(plans.map(plan => [plan.day, plan]));
  const historyByDay = new Map(history.map(event => [event.day, event]));
  const dishesById = new Map(dishes.map(dish => [dish.id, dish]));

  return <section className="card cooking-history">
    <div className="section-title"><h3>Eure vergangenen Tage</h3><button disabled={busy} onClick={onAdd}>＋ Nachtragen</button></div>
    <p>Vorschläge und tatsächlich gekochte Gerichte Tag für Tag. Mit „Gekocht“ bestätigt ihr direkt, was auf dem Tisch stand. Nur erfasste Kochereignisse zählen für die Statistik.</p>
    {Array.from({length: visibleDays}, (_, index) => previousDay(today, index)).map(day => {
      const plan = plansByDay.get(day), event = historyByDay.get(day);
      const proposed = plan?.dish_id ? dishesById.get(plan.dish_id) : undefined;
      const actual = event ? dishesById.get(event.dish_id) : undefined;
      const date = new Date(day + 'T12:00:00').toLocaleDateString('de-DE', {weekday: 'short', day: 'numeric', month: 'short', year: 'numeric'});
      return <div className="history-row" key={day}>
        <div className="history-day">
          <time dateTime={day}>{date}</time>
          <strong>{event ? actual?.name || 'Unbekanntes Gericht' : proposed?.name || (plan?.status === 'empty' ? 'Bewusst frei' : 'Kein Vorschlag gespeichert')}</strong>
          <span className={'history-status status ' + (event ? 'cooked' : plan?.status || '')}>
            {event ? '✓ Gekocht' : proposed ? statusLabels[plan?.status || ''] || 'Noch nicht als gekocht erfasst' : 'Noch nicht als gekocht erfasst'}
          </span>
          {event && proposed && proposed.id !== event.dish_id && <small>Geplant: {proposed.name}</small>}
        </div>
        <div className="history-actions">
          {event ? <>
            <button disabled={busy} aria-label={`Kochereignis vom ${date} bearbeiten`} onClick={() => onChoose(day, event)}>Ändern</button>
            <button disabled={busy} aria-label={`Kochereignis vom ${date} löschen`} onClick={() => onDelete(event)}>×</button>
          </> : <>
            {proposed && <button className="primary" disabled={busy} onClick={() => onCook(day, proposed.id)}>Gekocht</button>}
            <button disabled={busy} onClick={() => onChoose(day)}>{proposed ? 'Etwas anderes gekocht' : 'Gericht nachtragen'}</button>
          </>}
        </div>
      </div>;
    })}
    <button className="history-more" onClick={() => setVisibleDays(count => count + 30)}>30 ältere Tage anzeigen</button>
  </section>;
}
