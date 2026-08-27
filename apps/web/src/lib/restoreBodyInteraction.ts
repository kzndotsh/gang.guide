import { browser } from '$app/environment';

/** Undo modal/drawer scroll-lock side effects so the map stays tappable. */
export function restoreBodyInteraction() {
  if (!browser) return;
  document.body.style.pointerEvents = '';
  document.body.style.overflow = '';
}
