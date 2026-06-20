"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, submitOutcome } from "@/lib/api";
import type { OutcomeLabel, OutcomeReport } from "@/lib/types";

type OutcomeReportModalProps = {
  open: boolean;
  designId: string | null;
  modelVersion: string | null;
  onClose: () => void;
  onSubmitted?: (report: OutcomeReport) => void;
  initialReport?: OutcomeReport;
  provenanceContext?: Record<string, unknown>;
};

const testedMaterialOptions = [
  "Delivered design exactly",
  "A modified version",
  "Multiple clones from this design",
  "Not built or not tested",
  "I'm not sure"
];

const sequencingOptions = [
  "Matches expected regions",
  "Mismatch found",
  "Partial match",
  "Mixed or low quality",
  "Sequencing not performed",
  "Not applicable",
  "Inconclusive"
];

const expressionOptions = [
  "Met expected expression",
  "Below expected",
  "Absent",
  "Wrong product/localization",
  "Toxic or growth defect",
  "Not tested",
  "Not applicable",
  "Inconclusive"
];

const functionalOptions = [
  "Met expected function",
  "Below expected",
  "Absent",
  "Wrong product/localization",
  "Toxic or growth defect",
  "Not tested",
  "Not applicable",
  "Inconclusive"
];

const interpretationOptions = [
  "Accepted for intended use",
  "Did not validate",
  "Partially validated",
  "Attempted, but inconclusive",
  "Not built or not tested"
];

export function OutcomeReportModal({ open, ...props }: OutcomeReportModalProps) {
  if (!open) {
    return null;
  }

  return <OutcomeReportForm key={`${props.designId ?? "missing"}:${props.initialReport?.reported_at ?? "new"}`} {...props} />;
}

