import type { FieldSourceCitation, Graph, GraphEvent, GraphNode } from './types';
import { truncate } from '$lib/inspector/inspectorFormat';

export type SourceSnippet = {
  eventId?: string;
  eventTitle?: string;
  quote?: string;
};

export type OrgSourceLink = {
  url?: string;
  label: string;
  eventIds: string[];
  kind: 'news' | 'reference' | 'profile' | 'claim';
  predicate?: string;
  primary?: boolean;
  reviewStatus?: string;
  snippets: SourceSnippet[];
};

const PREDICATE_LABELS: Record<string, string> = {
  description: 'Description',
  nation_affiliation: 'Nation affiliation',
  type: 'Organization type',
  status: 'Status',
  ethnicity: 'Ethnicity',
  founded_year: 'Founded year',
  dissolved_year: 'Dissolved year',
  aliases: 'Aliases',
  colors: 'Colors',
  symbols: 'Symbols',
  original_text_names: 'Source names',
};

export function predicateLabel(predicate: string): string {
  return PREDICATE_LABELS[predicate] ?? predicate.replace(/_/g, ' ');
}

export function orgEvents(graph: Graph, orgId: string | null): GraphEvent[] {
  return [];
}

function sourceLabel(url: string, fallback?: string | null): string {
  if (fallback?.trim()) return fallback.trim();
  try {
    const host = new URL(url).hostname.replace(/^www\./, '');
    return host;
  } catch {
    return url;
  }
}

function isNewsUrl(url: string): boolean {
  return /streetgangs|news|blog|article/i.test(url);
}

function profileSourceUrl(node: GraphNode): string | null {
  const seedKey = node.data?.seed_key?.trim();
  if (!seedKey || seedKey.includes(' ')) return null;
  return `https://www.streetgangs.com/${seedKey.replace(/^\/+/, '')}`;
}

function bestQuote(...candidates: (string | undefined | null)[]): string | undefined {
  for (const text of candidates) {
    const trimmed = text?.trim();
    if (trimmed && trimmed.length > 24) return trimmed;
  }
  for (const text of candidates) {
    const trimmed = text?.trim();
    if (trimmed) return trimmed;
  }
  return undefined;
}

function addClaimLink(
  links: OrgSourceLink[],
  cite: FieldSourceCitation,
): OrgSourceLink {
  const url = cite.source_url ?? undefined;
  const existing = links.find(
    (item) =>
      item.kind === 'claim' &&
      item.predicate === cite.predicate &&
      item.url === url &&
      item.label === (cite.source_label ?? 'Source'),
  );
  const quote = bestQuote(cite.evidence_quote, cite.value_preview);
  const snippet: SourceSnippet = {
    eventTitle: predicateLabel(cite.predicate),
    quote,
  };
  if (existing) {
    if (quote && !existing.snippets.some((s) => s.quote === quote)) {
      existing.snippets.push(snippet);
    }
    existing.primary = existing.primary || Boolean(cite.primary);
    return existing;
  }
  const link: OrgSourceLink = {
    url,
    label: cite.source_label ?? sourceLabel(url ?? '', cite.source_id),
    eventIds: [],
    kind: 'claim',
    predicate: cite.predicate,
    primary: Boolean(cite.primary),
    reviewStatus: cite.review_status,
    snippets: quote || cite.predicate ? [snippet] : [],
  };
  links.push(link);
  return link;
}

