/** Cooking takes precedence; past firm plans need a cooking confirmation. */
export function planState(day: string, today: string, status: string|undefined, cooked: boolean): string {
  if (cooked) return 'cooked';
  if (day < today && (status === 'confirmed' || status === 'fixed')) return 'overdue';
  return status || 'open';
}
