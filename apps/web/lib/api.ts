import { API_BASE_URL } from "@/lib/config";
import type { JobAcceptedResponse, JobStatusResponse, SessionResponse } from "@/lib/types";

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
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

export async function pollJob(jobId: string, options: { intervalMs?: number; timeoutMs?: number } = {}) {
  const intervalMs = options.intervalMs ?? 750;
  const timeoutMs = options.timeoutMs ?? 30000;
  const startedAt = Date.now();

  for (;;) {
    const job = await getJob(jobId);
    const status = job.status.toLowerCase();
    if (status === "completed" || status === "succeeded" || status === "failed" || job.error) {
      return job;
    }
    if (Date.now() - startedAt > timeoutMs) {
      throw new ApiError(`Timed out waiting for job ${jobId}`);
    }
    await sleep(intervalMs);
  }
}

export async function exportDesign(designId: string, format: "genbank" | "fasta"): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/v1/designs/${encodeURIComponent(designId)}/export?format=${format}`);
  if (!response.ok) {
    throw new ApiError(`Export failed with ${response.status}`);
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
    const body = await response.text();
    throw new ApiError(body || `API request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