export function orgSourceLinks(
  graph: Graph,
  node: GraphNode | null,
  events: GraphEvent[],
): OrgSourceLink[] {
  const links: OrgSourceLink[] = [];
  const fieldSourceUrls = new Set<string>();

  if (node?.data?.field_sources) {
    for (const cites of Object.values(node.data.field_sources)) {
      for (const cite of cites) {
        addClaimLink(links, cite);
        if (cite.source_url) fieldSourceUrls.add(cite.source_url);
      }
    }
  }

  function findLink(url?: string, label?: string): OrgSourceLink | undefined {
    if (url?.trim()) return links.find((item) => item.url === url.trim());
    if (label?.trim()) {
      return links.find((item) => !item.url && item.label === label.trim());
    }
    return undefined;
  }

  function addSnippet(link: OrgSourceLink, snippet: SourceSnippet, eventId?: string) {
    if (eventId && !link.eventIds.includes(eventId)) link.eventIds.push(eventId);
    const duplicate = link.snippets.some(
      (s) =>
        s.eventId === snippet.eventId &&
        s.quote === snippet.quote &&
        s.eventTitle === snippet.eventTitle,
    );
    if (!duplicate) link.snippets.push(snippet);
  }

  function add(
    url: string | undefined,
    label: string | undefined,
    snippet: SourceSnippet = {},
    kind: OrgSourceLink['kind'] = 'reference',
    eventId?: string,
  ) {
    const key = url?.trim();
    if (key && fieldSourceUrls.has(key) && kind !== 'news') return findLink(key, label);
    const existing = findLink(key, label);
    if (existing) {
      addSnippet(existing, snippet, eventId);
      return existing;
    }
    const link: OrgSourceLink = {
      url: key,
      label: key ? sourceLabel(key, label) : (label?.trim() ?? 'Source'),
      eventIds: eventId ? [eventId] : [],
      kind: kind === 'reference' ? 'reference' : (key && isNewsUrl(key) ? 'news' : kind),
      snippets: snippet.quote || snippet.eventTitle ? [snippet] : [],
    };
    links.push(link);
    return link;
  }

  if (node?.data?.description && !fieldSourceUrls.size) {
    const profileUrl = profileSourceUrl(node);
    if (profileUrl && !fieldSourceUrls.has(profileUrl)) {
      add(
        profileUrl,
        `${node.label} profile`,
        { quote: truncate(node.data.description, 280) },
        'profile',
      );
    }
  }

  for (const ev of events) {
    const eventTitle = ev.title;
    for (const item of ev.data?.evidence ?? []) {
      const quote = bestQuote(item.quote, ev.data?.description);
      add(
        item.source_url,
        item.source_title ?? undefined,
        { eventId: ev.id, eventTitle, quote },
        'news',
        ev.id,
      );
    }
  }

  // Add org-level reference sources (from the sources field)
  if (node?.data?.sources) {
    for (const src of node.data.sources as Array<{ url?: string; title?: string } | string>) {
      const url = typeof src === 'string' ? src : src.url;
      const label = typeof src === 'string' ? undefined : src.title;
      if (url && !links.some((l) => l.url === url)) {
        add(url, label, {}, 'reference');
      }
    }
  }

  if (node?.data?.original_text_names?.length) {
    for (const name of node.data.original_text_names) {
      add(undefined, name, { quote: `Recorded as “${name}” in ingested sources.` }, 'reference');
    }
  }

  return links.sort((a, b) => {
    const rank = (k: OrgSourceLink['kind']) =>
      k === 'claim' ? 0 : k === 'profile' ? 1 : k === 'news' ? 2 : 3;
    const diff = rank(a.kind) - rank(b.kind);
    if (diff !== 0) return diff;
    if (a.primary !== b.primary) return a.primary ? -1 : 1;
    const pred = (a.predicate ?? '').localeCompare(b.predicate ?? '');
    if (pred !== 0) return pred;
    return b.eventIds.length - a.eventIds.length || a.label.localeCompare(b.label);
  });
}

export function groupedClaimSources(links: OrgSourceLink[]): Array<{ predicate: string; items: OrgSourceLink[] }> {
  const groups = new Map<string, OrgSourceLink[]>();
  for (const link of links) {
    if (link.kind !== 'claim' || !link.predicate) continue;
    const bucket = groups.get(link.predicate) ?? [];
    bucket.push(link);
    groups.set(link.predicate, bucket);
  }
  return [...groups.entries()]
    .map(([predicate, items]) => ({ predicate, items }))
    .sort((a, b) => a.predicate.localeCompare(b.predicate));
}

export function nonClaimSources(links: OrgSourceLink[]): OrgSourceLink[] {
  return links.filter((link) => link.kind !== 'claim' && link.kind !== 'news');
}

export function eventArticleSources(
  eventId: string,
  links: OrgSourceLink[],
): Array<OrgSourceLink & { eventSnippets: SourceSnippet[] }> {
  return links
    .filter(
      (link) =>
        (link.kind === 'news' || link.kind === 'reference') && link.eventIds.includes(eventId),
    )
    .map((link) => ({
      ...link,
      eventSnippets: link.snippets.filter(
        (snippet) => snippet.eventId === eventId || (!snippet.eventId && link.eventIds.length === 1),
      ),
    }));
}
