export type YearPrecision = 'exact' | 'circa' | 'decade' | 'range';

export type OrganizationStatus = 'active' | 'inactive' | 'defunct' | 'unknown';

export type YearSpanFields = {
  founded_year?: number;
  founded_year_latest?: number;
  founded_year_precision?: YearPrecision;
  dissolved_year?: number;
  dissolved_year_latest?: number;
  dissolved_year_precision?: YearPrecision;
};

export type FieldSourceCitation = {
  claim_id?: string;
  predicate: string;
  source_id?: string;
  source_type?: string;
  source_url?: string | null;
  source_label?: string;
  evidence_quote?: string | null;
  review_status?: string;
  primary?: boolean;
  value_preview?: string | null;
};

export type GraphNode = {
  id: string;
  type: string;
  label: string;
  detail_level: string;
  review_status: string;
  data: YearSpanFields & {
    id?: string;
    seed_key?: string;
    standard_name?: string;
    map_hint?: { lane?: string; x_year?: number };
    layout?: {
      lane: string;
      lane_label?: string;
      lane_index: number;
      lane_reason?: string;
      display_year: number;
      slot: number;
      overview: boolean;
      year_span?: {
        earliest: number;
        latest: number;
        precision: string;
        midpoint: number;
      } | null;
    };
    aliases?: string[];
    original_text_names?: string[];
    type?: string;
    ethnicity?: string;
    colors?: string[];
    symbols?: string[];
    status?: OrganizationStatus;
    description?: string;
    metro?: string;
    nation_affiliation?: string;
    era?: string;
    bootstrap?: boolean;
    detail_level?: string;
    field_sources?: Record<string, FieldSourceCitation[]>;
    sources?: Array<{ url?: string; title?: string } | string>;
  };
};

export type GraphEdge = {
  source: string;
  target: string;
  type: string;
  claim_id?: string;
  confidence_score?: number;
  review_status?: string;
};

export type GraphEvent = {
  id: string;
  title: string;
  year: number | null;
  year_earliest?: number | null;
  year_latest?: number | null;
  year_precision?: YearPrecision | null;
  data?: {
    description?: string;
    org_ids?: string[];
    org_id_refs?: string[];
    person_ids?: string[];
    evidence?: Array<{
      quote?: string;
      source_url?: string;
      source_title?: string | null;
      accessed_at?: string | null;
      validation_status?: string | null;
    }>;
  };
};

export type GraphVisibilityMeta = {
  registry: { claims: number };
  exported: {
    nodes: number;
    edges: number;
    nodes_with_founded_year: number;
    nodes_exact_circa: number;
    nodes_decade_estimated: number;
    nodes_estimate_only: number;
    nodes_with_colors: number;
    nodes_with_description: number;
    nodes_with_aliases: number;
    nodes_with_metro: number;
    nodes_active: number;
    nodes_inactive: number;
    nodes_multi_source: number;
    total_sources: number;
    linked_events: number;
    dated_events: number;
  };
  excluded: {
    mention_only_entities: number;
    relationships_off_graph: number;
    relationships_geo_filtered: number;
    events_unlinked: number;
    events_undated_or_noise: number;
  };
  edge_types?: Record<string, number>;
  top_source_domains?: [string, number][];
  lane_counts?: Record<string, number>;
};

export type Graph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  events?: GraphEvent[];
  provenance?: Record<string, Record<string, string[]>>;
  meta?: {
    node_count?: number;
    edge_count?: number;
    event_count?: number;
    lanes?: Array<{
      id: string;
      label: string;
      sort_order?: number;
      order?: number;
      cluster?: string;
    }>;
    visibility?: GraphVisibilityMeta;
  };
  exported_at?: string;
};