function OutcomeReportForm({ designId, modelVersion, onClose, onSubmitted, initialReport, provenanceContext }: Omit<OutcomeReportModalProps, "open">) {
  const [testedMaterial, setTestedMaterial] = useState(() => readStringProvenance(initialReport, "tested_material"));
  const [sequencingResult, setSequencingResult] = useState(() => initialReport?.sequencing_result ?? "");
  const [expressionResult, setExpressionResult] = useState(() => initialReport?.expression_result ?? "");
  const [functionalResult, setFunctionalResult] = useState(() => initialReport?.functional_result ?? "");
  const [interpretation, setInterpretation] = useState(() => interpretationFromReport(initialReport));
  const [notes, setNotes] = useState(() => initialReport?.notes ?? "");
  const [trainingConsent, setTrainingConsent] = useState(() => initialReport?.training_consent ?? false);
  const [consentReviewed, setConsentReviewed] = useState(() => Boolean(initialReport));
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [submittedReport, setSubmittedReport] = useState<OutcomeReport | null>(null);
  const [submitAttempted, setSubmitAttempted] = useState(false);

  const constructValidated = useMemo(() => {
    if (interpretation === "Accepted for intended use") {
      return true;
    }
    if (interpretation === "Did not validate") {
      return false;
    }
    return null;
  }, [interpretation]);

  const outcomeLabel = useMemo<OutcomeLabel>(() => {
    if (constructValidated === true) {
      return "positive";
    }
    if (constructValidated === false) {
      return "negative";
    }
    return "ambiguous";
  }, [constructValidated]);

  const validationIssues = useMemo(() => {
    const issues: string[] = [];
    if (!designId) {
      issues.push("Design context is missing.");
    }
    if (!modelVersion) {
      issues.push("Model version is missing.");
    }
    if (!interpretation && !sequencingResult && !expressionResult && !functionalResult) {
      issues.push("Add at least one observed result or overall interpretation.");
    }
    if (!consentReviewed) {
      issues.push("Choose whether this report may be used for model improvement.");
    }
    return issues;
  }, [consentReviewed, designId, expressionResult, functionalResult, interpretation, modelVersion, sequencingResult]);

  const evidenceMissing = !interpretation && !sequencingResult && !expressionResult && !functionalResult;

  const warnings = useMemo(() => {
    const items: string[] = [];
    if (interpretation === "Accepted for intended use" && sequencingResult && sequencingResult !== "Matches expected regions") {
      items.push("This report can be submitted, but sequencing evidence is incomplete or inconclusive.");
    }
    if (interpretation === "Did not validate" && sequencingResult === "Matches expected regions" && functionalResult === "Met expected function") {
      items.push("Reported evidence includes sequence match and expected function. Confirm the overall interpretation before submitting.");
    }
    if (testedMaterial === "A modified version") {
      items.push("Modified designs may require review before use for training.");
    }
    if (["Did not validate", "Partially validated", "Attempted, but inconclusive"].includes(interpretation) && !notes.trim()) {
      items.push("Notes are useful for failed, partial, or inconclusive outcomes.");
    }
    return items;
  }, [functionalResult, interpretation, notes, sequencingResult, testedMaterial]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitAttempted(true);
    setApiError(null);
    if (validationIssues.length || !designId || !modelVersion) {
      return;
    }

    const reportedAt = new Date().toISOString();
    const report: OutcomeReport = {
      design_id: designId,
      model_version: modelVersion,
      construct_validated: constructValidated,
      sequencing_result: sequencingResult || null,
      expression_result: expressionResult || null,
      functional_result: functionalResult || null,
      training_consent: trainingConsent,
      outcome_label: outcomeLabel,
      provenance: {
        reported_via: "web_manual_modal",
        tested_material: testedMaterial || null,
        consent_reviewed: consentReviewed,
        reported_at: reportedAt,
        ...(provenanceContext ?? {})
      },
      notes: notes.trim() || null,
      reported_at: reportedAt
    };

    try {
      setSubmitting(true);
      const saved = await submitOutcome(designId, report);
      setSubmittedReport(saved);
      onSubmitted?.(saved);
    } catch (error) {
      setSubmittedReport(null);
      setApiError(friendlyErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  if (submittedReport) {
    return (
      <ModalFrame onClose={onClose} titleId="outcome-submitted-title" descriptionId="outcome-submitted-description">
        <div className="space-y-4">
          <div>
            <p className="text-xs font-semibold uppercase text-action">Submitted</p>
            <h2 id="outcome-submitted-title" tabIndex={-1} className="mt-1 text-2xl font-semibold outline-none">Outcome submitted</h2>
            <p id="outcome-submitted-description" className="mt-2 text-sm leading-6 text-slate-600">Your report was saved for this design. Thank you for sharing what happened.</p>
          </div>
          <div className="border border-line bg-panel p-4 text-sm text-slate-700">
            <p><span className="font-semibold">Interpretation:</span> {interpretation || "Not specified"}</p>
            <p><span className="font-semibold">Sequencing:</span> {submittedReport.sequencing_result ?? "Not specified"}</p>
            <p><span className="font-semibold">Expression:</span> {submittedReport.expression_result ?? "Not specified"}</p>
            <p><span className="font-semibold">Function:</span> {submittedReport.functional_result ?? "Not specified"}</p>
            <p><span className="font-semibold">Consent:</span> {submittedReport.training_consent ? "Granted" : "Not granted"}</p>
            <p><span className="font-semibold">Reported:</span> {new Date(submittedReport.reported_at).toLocaleString()}</p>
          </div>
          <p className="text-sm text-slate-600">
            {submittedReport.training_consent
              ? "This report may be reviewed for use in model improvement according to policy."
              : "This report will not be used for model training."}
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={onClose} className="border border-action bg-action px-4 py-2 text-sm font-semibold text-white">
              Back to design
            </button>
          </div>
        </div>
      </ModalFrame>
    );
  }

  return (
    <ModalFrame onClose={onClose} titleId="outcome-report-title" descriptionId="outcome-report-description">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase text-action">Report outcome</p>
            <h2 id="outcome-report-title" tabIndex={-1} className="mt-1 text-2xl font-semibold outline-none">What happened in the lab?</h2>
            <p id="outcome-report-description" className="mt-2 text-sm leading-6 text-slate-600">Partial, failed, and uncertain results are useful.</p>
          </div>
          <span className={`border px-2 py-1 text-xs font-semibold ${validationIssues.length ? "border-warning/40 bg-amber-50 text-warning" : "border-action/40 bg-action/10 text-action"}`}>
            {validationIssues.length ? "Needs evidence" : "Ready to submit"}
          </span>
        </div>

        <section className="border border-line bg-panel p-4 text-sm text-slate-700">
          <p><span className="font-semibold">Design ID:</span> {designId ?? "Missing"}</p>
          <p><span className="font-semibold">Model version:</span> {modelVersion ?? "Missing"}</p>
          <p className="mt-2 text-xs text-slate-500">Report outcomes for the delivered design. If you changed the sequence before testing, mark that below.</p>
        </section>

        <SelectField label="What did you test?" value={testedMaterial} options={testedMaterialOptions} onChange={setTestedMaterial} />
        <p id="outcome-evidence-help" className="sr-only">Add at least one observed result (sequencing, expression, or functional) or an overall interpretation.</p>
        <SelectField id="outcome-sequencing" label="What sequence evidence do you have?" value={sequencingResult} options={sequencingOptions} onChange={setSequencingResult} ariaDescribedby="outcome-evidence-help" ariaInvalid={submitAttempted && evidenceMissing} />
        <SelectField id="outcome-expression" label="What happened in expression testing?" value={expressionResult} options={expressionOptions} onChange={setExpressionResult} ariaDescribedby="outcome-evidence-help" ariaInvalid={submitAttempted && evidenceMissing} />
        <SelectField id="outcome-functional" label="What happened in functional testing?" value={functionalResult} options={functionalOptions} onChange={setFunctionalResult} ariaDescribedby="outcome-evidence-help" ariaInvalid={submitAttempted && evidenceMissing} />
        <SelectField id="outcome-interpretation" label="Based on the evidence above, what is your interpretation?" value={interpretation} options={interpretationOptions} onChange={setInterpretation} ariaDescribedby="outcome-evidence-help" ariaInvalid={submitAttempted && evidenceMissing} />

        <label className="block text-sm font-medium text-slate-800">
          Notes
          <textarea
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={4}
            className="mt-2 w-full resize-none border border-line px-3 py-2 text-sm outline-none focus:border-action focus:ring-2 focus:ring-action/20"
            placeholder="Protocol deviations, vendor issues, changed sequence, weak controls, or clone-specific details..."
          />
        </label>

        <section className="border border-line p-4" aria-describedby="outcome-consent-help">
          <label className="flex gap-3 text-sm text-slate-800">
            <input
              type="checkbox"
              checked={trainingConsent}
              onChange={(event) => {
                setTrainingConsent(event.target.checked);
                setConsentReviewed(true);
              }}
              aria-invalid={submitAttempted && !consentReviewed || undefined}
              aria-describedby="outcome-consent-help"
              className="mt-1 h-4 w-4"
            />
            <span>I consent to this outcome report and non-sensitive linked design metadata being used to improve future design models.</span>
          </label>
          <button type="button" onClick={() => setConsentReviewed(true)} className="mt-3 text-xs font-semibold text-action hover:text-action/80 focus:outline-none focus:ring-2 focus:ring-action/20">
            {consentReviewed ? "Consent choice reviewed" : "Submit without training consent"}
          </button>
          <p id="outcome-consent-help" className="mt-2 text-xs leading-5 text-slate-500">Submitting an outcome does not require this consent. If unchecked, your report can still be saved, but it must not be used for model training or preference optimization.</p>
        </section>

        <section className="border border-line bg-panel p-4 text-sm">
          <h3 className="font-semibold text-slate-800">Evidence category</h3>
          <p className="mt-1 text-slate-600">{labelText(outcomeLabel, trainingConsent)}</p>
        </section>

        {validationIssues.length ? <MessageList id="outcome-validation-errors" tone="error" items={validationIssues} ariaLive={submitAttempted ? "polite" : undefined} /> : null}
        {warnings.length ? <MessageList tone="warning" items={warnings} /> : null}
        {apiError ? <p className="border border-red-200 bg-red-50 p-3 text-sm text-red-700">{apiError}</p> : null}

        <div className="sticky bottom-0 -mx-5 flex flex-wrap justify-end gap-2 border-t border-line bg-white px-5 py-4">
          <button type="button" onClick={onClose} disabled={submitting} className="border border-line bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-action hover:text-action focus:border-action focus:outline-none focus:ring-2 focus:ring-action/20 disabled:cursor-not-allowed disabled:border-line disabled:text-slate-400 disabled:hover:text-slate-400">
            Close
          </button>
          <button type="submit" disabled={submitting || Boolean(validationIssues.length)} className="border border-action bg-action px-4 py-2 text-sm font-semibold text-white hover:bg-action/90 focus:border-action focus:outline-none focus:ring-2 focus:ring-action/20 disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-300 disabled:hover:bg-slate-300">
            {submitting ? "Submitting..." : "Submit outcome"}
          </button>
        </div>
      </form>
    </ModalFrame>
  );
}

function ModalFrame({ children, onClose, titleId, descriptionId }: { children: React.ReactNode; onClose: () => void; titleId: string; descriptionId: string }) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    openerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const heading = document.getElementById(titleId);
    if (heading instanceof HTMLElement) {
      heading.focus();
    } else {
      dialogRef.current?.focus();
    }
    return () => {
      openerRef.current?.focus();
    };
  }, [titleId]);

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== "Tab") {
      return;
    }

    const dialog = dialogRef.current;
    if (!dialog) {
      return;
    }
    const focusable = Array.from(
      dialog.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((element) => !element.hasAttribute("disabled") && element.getAttribute("aria-hidden") !== "true");
    if (!focusable.length) {
      event.preventDefault();
      dialog.focus();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div
      ref={dialogRef}
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/50 px-4 py-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      tabIndex={-1}
      onKeyDown={handleKeyDown}
    >
      <div className="mx-auto max-w-3xl border border-line bg-white p-5 shadow-subtle">
        <div className="mb-4 flex justify-end">
          <button type="button" onClick={onClose} className="text-sm font-semibold text-slate-500 hover:text-slate-800 focus:outline-none focus:ring-2 focus:ring-action/20">
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function SelectField({ label, value, options, onChange, id, ariaDescribedby, ariaInvalid }: { label: string; value: string; options: string[]; onChange: (value: string) => void; id?: string; ariaDescribedby?: string; ariaInvalid?: boolean }) {
  return (
    <label className="block text-sm font-medium text-slate-800" htmlFor={id}>
      {label}
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)} aria-describedby={ariaDescribedby} aria-invalid={ariaInvalid || undefined} className="mt-2 w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-action focus:ring-2 focus:ring-action/20">
        <option value="">Select closest status</option>
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    </label>
  );
}

