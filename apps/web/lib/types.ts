export type FeatureType = "ORI" | "promoter" | "GOI" | "marker" | "MCS" | "terminator" | "other" | string;

export type AnnotatedFeature = {
  start: number;
  end: number;
  type: FeatureType;
  strand: -1 | 0 | 1;
  name: string;
  confidence: number;
};

export type AnnotatedSequence = {
  sequence: string;
  topology: "circular" | "linear" | string;
  features: AnnotatedFeature[];
  annotation_complete: boolean;
  vector_profile?: string;
};

export type DesignSpec = {
  organism?: string;
  genes?: string[];
  markers?: string[];
  constraints?: string[];
  tags?: string[];
  application?: string | null;
  cell_line?: string | null;
  cloning_method?: string | null;
  inducer?: string | null;
  promoter_type?: string | null;
  publication_doi?: string | null;
  source?: string | null;
  vector_type?: string | null;
  clarification_needed?: boolean;
  clarification_question?: string | null;
};

export type RetrievedTemplate = {
  source_id?: string;
  name?: string;
  score?: number;
  source?: string;
  vector_profile?: string;
};

export type JobResultPayload = {
  design_id?: string;
  action?: string;
  design?: JobResultPayload;
  design_spec?: DesignSpec | null;
  clarification_question?: string | null;
  recommendation_text?: string | null;
  retrieved_templates?: RetrievedTemplate[];
  annotated_sequence?: AnnotatedSequence | null;
  validation_report?: unknown;
};

export type SessionResponse = {
  session_id: string;
};

export type JobAcceptedResponse = {
  job_id: string;
};

export type JobStatusResponse = {
  job_id: string;
  status: string;
  result?: JobResultPayload | Record<string, unknown> | null;
  error?: string | null;
};
