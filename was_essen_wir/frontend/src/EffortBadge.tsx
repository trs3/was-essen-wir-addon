export function EffortBadge({effort, label}: {effort: 'quick'|'normal'|'elaborate'; label: string}) {
  const paths = {
    quick: 'M13 2 4 14h7l-1 8 10-13h-7l1-7Z',
    normal: 'M12 8v4l3 2 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
    elaborate: 'M5 11h14v7a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3v-7ZM2 13h3m14 0h3M8 7V4m4 3V2m4 5V4',
  };
  return <span className="effort-badge" data-effort={effort}>
    <svg aria-hidden="true" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={paths[effort]}/></svg>
    {label}
  </span>;
}
