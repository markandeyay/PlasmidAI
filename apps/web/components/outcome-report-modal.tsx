"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiError, submitOutcome } from "@/lib/api";
import type { OutcomeLabel, OutcomeReport } from "@/lib/types";

type OutcomeReportModalProps = {
  open: boolean;
  designId: string | null;
  modelVersion: string | null;
  onClose: () => void;
  onSubmitted?: (report: OutcomeReport) => void;
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

export function OutcomeReportModal({ open, designId, modelVersion, onClose, onSubmitted }: OutcomeReportModalProps) {
  const [testedMaterial, setTestedMaterial] = useState("");
  const [sequencingResult, setSequencingResult] = useState("");
  const [expressionResult, setExpressionResult] = useState("");
  const [functionalResult, setFunctionalResult] = useState("");
  const [interpretation, setInterpretation] = useState("");
  const [notes, setNotes] = useState("");
  const [trainingConsent, setTrainingConsent] = useState(false);
  const [consentReviewed, setConsentReviewed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [submittedReport, setSubmittedReport] = useState<OutcomeReport | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    setApiError(null);
  }, [open]);

  useEffect(() => {
    setSubmittedReport(null);
  }, [designId]);

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

  if (!open) {
    return null;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
        reported_at: reportedAt
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
      <ModalFrame onClose={onClose}>
        <div className="space-y-4">
          <div>
            <p className="text-xs font-semibold uppercase text-action">Submitted</p>
            <h2 className="mt-1 text-2xl font-semibold">Outcome submitted</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Your report was saved for this design. Thank you for sharing what happened.</p>
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
    <ModalFrame onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase text-action">Report outcome</p>
            <h2 className="mt-1 text-2xl font-semibold">What happened in the lab?</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Partial, failed, and uncertain results are useful.</p>
          </div>
          <span className="border border-line bg-panel px-2 py-1 text-xs font-semibold text-slate-600">
            {validationIssues.length ? "Needs evidence" : "Ready to submit"}
          </span>
        </div>

        <section className="border border-line bg-panel p-4 text-sm text-slate-700">
          <p><span className="font-semibold">Design ID:</span> {designId ?? "Missing"}</p>
          <p><span className="font-semibold">Model version:</span> {modelVersion ?? "Missing"}</p>
          <p className="mt-2 text-xs text-slate-500">Report outcomes for the delivered design. If you changed the sequence before testing, mark that below.</p>
        </section>

        <SelectField label="What did you test?" value={testedMaterial} options={testedMaterialOptions} onChange={setTestedMaterial} />
        <SelectField label="What sequence evidence do you have?" value={sequencingResult} options={sequencingOptions} onChange={setSequencingResult} />
        <SelectField label="What happened in expression testing?" value={expressionResult} options={expressionOptions} onChange={setExpressionResult} />
        <SelectField label="What happened in functional testing?" value={functionalResult} options={functionalOptions} onChange={setFunctionalResult} />
        <SelectField label="Based on the evidence above, what is your interpretation?" value={interpretation} options={interpretationOptions} onChange={setInterpretation} />

        <label className="block text-sm font-medium text-slate-800">
          Notes
          <textarea
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={4}
            className="mt-2 w-full resize-none border border-line px-3 py-2 text-sm outline-none focus:border-action"
            placeholder="Protocol deviations, vendor issues, changed sequence, weak controls, or clone-specific details..."
          />
        </label>

        <section className="border border-line p-4">
          <label className="flex gap-3 text-sm text-slate-800">
            <input
              type="checkbox"
              checked={trainingConsent}
              onChange={(event) => {
                setTrainingConsent(event.target.checked);
                setConsentReviewed(true);
              }}
              className="mt-1 h-4 w-4"
            />
            <span>I consent to this outcome report and non-sensitive linked design metadata being used to improve future design models.</span>
          </label>
          <button type="button" onClick={() => setConsentReviewed(true)} className="mt-3 text-xs font-semibold text-action">
            {consentReviewed ? "Consent choice reviewed" : "Submit without training consent"}
          </button>
          <p className="mt-2 text-xs leading-5 text-slate-500">Submitting an outcome does not require this consent. If unchecked, your report can still be saved, but it must not be used for model training or preference optimization.</p>
        </section>

        <section className="border border-line bg-panel p-4 text-sm">
          <h3 className="font-semibold text-slate-800">Evidence category</h3>
          <p className="mt-1 text-slate-600">{labelText(outcomeLabel, trainingConsent)}</p>
        </section>

        {validationIssues.length ? <MessageList tone="error" items={validationIssues} /> : null}
        {warnings.length ? <MessageList tone="warning" items={warnings} /> : null}
        {apiError ? <p className="border border-red-200 bg-red-50 p-3 text-sm text-red-700">{apiError}</p> : null}

        <div className="sticky bottom-0 -mx-5 flex flex-wrap justify-end gap-2 border-t border-line bg-white px-5 py-4">
          <button type="button" onClick={onClose} disabled={submitting} className="border border-line px-4 py-2 text-sm font-semibold text-slate-700 disabled:text-slate-400">
            Close
          </button>
          <button type="submit" disabled={submitting || Boolean(validationIssues.length)} className="border border-action bg-action px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-300">
            {submitting ? "Submitting..." : "Submit outcome"}
          </button>
        </div>
      </form>
    </ModalFrame>
  );
}

function ModalFrame({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/50 px-4 py-6" role="dialog" aria-modal="true">
      <div className="mx-auto max-w-3xl border border-line bg-white p-5 shadow-subtle">
        <div className="mb-4 flex justify-end">
          <button type="button" onClick={onClose} className="text-sm font-semibold text-slate-500 hover:text-slate-800">
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-slate-800">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-action">
        <option value="">Select closest status</option>
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    </label>
  );
}

function MessageList({ tone, items }: { tone: "error" | "warning"; items: string[] }) {
  const className = tone === "error" ? "border-red-200 bg-red-50 text-red-700" : "border-warning/40 bg-amber-50 text-warning";
  return (
    <ul className={`space-y-1 border p-3 text-sm ${className}`}>
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
