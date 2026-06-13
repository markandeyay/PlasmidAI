"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiError, createSession, exportDesign, getOutcome, getPendingOutcomePrompts, pollJob, submitDesign, submitRefinement } from "@/lib/api";
import { ExportActions, type ExportFormat, type ExportStatus } from "@/components/export-actions";
import { OutcomeReportModal } from "@/components/outcome-report-modal";
import { PlasmidMapView } from "@/components/plasmid-map-view";
import type { AnnotatedSequence, JobResultPayload, JobStatusResponse, OutcomeReport, PendingOutcomePrompt, ValidationCheck, ValidationReport } from "@/lib/types";

type UiState = "idle" | "submitting" | "polling" | "ready" | "awaiting_clarification" | "error";

type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  kind: "prompt" | "result" | "clarification" | "error";
  text: string;
  result?: JobResultPayload;
};

type OutcomeModalTarget = {
  designId: string;
  modelVersion: string;
  initialReport?: OutcomeReport;
  promptKey?: string;
  provenanceContext?: Record<string, unknown>;
};

const DEFAULT_PROMPT =
  "a bacterial expression vector for E. coli with ampicillin selection and GFP reporter readout";

const EXAMPLE_PROMPTS = [
  DEFAULT_PROMPT,
  "a mammalian GFP reporter plasmid for expression analysis in cultured cells",
  "a yeast shuttle vector with URA3 selection and centromere maintenance"
];

