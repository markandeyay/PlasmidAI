import { API_BASE_URL } from "@/lib/config";
import type { ApiErrorEnvelope, ApiFieldError, JobAcceptedResponse, JobStatusResponse, SessionResponse } from "@/lib/types";

export class ApiError extends Error {
  status?: number;
  code?: string;
  retryable: boolean;
  fieldErrors: ApiFieldError[];
  details: Record<string, unknown>;

  constructor(
    message: string,
    options: {
      status?: number;
      code?: string;
      retryable?: boolean;
      fieldErrors?: ApiFieldError[];
      details?: Record<string, unknown>;
    } = {}
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.retryable = options.retryable ?? false;
    this.fieldErrors = options.fieldErrors ?? [];
    this.details = options.details ?? {};
  }
}

export async function createSession(): Promise<SessionResponse> {
  return request<SessionResponse>("/v1/sessions", { method: "POST" });
}

export async function submitDesign(sessionId: string, goal: string): Promise<JobAcceptedResponse> {
  return request<JobAcceptedResponse>(`/v1/sessions/${encodeURIComponent(sessionId)}/design`, {
    method: "POST",
    body: JSON.stringify({ goal })
  });
}

export async function submitRefinement(sessionId: string, instruction: string): Promise<JobAcceptedResponse> {
  return request<JobAcceptedResponse>(`/v1/sessions/${encodeURIComponent(sessionId)}/refine`, {
    method: "POST",
    body: JSON.stringify({ instruction })
  });
}

export async function getJob(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/v1/jobs/${encodeURIComponent(jobId)}`, { method: "GET" });
}

export async function pollJob(
  jobId: string,
  options: { intervalMs?: number; timeoutMs?: number; onUpdate?: (job: JobStatusResponse) => void } = {}
) {
  const intervalMs = options.intervalMs ?? 750;
  const timeoutMs = options.timeoutMs ?? 30000;
  const startedAt = Date.now();

  for (;;) {
    const job = await getJob(jobId);
    options.onUpdate?.(job);
    const status = job.status.toLowerCase();
    if (status === "completed" || status === "succeeded" || status === "failed" || job.error) {
      return job;
    }
    if (Date.now() - startedAt > timeoutMs) {
      throw new ApiError(
        `The job is still running. You can try again in a moment with job ID ${jobId}.`,
        { code: "job_poll_timeout", retryable: true, details: { job_id: jobId } }
      );
    }
    await sleep(job.retry_after_ms ?? intervalMs);
  }
}

export async function exportDesign(designId: string, format: "genbank" | "fasta"): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/v1/designs/${encodeURIComponent(designId)}/export?format=${format}`);
  if (!response.ok) {
    throw await parseApiError(response);
  }
  return response.blob();
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {})
    }
  });
  if (!response.ok) {
    throw await parseApiError(response);
  }
  return response.json() as Promise<T>;
}

async function parseApiError(response: Response): Promise<ApiError> {
  const text = await response.text();
  if (text) {
    try {
      const body = JSON.parse(text) as Partial<ApiErrorEnvelope>;
      if (body.error?.message) {
        return new ApiError(body.error.message, {
          status: response.status,
          code: body.error.code,
          retryable: body.error.retryable,
          fieldErrors: body.error.field_errors,
          details: body.error.details
        });
      }
    } catch {
      return new ApiError(text, { status: response.status });
    }
  }
  return new ApiError(`API request failed with ${response.status}`, { status: response.status });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
