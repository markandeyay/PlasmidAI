"use client";

import { useMemo, useState } from "react";
import { ApiError, createSession, exportDesign, pollJob, submitDesign, submitRefinement } from "@/lib/api";
import { ExportActions } from "@/components/export-actions";
import { PlasmidMapView } from "@/components/plasmid-map-view";
import type { AnnotatedSequence, JobResultPayload } from "@/lib/types";

type UiState = "idle" | "submitting" | "polling" | "ready" | "awaiting_clarification" | "error";

type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  kind: "prompt" | "result" | "clarification" | "error";
  text: string;
  result?: JobResultPayload;
};

const DEFAULT_PROMPT =
  "a bacterial expression vector for E. coli with ampicillin selection and GFP reporter readout";

export default function Page() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      kind: "result",
      text: "Describe the construct you want. I will retrieve a grounding vector, run the design pipeline, and render the annotated plasmid when the job completes."
    }
  ]);
  const [input, setInput] = useState(DEFAULT_PROMPT);
  const [state, setState] = useState<UiState>("idle");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const latestResult = useMemo(
    () => [...messages].reverse().find((message) => message.result?.annotated_sequence)?.result,
    [messages]
  );
  const annotatedSequence = latestResult?.annotated_sequence ?? null;
  const designId = latestResult?.design_id ?? latestResult?.design?.design_id ?? null;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || state === "submitting" || state === "polling") {
      return;
    }

    setInput("");
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", kind: "prompt", text }
    ]);

    try {
      setState("submitting");
      const currentSessionId = sessionId ?? (await createSession()).session_id;
      setSessionId(currentSessionId);
      const response =
        sessionId && state !== "awaiting_clarification"
          ? await submitRefinement(currentSessionId, text)
          : sessionId && state === "awaiting_clarification"
            ? await submitRefinement(currentSessionId, text)
            : await submitDesign(currentSessionId, text);

      setActiveJobId(response.job_id);
      setState("polling");
      const job = await pollJob(response.job_id);
      const result = normalizeJobResult(job.result);
      const clarification = clarificationQuestion(result);
      if (job.error || job.status.toLowerCase() === "failed") {
        throw new ApiError(job.error ?? "Design job failed");
      }
      if (clarification) {
        setMessages((current) => [
          ...current,
          { id: crypto.randomUUID(), role: "assistant", kind: "clarification", text: clarification, result }
        ]);
        setState("awaiting_clarification");
      } else {
        setMessages((current) => [
          ...current,
          { id: crypto.randomUUID(), role: "assistant", kind: "result", text: resultSummary(result), result }
        ]);
        setState("ready");
      }
    } catch (error) {
      const text = error instanceof Error ? error.message : "The design request failed.";
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "system", kind: "error", text }
      ]);
      setState("error");
    } finally {
      setActiveJobId(null);
    }
  }

  async function handleExport(format: "genbank" | "fasta") {
    if (!designId) {
      return;
    }
    const blob = await exportDesign(designId, format);
    const suffix = format === "genbank" ? "gb" : "fasta";
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${designId}.${suffix}`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="min-h-screen bg-panel text-ink">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[minmax(0,1fr)_520px]">
        <section className="flex min-h-screen flex-col border-r border-line bg-white">
          <header className="border-b border-line px-6 py-5">
            <p className="text-sm font-semibold uppercase text-action">PlasmidAI</p>
            <h1 className="mt-1 text-2xl font-semibold">Design workspace</h1>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5" aria-live="polite">
            {messages.map((message) => (
              <article
                key={message.id}
                className={`max-w-3xl border p-4 shadow-subtle ${
                  message.role === "user"
                    ? "ml-auto border-action/30 bg-action/5"
                    : message.kind === "error"
                      ? "border-red-200 bg-red-50"
                      : message.kind === "clarification"
                        ? "border-warning/40 bg-amber-50"
                        : "border-line bg-white"
                }`}
              >
                <div className="mb-2 text-xs font-semibold uppercase text-slate-500">
                  {message.role === "user" ? "Researcher" : message.kind === "clarification" ? "Clarification" : "Design agent"}
                </div>
                <p className="whitespace-pre-wrap text-sm leading-6 text-slate-800">{message.text}</p>
                {message.result?.retrieved_templates?.length ? (
                  <ul className="mt-3 space-y-1 text-xs text-slate-600">
                    {message.result.retrieved_templates.slice(0, 3).map((template, index) => (
                      <li key={`${message.id}-${template.source_id ?? index}`}>
                        Retrieved {index + 1}: {template.name ?? template.source_id ?? "template"}{" "}
                        {typeof template.score === "number" ? `(${template.score.toFixed(3)})` : ""}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </article>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="border-t border-line bg-panel px-6 py-4">
            <label htmlFor="goal" className="sr-only">
              Experimental goal
            </label>
            <div className="flex flex-col gap-3 sm:flex-row">
              <textarea
                id="goal"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                disabled={state === "submitting" || state === "polling"}
                rows={3}
                className="min-h-24 flex-1 resize-none border border-line bg-white px-4 py-3 text-sm shadow-subtle outline-none focus:border-action"
                placeholder={
                  state === "awaiting_clarification"
                    ? "Answer the clarification question..."
                    : "Describe the plasmid you want..."
                }
              />
              <button
                type="submit"
                disabled={!input.trim() || state === "submitting" || state === "polling"}
                className="h-12 border border-action bg-action px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-300"
              >
                {state === "polling" ? "Working" : state === "awaiting_clarification" ? "Answer" : sessionId ? "Refine" : "Design"}
              </button>
            </div>
            {activeJobId ? <p className="mt-2 text-xs text-slate-500">Polling job {activeJobId}</p> : null}
          </form>
        </section>

        <aside className="min-h-screen bg-panel px-5 py-5">
          <div className="sticky top-5 space-y-4">
            <PlasmidMapView annotatedSequence={annotatedSequence as AnnotatedSequence | null} />
            <ExportActions designId={designId} onExport={handleExport} />
          </div>
        </aside>
      </div>
    </main>
  );
}

function normalizeJobResult(result: unknown): JobResultPayload {
  if (!result || typeof result !== "object") {
    return {};
  }
  const record = result as JobResultPayload;
  if (record.design && typeof record.design === "object") {
    const design = record.design as JobResultPayload;
    return { ...design, ...record, design };
  }
  return record;
}

function clarificationQuestion(result: JobResultPayload): string | null {
  return (
    result.clarification_question ??
    (result.design_spec?.clarification_needed ? result.design_spec.clarification_question ?? null : null)
  );
}

function resultSummary(result: JobResultPayload): string {
  const sequence = result.annotated_sequence;
  const recommendation = result.recommendation_text ?? result.design?.recommendation_text;
  if (recommendation) {
    return recommendation;
  }
  if (sequence) {
    return `Generated annotated ${sequence.topology} sequence with ${sequence.sequence.length.toLocaleString()} bp and ${sequence.features.length} labeled features.`;
  }
  return "Design job completed. Review the returned templates and validation details.";
}