const DISMISSED_OUTCOME_PROMPTS_KEY = "plasmidai:dismissed-outcome-prompts";
const REPORTED_OUTCOMES_KEY = "plasmidai:reported-outcomes";

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
  const [input, setInput] = useState("");
  const [state, setState] = useState<UiState>("idle");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStartedAt, setJobStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const [exportStatus, setExportStatus] = useState<Record<ExportFormat, ExportStatus>>({ genbank: "idle", fasta: "idle" });
  const [exportError, setExportError] = useState<string | null>(null);
  const [outcomeModalOpen, setOutcomeModalOpen] = useState(false);
  const [outcomeModalTarget, setOutcomeModalTarget] = useState<OutcomeModalTarget | null>(null);
  const [latestOutcome, setLatestOutcome] = useState<OutcomeReport | null>(null);
  const [reportedOutcomes, setReportedOutcomes] = useState<OutcomeReport[]>([]);
  const [pendingOutcomePrompts, setPendingOutcomePrompts] = useState<PendingOutcomePrompt[]>([]);
  const [dismissedPromptKeys, setDismissedPromptKeys] = useState<string[]>([]);

  const latestResult = useMemo(
    () => [...messages].reverse().find((message) => message.result?.annotated_sequence)?.result,
    [messages]
  );
  const annotatedSequence = latestResult?.annotated_sequence ?? null;
  const designId = latestResult?.design_id ?? latestResult?.design?.design_id ?? null;
  const modelVersion = latestResult?.validation_report?.generated_by_model_version ?? latestResult?.design?.validation_report?.generated_by_model_version ?? null;
  const isBusy = state === "submitting" || state === "polling";
  const activeClarification = useMemo(
    () => [...messages].reverse().find((message) => message.kind === "clarification")?.text ?? null,
    [messages]
  );

  useEffect(() => {
    if (!isBusy || jobStartedAt === null) {
      return;
    }
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, [isBusy, jobStartedAt]);

  useEffect(() => {
    let cancelled = false;
    setDismissedPromptKeys(readDismissedPromptKeys());
    setReportedOutcomes(readReportedOutcomes());
    getPendingOutcomePrompts()
      .then((prompts) => {
        if (!cancelled) {
          setPendingOutcomePrompts(prompts);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPendingOutcomePrompts([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!designId) {
      setLatestOutcome(null);
      return;
    }
    setLatestOutcome(reportedOutcomes.find((outcome) => outcome.design_id === designId) ?? null);
  }, [designId, reportedOutcomes]);

  useEffect(() => {
    if (!designId) {
      return;
    }
    let cancelled = false;
    getOutcome(designId)
      .then((outcome) => {
        if (!cancelled) {
          setReportedOutcomes((current) => persistReportedOutcomes(upsertReportedOutcome(current, outcome)));
        }
      })
      .catch(() => {
        // A missing outcome is expected for designs that have not been reported yet.
      });
    return () => {
      cancelled = true;
    };
  }, [designId]);

  useEffect(() => {
    let cancelled = false;
    const designIds = reportedOutcomes.map((outcome) => outcome.design_id);
    if (!designIds.length) {
      return;
    }
    Promise.all(
      designIds.map((knownDesignId) =>
        getOutcome(knownDesignId)
          .then((outcome) => outcome)
          .catch(() => null)
      )
    ).then((refreshed) => {
      if (cancelled) {
        return;
      }
      const outcomes = refreshed.filter((outcome): outcome is OutcomeReport => Boolean(outcome));
      if (outcomes.length) {
        setReportedOutcomes((current) => persistReportedOutcomes(mergeReportedOutcomes(current, outcomes)));
      }
    });
    return () => {
      cancelled = true;
    };
  }, [reportedOutcomes.length]);

  const visiblePendingPrompt = pendingOutcomePrompts.find((prompt) => !dismissedPromptKeys.includes(promptKey(prompt))) ?? null;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || isBusy) {
      return;
    }

    setInput("");
    setExportError(null);
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", kind: "prompt", text }
    ]);

    try {
      setState("submitting");
      setJobStartedAt(Date.now());
      const currentSessionId = sessionId ?? (await createSession()).session_id;
      const hasExistingSession = Boolean(sessionId);
      setSessionId(currentSessionId);
      const response = hasExistingSession
        ? await submitRefinement(currentSessionId, text)
        : await submitDesign(currentSessionId, text);

      setActiveJobId(response.job_id);
      setState("polling");
      const job = await pollJob(response.job_id, { onUpdate: () => setNow(Date.now()) });
      const result = normalizeJobResult(job.result);
      const clarification = clarificationQuestion(result);
      if (job.error || job.status.toLowerCase() === "failed") {
        throw jobError(job);
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
      const text = friendlyErrorMessage(error);
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "system", kind: "error", text }
      ]);
      setState("error");
    } finally {
      setActiveJobId(null);
      setJobStartedAt(null);
    }
  }

  async function handleExport(format: ExportFormat) {
    if (!designId) {
      return;
    }
    setExportError(null);
    setExportStatus((current) => ({ ...current, [format]: "loading" }));
    try {
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
      setExportStatus((current) => ({ ...current, [format]: "success" }));
    } catch (error) {
      setExportStatus((current) => ({ ...current, [format]: "error" }));
      setExportError(friendlyErrorMessage(error));
    }
  }

  function openCurrentOutcomeModal() {
    if (!designId) {
      return;
    }
    setOutcomeModalTarget({ designId, modelVersion: modelVersion ?? latestOutcome?.model_version ?? "unknown-model", initialReport: latestOutcome ?? undefined });
    setOutcomeModalOpen(true);
  }

  function openPromptOutcomeModal(prompt: PendingOutcomePrompt) {
    setOutcomeModalTarget({
      designId: prompt.design_id,
      modelVersion: "unknown-model",
      promptKey: promptKey(prompt),
      provenanceContext: {
        reported_via: "web_pending_outcome_prompt",
        prompt_session_id: prompt.session_id,
        prompt_created_at: prompt.created_at,
        prompt_days_since_created: prompt.days_since_created,
        model_version_fallback: "unknown-model"
      }
    });
    setOutcomeModalOpen(true);
  }

  function openReportedOutcomeModal(outcome: OutcomeReport) {
    setOutcomeModalTarget({
      designId: outcome.design_id,
      modelVersion: outcome.model_version,
      initialReport: outcome,
      provenanceContext: { reported_via: "web_my_outcomes_panel" }
    });
    setOutcomeModalOpen(true);
  }

  function dismissPrompt(prompt: PendingOutcomePrompt) {
    const key = promptKey(prompt);
    setDismissedPromptKeys((current) => persistDismissedPromptKey(current, key));
  }

  function handleOutcomeSubmitted(report: OutcomeReport) {
    setReportedOutcomes((current) => persistReportedOutcomes(upsertReportedOutcome(current, report)));
    if (report.design_id === designId) {
      setLatestOutcome(report);
    }
    const submittedPromptKey = outcomeModalTarget?.promptKey;
    if (submittedPromptKey) {
      setDismissedPromptKeys((current) => persistDismissedPromptKey(current, submittedPromptKey));
      setPendingOutcomePrompts((current) => current.filter((prompt) => promptKey(prompt) !== submittedPromptKey));
    }
  }

  return (
    <main className="min-h-screen bg-panel text-ink">
      {visiblePendingPrompt ? (
        <PendingOutcomeToast prompt={visiblePendingPrompt} onOpen={openPromptOutcomeModal} onDismiss={dismissPrompt} />
      ) : null}
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[minmax(0,1fr)_520px]">
        <section className="flex min-h-[70vh] flex-col border-r border-line bg-white lg:min-h-screen">
          <header className="border-b border-line px-4 py-5 sm:px-6">
            <p className="text-sm font-semibold uppercase text-action">PlasmidAI</p>
            <h1 className="mt-1 text-2xl font-semibold">Design workspace</h1>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-6" aria-live="polite">
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
                {message.result?.validation_report ? (
                  <ValidationReportPanel report={message.result.validation_report} />
                ) : null}
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
                {message.result?.annotated_sequence ? (
                  <a href="#plasmid-map" className="mt-3 inline-flex text-xs font-semibold text-action">
                    View plasmid map
                  </a>
                ) : null}
              </article>
            ))}
            {isBusy ? (
              <JobProgressCard jobId={activeJobId} state={state} elapsedMs={jobStartedAt ? now - jobStartedAt : 0} />
            ) : null}
          </div>

          <form onSubmit={handleSubmit} className="border-t border-line bg-panel px-4 py-4 sm:px-6">
            {state === "awaiting_clarification" && activeClarification ? (
              <div className="mb-3 border border-warning/40 bg-amber-50 p-3 text-sm text-slate-800">
                <span className="font-semibold text-warning">Clarification needed: </span>
                {activeClarification}
              </div>
            ) : null}
            {!sessionId && state === "idle" ? (
              <div className="mb-3 flex flex-wrap gap-2">
                {EXAMPLE_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => setInput(prompt)}
                    className="border border-line bg-white px-3 py-2 text-left text-xs text-slate-700 hover:border-action hover:text-action"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            ) : null}
            <label htmlFor="goal" className="sr-only">
              Experimental goal
            </label>
            <div className="flex flex-col gap-3 sm:flex-row">
              <textarea
                id="goal"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                disabled={isBusy}
                rows={3}
                className="min-h-24 flex-1 resize-none border border-line bg-white px-4 py-3 text-sm shadow-subtle outline-none focus:border-action"
                placeholder={
                  state === "awaiting_clarification"
                    ? "Answer the clarification question..."
                    : "Describe the host, marker, payload, promoter, and any constraints..."
                }
              />
              <button
                type="submit"
                disabled={!input.trim() || isBusy}
                className="h-12 border border-action bg-action px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-300"
              >
                {state === "submitting" ? "Starting" : state === "polling" ? "Designing" : state === "awaiting_clarification" ? "Answer" : sessionId ? "Refine" : "Design"}
              </button>
            </div>
            {activeJobId ? (
              <p className="mt-2 text-xs text-slate-500">Job {activeJobId} is running. You can keep this page open while results are prepared.</p>
            ) : null}
          </form>
        </section>

        <aside className="min-h-0 bg-panel px-4 py-4 sm:px-5 sm:py-5 lg:min-h-screen">
          <div className="space-y-4 lg:sticky lg:top-5">
            <PlasmidMapView annotatedSequence={annotatedSequence as AnnotatedSequence | null} />
            <ExportActions designId={designId} status={exportStatus} error={exportError} onExport={handleExport} />
            <OutcomePanel designId={designId} latestOutcome={latestOutcome} onOpen={openCurrentOutcomeModal} />
            <MyOutcomesPanel outcomes={reportedOutcomes} onOpen={openReportedOutcomeModal} />
          </div>
        </aside>
      </div>
      <OutcomeReportModal
        open={outcomeModalOpen}
        designId={outcomeModalTarget?.designId ?? null}
        modelVersion={outcomeModalTarget?.modelVersion ?? null}
        onClose={() => setOutcomeModalOpen(false)}
        onSubmitted={handleOutcomeSubmitted}
        initialReport={outcomeModalTarget?.initialReport}
        provenanceContext={outcomeModalTarget?.provenanceContext}
      />
    </main>
  );
}

