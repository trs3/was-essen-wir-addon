import {useEffect, useRef, useState} from 'react';

type CalendarStatus = {enabled: boolean; path: string|null; version: number};
type Props = {
  request: (path: string, method?: string, body?: unknown) => Promise<CalendarStatus>;
  onError: (message: string) => void;
  notify: (message: string) => void;
};

export function CalendarSubscription({request, onError, notify}: Props) {
  const [status, setStatus] = useState<CalendarStatus|null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let mounted = true;
    const refresh = () => request('/calendar').then(value => {
      if (mounted) setStatus(value);
    }).catch(error => { if (mounted) onError(error.message); });
    refresh();
    window.addEventListener('focus', refresh);
    return () => { mounted = false; window.removeEventListener('focus', refresh); };
  }, [request, onError]);

  async function change(action: 'enable'|'rotate'|'disable') {
    if (!status || busy) return;
    if (action === 'rotate' && !confirm('Der bisherige Link wird ungültig. Bestehende Kalender-Abos benötigen danach den neuen Link. Fortfahren?')) return;
    setBusy(true);
    onError('');
    try {
      setStatus(await request('/calendar', 'POST', {action, version: status.version}));
      notify(action === 'disable' ? 'Kalender-Link deaktiviert.' : action === 'rotate' ? 'Neuer Kalender-Link erstellt. Bitte die Abos aktualisieren.' : 'Kalender-Link erstellt.');
    } catch (error) {
      onError((error as Error).message);
      try { setStatus(await request('/calendar')); } catch { /* Keep the visible last state. */ }
    } finally { setBusy(false); }
  }

  const url = status?.path ? new URL(status.path, window.location.origin).href : '';
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);
  async function copy() {
    if (navigator.clipboard) {
      try { await navigator.clipboard.writeText(url); notify('Kalender-Link kopiert.'); return; }
      catch { /* HTTP and denied clipboard access use manual selection. */ }
    }
    input.current?.focus();
    input.current?.select();
    notify('Link markiert. Bitte über das Kopiermenü kopieren.');
  }

  return <section className="card calendar-subscription">
    <h3>Euer Plan im Apple Kalender</h3>
    <p>Abonniert euren Essensplan als eigenen Kalender. Gerichte erscheinen ganztägig; Vorschläge, feste Termine und tatsächlich gekochte Gerichte werden berücksichtigt. Freie Tage bleiben leer.</p>
    {!status ? <p>Kalender-Einstellungen werden geladen …</p> : status.enabled ? <>
      <label>Privater Kalender-Link<input ref={input} type="text" readOnly value={url} autoComplete="off" spellCheck={false} onFocus={event => event.target.select()}/></label>
      <button onClick={copy}>Kalender-Link kopieren</button>
      {local && <p>Für das iPhone öffne die App über die Netzwerkadresse deines Servers und kopiere den Link dort. Ein Link mit localhost funktioniert nur auf diesem Mac.</p>}
      <details><summary>So abonnierst du den Kalender</summary>
        <p><strong>iPhone:</strong> Kalender → Kalender → Kalender hinzufügen → Kalenderabonnement hinzufügen. Den Link einfügen und bestätigen.</p>
        <p><strong>Mac:</strong> Kalender → Ablage → Neues Kalenderabonnement. Den Link einfügen und ein Aktualisierungsintervall wählen.</p>
        <p>Apple Kalender bestimmt, wann Änderungen abgerufen werden. Der Server muss dabei über euer Heimnetz, VPN oder eine erreichbare HTTPS-Adresse verfügbar sein. Änderungen am Essen macht ihr weiterhin hier in der App.</p>
        <a className="calendar-download" href={url} download="was-essen-wir.ics">ICS-Datei einmalig herunterladen</a>
        <p>Ein einmaliger Dateiimport aktualisiert sich nicht automatisch. Dafür den Link abonnieren.</p>
      </details>
      <p className="calendar-privacy">Wer diesen Link kennt, kann euren Kalender lesen. Teilt ihn nur mit Personen, die euren Plan sehen dürfen.</p>
      <div className="calendar-actions"><button disabled={busy} onClick={() => change('rotate')}>Link erneuern</button><button disabled={busy} onClick={() => change('disable')}>Link deaktivieren</button></div>
    </> : <button className="primary" disabled={busy} onClick={() => change('enable')}>Kalender-Link erstellen</button>}
  </section>;
}