function MessageList({ tone, items, id, ariaLive }: { tone: "error" | "warning"; items: string[]; id?: string; ariaLive?: "polite" }) {
  const className = tone === "error" ? "border-red-200 bg-red-50 text-red-700" : "border-warning/40 bg-amber-50 text-warning";
  return (
    <ul id={id} aria-live={ariaLive} className={`space-y-1 border p-3 text-sm ${className}`}>
      {items.map((item) => <li key={item}>{item}</li>)}
    </ul>
  );
}

function labelText(label: OutcomeLabel, trainingConsent: boolean): string {
  if (!trainingConsent) {
    return "Not eligible for training because consent was not granted.";
  }
  if (label === "positive") {
    return "Likely positive evidence";
  }
  if (label === "negative") {
    return "Likely negative evidence";
  }
  return "Ambiguous evidence";
}

function interpretationFromReport(report: OutcomeReport | undefined): string {
  if (!report) {
    return "";
  }
  if (report.construct_validated === true) {
    return "Accepted for intended use";
  }
  if (report.construct_validated === false) {
    return "Did not validate";
  }
  return report.outcome_label === "ambiguous" ? "Attempted, but inconclusive" : "";
}

function readStringProvenance(report: OutcomeReport | undefined, key: string): string {
  const value = report?.provenance?.[key];
  return typeof value === "string" ? value : "";
}

function friendlyErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const fieldText = error.fieldErrors.length ? ` ${error.fieldErrors.map((field) => `${field.field}: ${field.message}`).join(" ")}` : "";
    return `${error.message}${fieldText}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Outcome submission failed.";
}