function MyOutcomesPanel({ outcomes, onOpen }: { outcomes: OutcomeReport[]; onOpen: (outcome: OutcomeReport) => void }) {
  const sortedOutcomes = [...outcomes].sort((a, b) => new Date(b.reported_at).getTime() - new Date(a.reported_at).getTime());
  return (
    <section className="border border-line bg-white p-4 shadow-subtle" aria-label="My reported outcomes">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">My outcomes</h2>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Shows outcomes reported from this browser until a backend list endpoint is available. Known designs are refreshed individually when possible.
          </p>
        </div>
        <span className="border border-line bg-panel px-2 py-1 text-xs font-semibold text-slate-600">{outcomes.length}</span>
      </div>
      {sortedOutcomes.length ? (
        <div className="mt-3 space-y-2">
          {sortedOutcomes.map((outcome) => (
            <article key={outcome.design_id} className="border border-line bg-panel p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="break-all text-sm font-semibold text-slate-800">{outcome.design_id}</p>
                  <p className="mt-1 text-xs text-slate-500">Reported {new Date(outcome.reported_at).toLocaleDateString()}</p>
                </div>
                <OutcomeStatusBadge label={outcome.outcome_label} />
              </div>
              <p className="mt-2 text-xs text-slate-600">Training consent: {outcome.training_consent ? "granted" : "not granted"}</p>
              <button type="button" onClick={() => onOpen(outcome)} className="mt-3 w-full border border-action bg-white px-3 py-2 text-sm font-semibold text-action hover:bg-action/5">
                Review or edit outcome
              </button>
            </article>
          ))}
        </div>
      ) : (
        <p className="mt-3 border border-line bg-panel p-3 text-xs leading-5 text-slate-600">No locally known reported outcomes yet. Reports submitted from this browser will appear here.</p>
      )}
    </section>
  );
}

