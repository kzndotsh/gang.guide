export const DEFAULT_YEAR_MIN = 1930;

/** Omit `year` from the URL when it is just the default visible range. */
export function yearQueryValue(yearMin: number, yearMax: number, domainMax: number): string | null {
  if (yearMin === DEFAULT_YEAR_MIN && yearMax === domainMax) return null;
  return `${yearMin}-${yearMax}`;
}

/**
 * Update the query string without going through SvelteKit's `replaceState`.
 * Kit's helper `$set`s the page store; doing that on first paint of `/` → `/?year=`
 * aborts hydration. Native replaceState with the existing history.state is enough.
 */
export function replaceLocation(next: string): void {
  const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  if (next === current) return;
  history.replaceState(history.state, '', next);
}