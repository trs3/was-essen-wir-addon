import {useId, useState} from 'react';

export function FieldHelp({label, children}: {label: string; children: string}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  return <span className="field-help" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
    <button type="button" className="help-button" aria-label={`Hilfe: ${label}`} aria-describedby={open ? id : undefined}
      onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} onClick={() => setOpen(true)}
      onKeyDown={event => {if (event.key === 'Escape' && open) {event.stopPropagation(); setOpen(false);}}}>?</button>
    {open && <span id={id} role="tooltip" className="field-tooltip">{children}</span>}
  </span>;
}