function OutcomeStatusBadge({ label }: { label: OutcomeReport["outcome_label"] }) {
  const className =
    label === "positive"
      ? "border-action/40 bg-action/10 text-action"
      : label === "negative"
        ? "border-red-300 bg-red-50 text-red-700"
        : "border-warning/40 bg-amber-50 text-warning";
  return <span className={`border px-2 py-1 text-xs font-semibold capitalize ${className}`}>{label}</span>;
}

function PendingOutcomeToast({ prompt, onOpen, onDismiss }: { prompt: PendingOutcomePrompt; onOpen: (prompt: PendingOutcomePrompt) => void; onDismiss: (prompt: PendingOutcomePrompt) => void }) {
  return (
    <aside className="fixed bottom-4 right-4 z-40 w-[calc(100%-2rem)] max-w-md border border-action/30 bg-white p-4 shadow-subtle" aria-label="Pending outcome prompt">
      <p className="text-xs font-semibold uppercase text-action">Outcome follow-up</p>
      <p className="mt-1 text-sm text-slate-800">Design {prompt.design_id} is ready for lab outcome feedback.</p>
      <p className="mt-1 text-xs text-slate-500">Created {prompt.days_since_created} days ago.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" onClick={() => onOpen(prompt)} className="border border-action bg-action px-3 py-2 text-sm font-semibold text-white">
          Report outcome
        </button>
        <button type="button" onClick={() => onDismiss(prompt)} className="border border-line px-3 py-2 text-sm font-semibold text-slate-700">
          Not now
        </button>
      </div>
    </aside>
  );
}

