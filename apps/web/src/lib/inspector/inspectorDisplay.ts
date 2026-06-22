import type { GraphNode } from '$lib/types';

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Strip repeated word-subsequences from garbled StreetGangs titles. */
function stripRepeatedSegment(text: string): string {
  const words = text.split(/\s+/);
  const n = words.length;
  if (n < 6) return text;

  const norm = (w: string) => w.toLowerCase().replace(/,$/, '');

  let bestSize = 0;
  let bestStart = -1;
  for (let size = Math.floor(n / 2); size > 2; size--) {
    let found = false;
    for (let i = 0; i < n - size; i++) {
      const chunk = words.slice(i, i + size).map(norm);
      for (let j = i + size; j <= n - size; j++) {
        const cand = words.slice(j, j + size).map(norm);
        if (chunk.every((w, k) => w === cand[k])) {
          bestSize = size;
          bestStart = i;
          found = true;
          break;
        }
      }
      if (found) break;
    }
    if (found) break;
  }

  if (bestStart >= 0) {
    return words
      .slice(0, bestStart + bestSize)
      .join(' ')
      .replace(/,$/, '')
      .replace(/\s*\([^)]+\)\s*$/, '')
      .trim();
  }
  return text;
}

/** Prefer registry standard_name over export label (may carry StreetGangs breadcrumb noise). */
export function orgDisplayTitle(node: GraphNode | null): string {
  if (!node) return '';
  const raw = node.data?.standard_name?.trim() || node.label;
  return stripRepeatedSegment(raw);
}

/** Strip StreetGangs title lead-in duplication from exported descriptions. */
export function orgDisplayDescription(node: GraphNode | null): string | undefined {
  const raw = node?.data?.description?.trim();
  if (!raw) return undefined;

  const title = orgDisplayTitle(node);
  if (!title) return raw;

  // "Name (geo note) Name are..." → "Name are..."
  const geoDup = new RegExp(
    `^${escapeRegex(title)}\\s*\\([^)]+\\)\\s*${escapeRegex(title)}\\s*`,
    'i',
  );
  if (geoDup.test(raw)) {
    return raw.replace(geoDup, `${title} `);
  }

  // "Name in Location Name are..." → "Name are..."
  const geoInDup = new RegExp(
    `^${escapeRegex(title)}\\s+in\\s+[^.!?]+?\\s+${escapeRegex(title)}\\s+`,
    'i',
  );
  if (geoInDup.test(raw)) {
    return raw.replace(geoInDup, `${title} `);
  }

  const label = node!.label?.trim();
  if (label && label !== title && raw.toLowerCase().startsWith(label.toLowerCase())) {
    const rest = raw.slice(label.length).trimStart();
    if (/^(are|is|were|was)\b/i.test(rest)) {
      return `${title} ${rest}`;
    }
    return rest || raw;
  }

  return raw;
}
