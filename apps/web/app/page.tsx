"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiError, createSession, exportDesign, getOutcome, getPendingOutcomePrompts, pollJob, submitDesign, submitRefinement } from "@/lib/api";
import { ExportActions, type ExportFormat, type ExportStatus } from "@/components/export-actions";
import { OutcomeReportModal } from "@/components/outcome-report-modal";
import { PlasmidMapView } from "@/components/plasmid-map-view";
import type { AnnotatedSequence, JobResultPayload, JobStatusResponse, OutcomeReport, PendingOutcomePrompt, ValidationCheck, ValidationReport } from "@/lib/types";

type UiState = "idle" | "submitting" | "polling" | "poll_timeout" | "ready" | "awaiting_clarification" | "error";
type PendingPromptStatus = "loading" | "ready" | "error";

type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  kind: "prompt" | "clarification_answer" | "result" | "clarification" | "status" | "error";
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
const INITIAL_EXPORT_STATUS: Record<ExportFormat, ExportStatus> = { genbank: "idle", fasta: "idle" };
const INITIAL_EXPORT_ERRORS: Record<ExportFormat, string | null> = { genbank: null, fasta: null };

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
  const [exportStatus, setExportStatus] = useState<Record<ExportFormat, ExportStatus>>(INITIAL_EXPORT_STATUS);
  const [exportError, setExportError] = useState<Record<ExportFormat, string | null>>(INITIAL_EXPORT_ERRORS);
  const [outcomeModalOpen, setOutcomeModalOpen] = useState(false);
  const [outcomeModalTarget, setOutcomeModalTarget] = useState<OutcomeModalTarget | null>(null);
  const [latestOutcome, setLatestOutcome] = useState<OutcomeReport | null>(null);
  const [reportedOutcomes, setReportedOutcomes] = useState<OutcomeReport[]>([]);
  const [pendingOutcomePrompts, setPendingOutcomePrompts] = useState<PendingOutcomePrompt[]>([]);
  const [pendingPromptStatus, setPendingPromptStatus] = useState<PendingPromptStatus>("loading");
  const [dismissedPromptKeys, setDismissedPromptKeys] = useState<string[]>([]);
  const [appStatus, setAppStatus] = useState("");
  const [outcomeRefreshStatus, setOutcomeRefreshStatus] = useState<"idle" | "refreshing" | "error">("idle");
  const [threadOpen, setThreadOpen] = useState(false);
  const [inspectOpen, setInspectOpen] = useState(false);

  const latestResult = useMemo(
    () => [...messages].reverse().find((message) => message.result?.annotated_sequence)?.result,
    [messages]
  );
  const reportedOutcomeDesignIds = useMemo(
    () => Array.from(new Set(reportedOutcomes.map((outcome) => outcome.design_id))).sort().join("|"),
    [reportedOutcomes]
  );
  const annotatedSequence = latestResult?.annotated_sequence ?? null;
  const designId = latestResult?.design_id ?? latestResult?.design?.design_id ?? null;
  const modelVersion = latestResult?.validation_report?.generated_by_model_version ?? latestResult?.design?.validation_report?.generated_by_model_version ?? null;
  const isBusy = state === "submitting" || state === "polling";
  const isPollTimeoutRecovery = state === "poll_timeout" && Boolean(activeJobId);
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
    setPendingPromptStatus("loading");
    getPendingOutcomePrompts()
      .then((prompts) => {
        if (!cancelled) {
          setPendingOutcomePrompts(prompts);
          setPendingPromptStatus("ready");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPendingOutcomePrompts([]);
          setPendingPromptStatus("error");
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
    const designIds = reportedOutcomeDesignIds ? reportedOutcomeDesignIds.split("|") : [];
    if (!designIds.length) {
      setOutcomeRefreshStatus("idle");
      return;
    }
    setOutcomeRefreshStatus("refreshing");
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
        setOutcomeRefreshStatus("idle");
      } else {
        setOutcomeRefreshStatus("error");
      }
    });
    return () => {
      cancelled = true;
    };
  }, [reportedOutcomeDesignIds]);

  useEffect(() => {
    setExportStatus({ ...INITIAL_EXPORT_STATUS });
    setExportError({ ...INITIAL_EXPORT_ERRORS });
  }, [designId]);

  const visiblePendingPrompt = pendingOutcomePrompts.find((prompt) => !dismissedPromptKeys.includes(promptKey(prompt))) ?? null;
  const visiblePendingPromptKey = visiblePendingPrompt ? promptKey(visiblePendingPrompt) : null;

  useEffect(() => {
    if (visiblePendingPrompt) {
      setAppStatus(`Outcome follow-up available for design ${visiblePendingPrompt.design_id}.`);
    }
  }, [visiblePendingPromptKey, visiblePendingPrompt]);

  useEffect(() => {
    if (isBusy) {
      setThreadOpen(true);
    }
  }, [isBusy]);

  useEffect(() => {
    if (!threadOpen && !inspectOpen) {
      return;
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setThreadOpen(false);
        setInspectOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [threadOpen, inspectOpen]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || isBusy || isPollTimeoutRecovery) {
      return;
    }

    setInput("");
    setExportStatus({ ...INITIAL_EXPORT_STATUS });
    setExportError({ ...INITIAL_EXPORT_ERRORS });
    const submittedKind = state === "awaiting_clarification" ? "clarification_answer" : "prompt";
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", kind: submittedKind, text }
    ]);

    let keepActiveJob = false;
    try {
      setState("submitting");
      setAppStatus("Starting design job.");
      setJobStartedAt(Date.now());
      const currentSessionId = sessionId ?? (await createSession()).session_id;
      const hasExistingSession = Boolean(sessionId);
      setSessionId(currentSessionId);
      const response = hasExistingSession
        ? await submitRefinement(currentSessionId, text)
        : await submitDesign(currentSessionId, text);

      setActiveJobId(response.job_id);
      await pollAndApplyJob(response.job_id);
    } catch (error) {
      if (isPollingTimeout(error)) {
        keepActiveJob = true;
        const jobId = String(error.details.job_id ?? activeJobId ?? "unknown");
        setActiveJobId(jobId);
        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "system",
            kind: "status",
            text: `Job ${jobId} is still queued or running. Keep this page open, confirm the local worker or demo fixture is running, then use Check status to resume polling.`
          }
        ]);
        setState("poll_timeout");
        setAppStatus(`Job ${jobId} is still queued or running. Check the local worker or demo fixture before retrying.`);
        return;
      }
      const text = friendlyErrorMessage(error);
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "system", kind: "error", text }
      ]);
      setState("error");
      setAppStatus(`Design failed. ${text}`);
    } finally {
      if (!keepActiveJob) {
        setActiveJobId(null);
        setJobStartedAt(null);
      }
    }
  }

  async function handleCheckJob() {
    if (!activeJobId || isBusy) {
      return;
    }
    let keepActiveJob = false;
    try {
      setJobStartedAt(Date.now());
      await pollAndApplyJob(activeJobId);
    } catch (error) {
      if (isPollingTimeout(error)) {
        keepActiveJob = true;
        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "system",
            kind: "status",
            text: `Job ${activeJobId} is still queued or running. Confirm the local worker or demo fixture is running, then try again.`
          }
        ]);
        setState("poll_timeout");
        setAppStatus(`Job ${activeJobId} is still queued or running. Check the local worker or demo fixture before retrying.`);
        return;
      }
      const text = friendlyErrorMessage(error);
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "system", kind: "error", text }
      ]);
      setState("error");
      setAppStatus(`Status check failed. ${text}`);
    } finally {
      if (!keepActiveJob) {
        setActiveJobId(null);
        setJobStartedAt(null);
      }
    }
  }

  async function pollAndApplyJob(jobId: string) {
    setState("polling");
    setAppStatus("Designing and validating plasmid.");
    const job = await pollJob(jobId, { onUpdate: () => setNow(Date.now()) });
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
      setAppStatus("Clarification needed.");
    } else {
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "assistant", kind: "result", text: resultSummary(result), result }
      ]);
      setState("ready");
      setAppStatus("Design complete.");
    }
  }

  async function handleExport(format: ExportFormat) {
    if (!designId || isBusy) {
      return;
    }
    setExportError((current) => ({ ...current, [format]: null }));
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
      setExportError((current) => ({ ...current, [format]: `${formatLabel(format)} export failed. ${friendlyErrorMessage(error)}` }));
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

  function handleStartOverAfterTimeout() {
    const abandonedJobId = activeJobId;
    setActiveJobId(null);
    setJobStartedAt(null);
    setSessionId(null);
    setState("idle");
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "system",
        kind: "status",
        text: abandonedJobId
          ? `Stopped waiting for job ${abandonedJobId}. Start a new design when the demo fixture or worker is ready.`
          : "Stopped waiting for the previous job. Start a new design when the demo fixture or worker is ready."
      }
    ]);
    setAppStatus("Timed-out job abandoned. Start a new design when the demo fixture or worker is ready.");
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
    <main className="flex h-screen flex-col bg-cream font-sans text-ink">
      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">{appStatus}</p>
      {visiblePendingPrompt ? (
        <PendingOutcomeToast prompt={visiblePendingPrompt} onOpen={openPromptOutcomeModal} onDismiss={dismissPrompt} />
      ) : null}

      <header className="flex h-14 items-center gap-sm border-b border-line bg-paper px-md md:h-12" role="banner">
        <span className="font-serif text-h3 text-ink">PlasmidAI</span>
        <span className="mx-2xs hidden h-6 w-px bg-line-strong sm:block" aria-hidden />
        <h1 id="design-workspace-title" className="font-serif text-h3 text-ink">Design workspace</h1>
        <div className="ml-auto flex items-center gap-xs">
          <button
            type="button"
            onClick={() => setInspectOpen(true)}
            className="hidden rounded-md border border-line bg-paper px-sm py-2xs text-xs font-semibold text-ink hover:border-line-strong focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40 md:inline-flex lg:hidden"
          >
            Inspect
          </button>
          <button
            type="button"
            onClick={() => setThreadOpen((open) => !open)}
            aria-expanded={threadOpen}
            aria-controls="design-thread"
            className="rounded-md border border-line bg-paper px-sm py-2xs text-xs font-semibold text-ink hover:border-line-strong focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40"
          >
            {threadOpen ? "Hide conversation" : "Show conversation"}
          </button>
        </div>
      </header>

      <div className="relative min-h-0 flex-1">
        <div className="hidden h-full md:grid md:grid-cols-1 lg:grid-cols-[56px_minmax(0,1fr)_320px]">
          <nav className="hidden flex-col items-center gap-sm border-r border-line bg-paper py-md md:flex lg:flex" aria-label="Workspace navigation">
            <button
              type="button"
              onClick={() => setThreadOpen((open) => !open)}
              aria-expanded={threadOpen}
              aria-controls="design-thread"
              aria-label="Toggle conversation"
              className="flex h-8 w-8 items-center justify-center rounded-md border border-line bg-paper text-ink hover:border-line-strong focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40"
            >
              <svg viewBox="0 0 16 16" className="h-4 w-4" aria-hidden="true">
                <path fill="currentColor" d="M2 3h12v8H6l-3 3v-3H2V3zm1 1v6h2v1.5L6.5 10H13V4H3z" />
              </svg>
            </button>
            <div className="mt-auto flex w-full flex-col items-center gap-xs px-2xs" aria-hidden>
              <span className="h-8 w-8 rounded-md border border-dashed border-line" />
              <span className="h-8 w-8 rounded-md border border-dashed border-line" />
            </div>
          </nav>

          <div className="flex min-h-0 min-w-0 flex-col bg-cream p-sm md:p-md">
            <PlasmidMapView annotatedSequence={annotatedSequence as AnnotatedSequence | null} />
          </div>

          <aside className="hidden min-h-0 overflow-y-auto border-l border-line bg-paper px-sm py-md lg:block" aria-labelledby="right-rail-title">
            <h2 id="right-rail-title" className="sr-only">Workspace panels</h2>
            <div className="space-y-md">
              {pendingPromptStatus === "error" ? <PendingPromptFetchMessage /> : null}
              {isBusy ? <RightRailJobNotice jobId={activeJobId} hasPreviousDesign={Boolean(designId)} /> : null}
              <ValidationSummary report={latestResult?.validation_report ?? null} onOpenThread={() => setThreadOpen(true)} />
              <ExportActions designId={designId} status={exportStatus} error={exportError} disabledReason={isBusy ? "A new design job is running. Exports stay disabled to avoid downloading the previous design by mistake." : null} onExport={handleExport} />
              <OutcomePanel designId={designId} latestOutcome={latestOutcome} disabledReason={isBusy ? "A new design job is running. Outcome reporting is disabled until the current result is ready." : null} onOpen={openCurrentOutcomeModal} />
              <MyOutcomesPanel outcomes={reportedOutcomes} onOpen={openReportedOutcomeModal} refreshStatus={outcomeRefreshStatus} />
            </div>
          </aside>
        </div>

        <div className="h-full overflow-y-auto md:hidden">
          <div className="flex min-h-0 flex-col">
            <div className="h-[55vh] min-h-0 p-sm">
              <PlasmidMapView annotatedSequence={annotatedSequence as AnnotatedSequence | null} />
            </div>
            <section className="flex gap-xs border-t border-line bg-paper p-sm" aria-label="Export actions">
              <button
                type="button"
                disabled={!designId || isBusy}
                onClick={() => void handleExport("genbank")}
                className="flex-1 rounded-md border border-line-strong bg-paper px-sm py-2xs text-sm font-semibold text-ink hover:bg-mist focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40 disabled:cursor-not-allowed disabled:border-line disabled:bg-paper disabled:text-slate disabled:hover:bg-paper"
              >
                GenBank
              </button>
              <button
                type="button"
                disabled={!designId || isBusy}
                onClick={() => void handleExport("fasta")}
                className="flex-1 rounded-md border border-line-strong bg-paper px-sm py-2xs text-sm font-semibold text-ink hover:bg-mist focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40 disabled:cursor-not-allowed disabled:border-line disabled:bg-paper disabled:text-slate disabled:hover:bg-paper"
              >
                FASTA
              </button>
            </section>
            <div className="space-y-md p-sm">
              {pendingPromptStatus === "error" ? <PendingPromptFetchMessage /> : null}
              {isBusy ? <RightRailJobNotice jobId={activeJobId} hasPreviousDesign={Boolean(designId)} /> : null}
              <ValidationSummary report={latestResult?.validation_report ?? null} onOpenThread={() => setThreadOpen(true)} />
              <OutcomePanel designId={designId} latestOutcome={latestOutcome} disabledReason={isBusy ? "A new design job is running. Outcome reporting is disabled until the current result is ready." : null} onOpen={openCurrentOutcomeModal} />
              <MyOutcomesPanel outcomes={reportedOutcomes} onOpen={openReportedOutcomeModal} refreshStatus={outcomeRefreshStatus} />
            </div>
          </div>
        </div>

        {threadOpen ? (
          <>
            <button
              type="button"
              aria-label="Dismiss conversation"
              tabIndex={-1}
              onClick={() => setThreadOpen(false)}
              className="absolute inset-x-0 bottom-0 top-0 z-20 bg-ink/30 lg:left-14 lg:right-[320px]"
            />
            <div
              id="design-thread"
              role="dialog"
              aria-label="Conversation history"
              className="absolute inset-x-0 bottom-0 z-30 flex max-h-[60vh] flex-col bg-paper shadow-floating lg:left-14 lg:right-[320px]"
            >
              <div className="flex items-center justify-between gap-sm border-b border-line px-md py-sm">
                <h2 className="font-serif text-h3 text-ink">Conversation</h2>
                <button
                  type="button"
                  onClick={() => setThreadOpen(false)}
                  className="rounded-md border border-line bg-paper px-sm py-2xs text-xs font-semibold text-ink hover:border-line-strong focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40"
                >
                  Hide
                </button>
              </div>
              <div className="flex-1 space-y-sm overflow-y-auto px-md py-md">
                {messages.map((message) => (
                  <article
                    key={message.id}
                    className={`max-w-3xl border p-4 shadow-rest ${
                      message.role === "user"
                        ? "ml-auto border-coral/30 bg-coral/5"
                        : message.kind === "error"
                          ? "border-clay/40 bg-clay/5"
                          : message.kind === "clarification"
                            ? "border-honey/40 bg-honey/5"
                            : "border-line bg-paper"
                    }`}
                  >
                    <div className="mb-2 text-xs font-semibold uppercase text-slate">
                      {message.role === "user"
                        ? message.kind === "clarification_answer"
                          ? "Clarification answer"
                          : "Researcher"
                        : message.kind === "clarification"
                          ? "Clarification"
                          : message.kind === "status"
                            ? "Job status"
                            : "Design agent"}
                    </div>
                    <p className="whitespace-pre-wrap text-sm leading-6 text-ink">{message.text}</p>
                    {message.result ? (
                      message.result.validation_report ? <ValidationReportPanel report={message.result.validation_report} /> : <MissingValidationReportPanel />
                    ) : null}
                    {message.result && !message.result.annotated_sequence ? <PartialResultNotice result={message.result} /> : null}
                    {message.result ? <RetrievedTemplatesPanel result={message.result} messageId={message.id} /> : null}
                    {message.result?.annotated_sequence ? (
                      <a
                        href="#plasmid-map"
                        onClick={() => setThreadOpen(false)}
                        className="mt-3 inline-flex rounded-sm text-xs font-semibold text-coral focus:outline-none focus:ring-2 focus:ring-coral/40"
                      >
                        View plasmid map
                      </a>
                    ) : null}
                  </article>
                ))}
                {isBusy ? (
                  <JobProgressCard jobId={activeJobId} state={state} elapsedMs={jobStartedAt ? now - jobStartedAt : 0} />
                ) : null}
              </div>
            </div>
          </>
        ) : null}

        {inspectOpen ? (
          <div className="absolute inset-0 z-30 hidden md:flex lg:hidden">
            <button
              type="button"
              aria-label="Close inspector"
              tabIndex={-1}
              onClick={() => setInspectOpen(false)}
              className="absolute inset-0 bg-ink/30"
            />
            <aside className="relative ml-auto h-full w-[320px] overflow-y-auto border-l border-line-strong bg-paper p-md shadow-floating" aria-labelledby="right-rail-title">
              <div className="mb-sm flex items-center justify-between">
                <h2 id="right-rail-title" className="sr-only">Workspace panels</h2>
                <button
                  type="button"
                  onClick={() => setInspectOpen(false)}
                  className="ml-auto rounded-md border border-line bg-paper px-sm py-2xs text-xs font-semibold text-ink hover:border-line-strong focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40"
                >
                  Close
                </button>
              </div>
              <div className="space-y-md">
                {pendingPromptStatus === "error" ? <PendingPromptFetchMessage /> : null}
                {isBusy ? <RightRailJobNotice jobId={activeJobId} hasPreviousDesign={Boolean(designId)} /> : null}
                <ValidationSummary report={latestResult?.validation_report ?? null} onOpenThread={() => { setInspectOpen(false); setThreadOpen(true); }} />
                <ExportActions designId={designId} status={exportStatus} error={exportError} disabledReason={isBusy ? "A new design job is running. Exports stay disabled to avoid downloading the previous design by mistake." : null} onExport={handleExport} />
                <OutcomePanel designId={designId} latestOutcome={latestOutcome} disabledReason={isBusy ? "A new design job is running. Outcome reporting is disabled until the current result is ready." : null} onOpen={openCurrentOutcomeModal} />
                <MyOutcomesPanel outcomes={reportedOutcomes} onOpen={openReportedOutcomeModal} refreshStatus={outcomeRefreshStatus} />
              </div>
            </aside>
          </div>
        ) : null}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-line bg-paper px-md py-md" aria-label="Design composer">
        {state === "awaiting_clarification" && activeClarification ? (
          <div className="mb-3 rounded-md border border-honey/40 bg-honey/10 p-md text-sm text-ink">
            <span className="font-semibold text-honey">Clarification needed: </span>
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
                className="rounded-md border border-line bg-paper px-sm py-xs text-left text-xs text-ink hover:bg-mist focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40"
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
            disabled={isBusy || isPollTimeoutRecovery}
            rows={3}
            className="min-h-24 flex-1 resize-none rounded-md border border-line bg-paper px-md py-sm text-sm text-ink shadow-rest outline-none focus:border-coral focus:ring-2 focus:ring-coral/40"
            placeholder={
              state === "awaiting_clarification"
                ? "Answer the clarification question..."
                : "Describe the host, marker, payload, promoter, and any constraints..."
            }
          />
          <button
            type="submit"
            disabled={!input.trim() || isBusy || isPollTimeoutRecovery}
            className="h-12 rounded-md border border-coral bg-coral px-md text-sm font-semibold text-paper shadow-rest hover:shadow-raised focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40 disabled:cursor-not-allowed disabled:border-line disabled:bg-line disabled:text-slate disabled:shadow-none"
          >
            {state === "submitting" ? "Starting" : state === "polling" ? "Designing" : state === "awaiting_clarification" ? "Answer" : sessionId ? "Refine" : "Design"}
          </button>
        </div>
        {activeJobId ? (
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate">
            <span>
              Job {activeJobId} is still queued or running. For a local demo, confirm the worker or deterministic demo fixture is running before retrying.
            </span>
            {state === "poll_timeout" ? (
              <>
                <button type="button" className="rounded-sm font-semibold text-coral focus:outline-none focus:ring-2 focus:ring-coral/40" onClick={() => void handleCheckJob()}>
                  Check status
                </button>
                <button type="button" className="rounded-sm font-semibold text-ink hover:text-coral focus:outline-none focus:ring-2 focus:ring-coral/40" onClick={handleStartOverAfterTimeout}>
                  Start over
                </button>
              </>
            ) : null}
          </div>
        ) : null}
      </form>

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

function MyOutcomesPanel({ outcomes, onOpen, refreshStatus }: { outcomes: OutcomeReport[]; onOpen: (outcome: OutcomeReport) => void; refreshStatus: "idle" | "refreshing" | "error" }) {
  const sortedOutcomes = [...outcomes].sort((a, b) => new Date(b.reported_at).getTime() - new Date(a.reported_at).getTime());
  return (
    <section className="rounded-md border border-line bg-paper p-md shadow-rest" aria-label="My reported outcomes">
      <div className="flex flex-wrap items-start justify-between gap-sm">
        <div>
          <h2 className="font-serif text-h3 text-ink">My outcomes</h2>
          <p className="mt-2xs text-small leading-5 text-slate">
            Shows outcomes reported from this browser until a backend list endpoint is available. Known designs are refreshed individually when possible.
          </p>
        </div>
        <span className="rounded-sm border border-line bg-mist px-xs py-2xs text-caption font-semibold text-slate">{outcomes.length}</span>
      </div>
      {refreshStatus === "refreshing" ? (
        <p className="mt-sm flex items-center gap-xs text-small text-slate" role="status" aria-busy="true">
          <span className="h-2 w-2 animate-pulse rounded-pill bg-coral" aria-hidden="true" />
          Refreshing outcomes...
        </p>
      ) : null}
      {refreshStatus === "error" && sortedOutcomes.length ? (
        <p className="mt-sm rounded-md border border-line bg-mist p-sm text-small leading-5 text-slate">Could not refresh saved outcomes. The list below shows the most recent reports saved in this browser.</p>
      ) : null}
      {sortedOutcomes.length ? (
        <div className="mt-sm space-y-sm">
          {sortedOutcomes.map((outcome) => (
            <article key={outcome.design_id} className="rounded-md border border-line bg-mist p-md">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="break-all text-sm font-semibold text-ink">{outcome.design_id}</p>
                  <p className="mt-2xs text-xs text-slate">Reported {new Date(outcome.reported_at).toLocaleDateString()}</p>
                </div>
                <OutcomeStatusBadge label={outcome.outcome_label} />
              </div>
              <p className="mt-2 text-small text-slate">Training consent: {outcome.training_consent ? "granted" : "not granted"}</p>
              <button type="button" onClick={() => onOpen(outcome)} className="mt-sm w-full rounded-md border border-coral bg-coral px-md py-sm text-sm font-semibold text-paper shadow-rest hover:shadow-raised focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40 disabled:cursor-not-allowed disabled:border-line disabled:bg-line disabled:text-slate disabled:shadow-none">
                Review or edit outcome
              </button>
            </article>
          ))}
        </div>
      ) : (
        <p className="mt-sm rounded-md border border-line bg-mist p-sm text-small leading-5 text-slate">No locally known reported outcomes yet. Reports submitted from this browser will appear here.</p>
      )}
    </section>
  );
}

function OutcomeStatusBadge({ label }: { label: OutcomeReport["outcome_label"] }) {
  const className =
    label === "positive"
      ? "border-sage/40 bg-sage/10 text-sage"
      : label === "negative"
        ? "border-clay/40 bg-clay/10 text-clay"
        : "border-honey/40 bg-honey/10 text-honey";
  return <span className={`rounded-pill border px-xs py-2xs text-caption font-semibold capitalize ${className}`}>{label}</span>;
}

function PendingOutcomeToast({ prompt, onOpen, onDismiss }: { prompt: PendingOutcomePrompt; onOpen: (prompt: PendingOutcomePrompt) => void; onDismiss: (prompt: PendingOutcomePrompt) => void }) {
  return (
    <aside className="fixed left-4 right-4 top-4 z-40 rounded-lg border border-line bg-paper p-md shadow-floating sm:left-auto sm:top-auto sm:bottom-4 sm:w-[calc(100%-2rem)] sm:max-w-md" aria-label="Pending outcome prompt">
      <p className="text-caption font-semibold uppercase tracking-[0.06em] text-coral">Outcome follow-up</p>
      <p className="mt-2xs text-sm text-ink">Design {prompt.design_id} is ready for lab outcome feedback.</p>
      <p className="mt-2xs text-xs text-slate">Created {prompt.days_since_created} days ago.</p>
      <div className="mt-sm flex flex-wrap gap-2">
        <button type="button" onClick={() => onOpen(prompt)} className="rounded-md border border-coral bg-coral px-md py-sm text-sm font-semibold text-paper shadow-rest hover:shadow-raised focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40">
          Report outcome
        </button>
        <button type="button" onClick={() => onDismiss(prompt)} className="rounded-md border border-line-strong bg-paper px-md py-sm text-sm font-semibold text-ink hover:bg-mist focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40">
          Not now
        </button>
      </div>
    </aside>
  );
}

function RightRailJobNotice({ jobId, hasPreviousDesign }: { jobId: string | null; hasPreviousDesign: boolean }) {
  return (
    <section className="rounded-md border border-line bg-mist p-md shadow-rest" role="status" aria-live="polite">
      <p className="flex items-center gap-xs text-caption font-semibold uppercase tracking-[0.06em] text-coral">
        <span className="h-2 w-2 animate-pulse rounded-pill bg-coral" aria-hidden="true" />
        Design running
      </p>
      <p className="mt-2xs text-sm leading-6 text-slate">
        {hasPreviousDesign
          ? "A new design is running. The panels below still show the last completed design until the current result is ready."
          : "A design is running. The map, export, and outcome panels will update when the result is ready."}
      </p>
      {jobId ? <p className="mt-2 text-xs text-slate">Job ID: {jobId}</p> : null}
    </section>
  );
}

function PendingPromptFetchMessage() {
  return (
    <section className="rounded-md border border-line bg-paper p-sm text-small leading-5 text-slate shadow-rest" aria-label="Outcome prompt status">
      Outcome follow-ups could not be checked. You can continue designing; prompts will be checked again on reload.
    </section>
  );
}

function ValidationSummary({ report, onOpenThread }: { report: ValidationReport | null; onOpenThread: () => void }) {
  if (!report) {
    return (
      <section className="rounded-md border border-line bg-paper p-md shadow-rest" aria-label="Validation summary">
        <h2 className="font-serif text-h3 text-ink">Validation</h2>
        <p className="mt-2xs text-small leading-5 text-slate">No validation report yet. Run a design job to see assembly checks.</p>
      </section>
    );
  }
  const checks = report.checks ?? [];
  const overall = report.overall ?? (checks.some((check) => normalizeStatus(check.status) === "FAIL")
    ? "FAIL"
    : checks.some((check) => normalizeStatus(check.status) === "WARN")
      ? "WARN"
      : "PASS");
  const badgeClass =
    overall === "PASS"
      ? "border-sage/40 bg-sage/10 text-sage"
      : overall === "WARN"
        ? "border-honey/40 bg-honey/10 text-honey"
        : "border-clay/40 bg-clay/10 text-clay";
  return (
    <section className="rounded-md border border-line bg-paper p-md shadow-rest" aria-label="Validation summary">
      <div className="flex items-center justify-between gap-sm">
        <h2 className="font-serif text-h3 text-ink">Validation</h2>
        <span className={`rounded-pill border px-xs py-2xs text-caption font-semibold uppercase tracking-[0.06em] ${badgeClass}`}>{overall}</span>
      </div>
      <p className="mt-2 text-small leading-5 text-slate">{checks.length} check{checks.length === 1 ? "" : "s"} reported.</p>
      <button
        type="button"
        onClick={onOpenThread}
        className="mt-2 text-xs font-semibold text-coral hover:underline focus:outline-none focus:ring-2 focus:ring-coral/40"
      >
        Open full report
      </button>
    </section>
  );
}

function OutcomePanel({ designId, latestOutcome, disabledReason, onOpen }: { designId: string | null; latestOutcome: OutcomeReport | null; disabledReason: string | null; onOpen: () => void }) {
  const disabled = !designId || Boolean(disabledReason);
  return (
    <section className="rounded-md border border-line bg-paper p-md shadow-rest" aria-label="Outcome reporting">
      <h2 className="font-serif text-h3 text-ink">Lab outcome</h2>
      <p className="mt-2xs text-small leading-5 text-slate">
        {disabledReason
          ? disabledReason
          : designId
          ? latestOutcome
            ? `Outcome reported ${new Date(latestOutcome.reported_at).toLocaleDateString()}.`
            : "Have lab results for this design? Failed and inconclusive results are useful too."
          : "Complete a design job to report lab results."}
      </p>
      {latestOutcome ? (
        <p className="mt-2 text-xs text-slate">Training consent: {latestOutcome.training_consent ? "granted" : "not granted"}</p>
      ) : null}
      <button
        type="button"
        disabled={disabled}
        onClick={onOpen}
        className="mt-md w-full rounded-md border border-coral bg-coral px-md py-sm text-sm font-semibold text-paper shadow-rest hover:shadow-raised focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40 disabled:cursor-not-allowed disabled:border-line disabled:bg-line disabled:text-slate disabled:shadow-none"
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
    <article className="max-w-3xl rounded-md border border-line bg-mist p-md shadow-rest" role="status" aria-live="polite" aria-atomic="true">
      <div className="mb-2 flex items-center justify-between gap-md text-caption font-semibold uppercase tracking-[0.06em] text-coral">
        <span>{label}</span>
        <span aria-hidden="true">{elapsedSeconds}s</span>
      </div>
      <div className="space-y-sm" aria-hidden>
        <div className="h-2 w-full overflow-hidden rounded-pill bg-paper">
          <div className="h-full w-2/3 origin-left animate-pulse rounded-pill bg-coral/40" />
        </div>
        <div className="grid grid-cols-3 gap-sm text-sm text-slate">
          <span>Retrieving templates</span>
          <span>Generating candidate</span>
          <span>Running checks</span>
        </div>
      </div>
      {jobId ? <p className="mt-sm text-xs text-slate">Job ID: {jobId}</p> : null}
    </article>
  );
}

function RetrievedTemplatesPanel({ result, messageId }: { result: JobResultPayload; messageId: string }) {
  if (!Array.isArray(result.retrieved_templates)) {
    return <ResultNote title="Retrieved templates" text="Template retrieval was not returned for this job." />;
  }

  if (!result.retrieved_templates.length) {
    return <ResultNote title="Retrieved templates" text="No matching templates were retrieved." />;
  }

  return (
    <section className="mt-md rounded-md border border-line bg-mist p-md" aria-label="Retrieved template evidence">
      <h3 className="text-caption font-semibold uppercase tracking-[0.06em] text-slate">Retrieved template evidence</h3>
      <ul className="mt-sm space-y-2xs text-small text-slate">
        {result.retrieved_templates.slice(0, 3).map((template, index) => (
          <li key={`${messageId}-${template.source_id ?? index}`}>
            <span className="font-medium text-ink">Retrieved {index + 1}: {template.name ?? template.source_id ?? "template"}</span>{" "}
            {typeof template.score === "number" ? `(${template.score.toFixed(3)})` : ""}
            <span className="block text-slate">
              {[template.source_id, template.vector_profile, template.source].filter(Boolean).join(" · ") || "No additional source metadata returned."}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function MissingValidationReportPanel() {
  return <ResultNote title="Validation report" text="Validation report was not returned for this job." />;
}

function ResultNote({ title, text }: { title: string; text: string }) {
  return (
    <section className="mt-md rounded-md border border-line bg-mist p-md" aria-label={title}>
      <h3 className="text-caption font-semibold uppercase tracking-[0.06em] text-slate">{title}</h3>
      <p className="mt-2xs text-small leading-5 text-slate">{text}</p>
    </section>
  );
}

function ValidationReportPanel({ report }: { report: ValidationReport }) {
  const checks = report.checks ?? [];
  const overall = report.overall ?? (checks.some((check) => normalizeStatus(check.status) === "FAIL") ? "FAIL" : "PASS");
  return (
    <section className="mt-md rounded-md border border-line bg-mist p-md" aria-label="Validation report">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-caption font-semibold uppercase tracking-[0.06em] text-slate">Validation report</h3>
        <StatusBadge status={overall} />
      </div>
      {report.generated_by_model_version ? (
        <p className="mt-2xs text-xs text-slate">Model: {report.generated_by_model_version}</p>
      ) : null}
      {checks.length ? (
        <div className="mt-sm space-y-sm">
          {checks.map((check, index) => (
            <div key={`${checkTitle(check)}-${index}`} className="rounded-md border border-line bg-paper p-md">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium text-ink">{checkTitle(check)}</p>
                <StatusBadge status={check.status ?? "PASS"} />
              </div>
              {check.message ? <p className="mt-2xs text-small leading-5 text-slate">{check.message}</p> : null}
              {regionLabel(check) ? <p className="mt-2xs text-xs text-slate">Region: {regionLabel(check)}</p> : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-sm text-small text-slate">No individual checks were returned.</p>
      )}
    </section>
  );
}

function PartialResultNotice({ result }: { result: JobResultPayload }) {
  const hasEvidence = Boolean(result.retrieved_templates?.length || result.validation_report);
  if (!hasEvidence) {
    return null;
  }
  return (
    <section className="mt-md rounded-md border border-honey/40 bg-honey/10 p-md text-small leading-5 text-slate" aria-label="Partial result">
      <p className="font-semibold text-honey">Partial result</p>
      <p className="mt-2xs">
        The job returned supporting evidence but no annotated sequence, so the plasmid map and exports are not available yet. Refine the request or retry the job if a full design was expected.
      </p>
    </section>
  );
}

function StatusBadge({ status }: { status: string }) {
  const normalized = normalizeStatus(status);
  const className =
    normalized === "PASS"
      ? "border-sage/40 bg-sage/10 text-sage"
      : normalized === "WARN"
        ? "border-honey/40 bg-honey/10 text-honey"
        : normalized === "FAIL"
          ? "border-clay/40 bg-clay/10 text-clay"
          : "border-line-strong bg-mist text-slate";
  return <span className={`rounded-pill border px-xs py-2xs text-caption font-semibold uppercase tracking-[0.06em] ${className}`}>{normalized}</span>;
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

function formatLabel(format: ExportFormat): string {
  return format === "genbank" ? "GenBank" : "FASTA";
}

function isPollingTimeout(error: unknown): error is ApiError {
  return error instanceof ApiError && error.code === "job_poll_timeout";
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