function OutcomePanel({ designId, latestOutcome, onOpen }: { designId: string | null; latestOutcome: OutcomeReport | null; onOpen: () => void }) {
  return (
    <section className="border border-line bg-white p-4 shadow-subtle" aria-label="Outcome reporting">
      <h2 className="text-sm font-semibold">Lab outcome</h2>
      <p className="mt-1 text-xs leading-5 text-slate-600">
        {designId
          ? latestOutcome
            ? `Outcome reported ${new Date(latestOutcome.reported_at).toLocaleDateString()}.`
            : "Have lab results for this design? Failed and inconclusive results are useful too."
          : "Complete a design job to report lab results."}
      </p>
      {latestOutcome ? (
        <p className="mt-2 text-xs text-slate-500">Training consent: {latestOutcome.training_consent ? "granted" : "not granted"}</p>
      ) : null}
      <button
        type="button"
        disabled={!designId}
        onClick={onOpen}
        className="mt-4 w-full border border-action bg-action px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-300"
      >
        {latestOutcome ? "Review or edit outcome" : "Report outcome"}
      </button>
    </section>
  );
}

function JobProgressCard({ jobId, state, elapsedMs }: { jobId: string | null; state: UiState; elapsedMs: number }) {
  const elapsedSeconds = Math.max(0, Math.round(elapsedMs / 1000));
  const label = state === "submitting" ? "Starting design job" : "Designing and validating plasmid";
  return (
    <article className="max-w-3xl border border-action/30 bg-action/5 p-4 shadow-subtle">
      <div className="mb-2 flex items-center justify-between gap-4 text-xs font-semibold uppercase text-action">
        <span>{label}</span>
        <span>{elapsedSeconds}s</span>
      </div>
      <div className="space-y-2" aria-hidden>
        <div className="h-2 w-full overflow-hidden bg-white">
          <div className="h-full w-2/3 animate-pulse bg-action/40" />
        </div>
        <div className="grid grid-cols-3 gap-2 text-xs text-slate-600">
          <span>Retrieving templates</span>
          <span>Generating candidate</span>
          <span>Running checks</span>
        </div>
      </div>
      {jobId ? <p className="mt-3 text-xs text-slate-500">Job ID: {jobId}</p> : null}
    </article>
  );
}

