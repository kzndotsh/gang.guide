import { orgDisplayTitle } from '$lib/inspector/inspectorDisplay';
import type { GraphNode } from './types';

export type SearchResult = {
  node: GraphNode;
  score: number;
  matchField: string;
};

function normalize(value: string): string {
  return value.toLowerCase().replace(/\s+/g, ' ').trim();
}

function collectTerms(node: GraphNode): { text: string; field: string }[] {
  const terms: { text: string; field: string }[] = [];
  const title = orgDisplayTitle(node);
  if (title) terms.push({ text: title, field: 'name' });
  if (node.label && node.label !== title) {
    terms.push({ text: node.label, field: 'label' });
  }
  for (const alias of node.data?.aliases ?? []) {
    const trimmed = alias?.trim();
    if (trimmed) terms.push({ text: trimmed, field: 'alias' });
  }
  for (const name of node.data?.original_text_names ?? []) {
    const trimmed = name?.trim();
    if (trimmed) terms.push({ text: trimmed, field: 'alias' });
  }
  if (node.data?.metro) terms.push({ text: node.data.metro, field: 'metro' });
  const slug = node.id.replace(/^org:/, '').replace(/-/g, ' ');
  terms.push({ text: slug, field: 'id' });
  return terms;
}

function scoreTerm(query: string, text: string): number {
  const q = normalize(query);
  const t = normalize(text);
  if (!q || !t) return 0;
  if (t === q) return 100;
  if (t.startsWith(q)) return 80;
  if (t.split(/\s+/).some((word) => word.startsWith(q))) return 65;
  if (t.includes(q)) return 50;
  return 0;
}

/** Rank org nodes by query against name, aliases, metro, and slug id. */
export function searchOrgNodes(
  nodes: GraphNode[],
  query: string,
  limit = 12,
): SearchResult[] {
  const q = normalize(query);
  if (q.length < 2) return [];

  const scored: SearchResult[] = [];
  for (const node of nodes) {
    let best = 0;
    let matchField = '';
    for (const { text, field } of collectTerms(node)) {
      const score = scoreTerm(q, text);
      if (score > best) {
        best = score;
        matchField = field;
      }
    }
    if (best > 0) scored.push({ node, score: best, matchField });
  }

  return scored
    .sort(
      (a, b) =>
        b.score - a.score ||
        orgDisplayTitle(a.node).localeCompare(orgDisplayTitle(b.node)),
    )
    .slice(0, limit);
}