function ValidationReportPanel({ report }: { report: ValidationReport }) {
  const checks = report.checks ?? [];
  const overall = report.overall ?? (checks.some((check) => normalizeStatus(check.status) === "FAIL") ? "FAIL" : "PASS");
  return (
    <section className="mt-4 border border-line bg-panel p-3" aria-label="Validation report">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase text-slate-600">Validation report</h3>
        <StatusBadge status={overall} />
      </div>
      {report.generated_by_model_version ? (
        <p className="mt-1 text-xs text-slate-500">Model: {report.generated_by_model_version}</p>
      ) : null}
      {checks.length ? (
        <div className="mt-3 space-y-2">
          {checks.map((check, index) => (
            <div key={`${checkTitle(check)}-${index}`} className="border border-line bg-white p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium text-slate-800">{checkTitle(check)}</p>
                <StatusBadge status={check.status ?? "PASS"} />
              </div>
              {check.message ? <p className="mt-1 text-xs leading-5 text-slate-600">{check.message}</p> : null}
              {regionLabel(check) ? <p className="mt-1 text-xs text-slate-500">Region: {regionLabel(check)}</p> : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-xs text-slate-500">No individual checks were returned.</p>
      )}
    </section>
  );
}

function StatusBadge({ status }: { status: string }) {
  const normalized = normalizeStatus(status);
  const className =
    normalized === "PASS"
      ? "border-action/40 bg-action/10 text-action"
      : normalized === "WARN"
        ? "border-warning/40 bg-amber-50 text-warning"
        : normalized === "FAIL"
          ? "border-red-300 bg-red-50 text-red-700"
          : "border-slate-300 bg-slate-50 text-slate-600";
  return <span className={`border px-2 py-1 text-xs font-semibold ${className}`}>{normalized}</span>;
}

function normalizeStatus(status: string | undefined): string {
  return (status ?? "UNKNOWN").toUpperCase();
}

function checkTitle(check: ValidationCheck): string {
  return check.name ?? check.check ?? check.category ?? "Validation check";
}

function regionLabel(check: ValidationCheck): string | null {
  const explicitRegions = check.regions
    ?.map((region) => {
      if (typeof region.start !== "number" || typeof region.end !== "number") {
        return region.label ?? region.feature ?? null;
      }
      return `${region.label ?? region.feature ?? "region"} ${region.start + 1}..${region.end}`;
    })
    .filter(Boolean);
  if (explicitRegions?.length) {
    return explicitRegions.join(", ");
  }
  if (typeof check.start === "number" && typeof check.end === "number") {
    return `${check.start + 1}..${check.end}`;
  }
  return null;
}

function jobError(job: JobStatusResponse): ApiError {
  const detail = job.error_detail;
  if (detail) {
    return new ApiError(detail.message, {
      code: detail.code,
      retryable: detail.retryable,
      details: detail.details
    });
  }
  return new ApiError(job.error ?? "The design job failed before producing a result.", { code: "job_failed" });
}

function friendlyErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const fieldText = error.fieldErrors.length
      ? ` ${error.fieldErrors.map((field) => `${field.field}: ${field.message}`).join(" ")}`
      : "";
    const retryText = error.retryable ? " Try again in a moment." : "";
    return `${error.message}${fieldText}${retryText}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "The design request failed.";
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

function promptKey(prompt: PendingOutcomePrompt): string {
  return `${prompt.design_id}:${prompt.session_id}`;
}

function readDismissedPromptKeys(): string[] {
  try {
    const raw = window.sessionStorage.getItem(DISMISSED_OUTCOME_PROMPTS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : [];
  } catch {
    return [];
  }
}

function persistDismissedPromptKey(current: string[], key: string): string[] {
  const next = current.includes(key) ? current : [...current, key];
  try {
    window.sessionStorage.setItem(DISMISSED_OUTCOME_PROMPTS_KEY, JSON.stringify(next));
  } catch {
    return next;
  }
  return next;
}

function readReportedOutcomes(): OutcomeReport[] {
  try {
    const raw = window.localStorage.getItem(REPORTED_OUTCOMES_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(isOutcomeReport);
  } catch {
    return [];
  }
}

function persistReportedOutcomes(outcomes: OutcomeReport[]): OutcomeReport[] {
  try {
    window.localStorage.setItem(REPORTED_OUTCOMES_KEY, JSON.stringify(outcomes));
  } catch {
    return outcomes;
  }
  return outcomes;
}

function upsertReportedOutcome(current: OutcomeReport[], outcome: OutcomeReport): OutcomeReport[] {
  return mergeReportedOutcomes(current, [outcome]);
}

function mergeReportedOutcomes(current: OutcomeReport[], incoming: OutcomeReport[]): OutcomeReport[] {
  const byDesignId = new Map(current.map((outcome) => [outcome.design_id, outcome]));
  for (const outcome of incoming) {
    byDesignId.set(outcome.design_id, outcome);
  }
  return Array.from(byDesignId.values()).sort((a, b) => new Date(b.reported_at).getTime() - new Date(a.reported_at).getTime());
}

function isOutcomeReport(value: unknown): value is OutcomeReport {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Partial<OutcomeReport>;
  return (
    typeof record.design_id === "string" &&
    typeof record.model_version === "string" &&
    typeof record.training_consent === "boolean" &&
    (record.outcome_label === "positive" || record.outcome_label === "negative" || record.outcome_label === "ambiguous") &&
    typeof record.reported_at === "string"
  );
}
