# Loading And Empty States Audit

Scope: `apps/web` frontend loading and empty states on branch `phase4-visual-polish`.

Out of scope: root docs, research findings, root README, backend, generation code, and other worktrees.

## Priority Findings

### P1 - Right rail can show stale completed-design state while a new job is running

- References: `apps/web/app/page.tsx:68-71`, `apps/web/app/page.tsx:343-345`, `apps/web/app/page.tsx:400-405`, `apps/web/app/page.tsx:514-535`
- Current behavior: `latestResult`, `annotatedSequence`, and `designId` continue to point at the most recent completed result while `state` is `submitting` or `polling`. The active job progress card appears only in the chat column, while the plasmid map, export actions, and lab outcome panel remain tied to the previous design.
- User impact: during refinement or a second design, users can read the right rail as the in-progress result and can export/report an older design by mistake.
- Minimal fix: pass `isBusy` and `activeJobId` into the right-rail components or wrapper. Show a compact "New design running" notice above the map, label the map/export as "Showing last completed design", and disable exports/outcome reporting while a new job is active unless explicitly intended.

### P1 - Zero retrieved templates/corpus no-match state is silently omitted

- References: `apps/web/app/page.tsx:323-335`, `apps/web/app/page.tsx:654-664`
- Current behavior: retrieved templates render only when `retrieved_templates.length` is truthy. If retrieval returns an empty array or no matches, the result card has no retrieval section. The fallback result summary still says to review returned templates and validation details.
- User impact: users cannot tell whether retrieval was skipped, still pending, failed upstream, or completed with no matches.
- Minimal fix: when a result is present, render a small retrieval status block. Use "No matching templates were retrieved" for an empty array, and "Template retrieval was not returned for this job" when the field is absent.

### P1 - Validation report absent after completion has no explicit empty/error state

- References: `apps/web/app/page.tsx:323-325`, `apps/web/app/page.tsx:538-566`, `apps/web/app/page.tsx:654-664`
- Current behavior: `ValidationReportPanel` renders only when `message.result.validation_report` exists. Empty checks inside an existing report are handled, but a missing report after completion is invisible.
- User impact: users cannot distinguish "validation passed elsewhere", "validation unavailable", "validation not started", and "validation failed to return".
- Minimal fix: render a validation placeholder for completed result cards when `validation_report` is `null` or missing. Copy should be explicit, for example "Validation report was not returned for this job." Keep `JobProgressCard` as the in-progress state for running validation.

### P1 - Pending outcome prompt loading and error states collapse into "no prompt"

- References: `apps/web/app/page.tsx:61`, `apps/web/app/page.tsx:85-99`, `apps/web/app/page.tsx:158`, `apps/web/app/page.tsx:293-297`, `apps/web/app/page.tsx:470-486`
- Current behavior: pending prompts are initialized to `[]`; fetch failure also sets `[]`; an empty successful response also leaves `[]`. Only a visible prompt is rendered.
- User impact: users get no signal when outcome prompts are loading, unavailable, or failed due to API/network issues.
- Minimal fix: add a small prompt fetch status such as `idle | loading | ready | error`. Do not show a toast for the normal empty state, but expose a subtle inline/rail message or retry affordance on error.

### P2 - Export state can remain stale across designs and errors are global

- References: `apps/web/app/page.tsx:55-56`, `apps/web/app/page.tsx:168`, `apps/web/app/page.tsx:218-239`, `apps/web/app/page.tsx:402-403`, `apps/web/components/export-actions.tsx:11-29`, `apps/web/components/export-actions.tsx:47-56`
- Current behavior: `exportError` is cleared on submit, but `exportStatus` is not reset when a new design job starts or when `designId` changes. A prior "Download started" or "GenBank ready" status can remain visible for the next design. Export errors are a single section-level message, not tied to GenBank vs FASTA.
- User impact: users can misread an old export success/error as applying to the current design.
- Minimal fix: reset both format statuses to `idle` when a new job starts and when a different `designId` becomes current. Track error per format or include the failed format in the error message.

### P2 - Plasmid map has a basic empty/loading state but no render failure fallback

- References: `apps/web/components/plasmid-map-view.tsx:7-10`, `apps/web/components/plasmid-map-view.tsx:16-25`, `apps/web/components/plasmid-map-view.tsx:57-67`, `apps/web/components/plasmid-map-view.tsx:75-78`
- Current behavior: pre-design empty state is clear and dynamic import loading shows "Loading map...". If `SeqViz` fails during client rendering, there is no local error fallback. During an active design job the map does not communicate that a new map is pending.
- User impact: users can see a blank or broken map area without recovery guidance, especially if the sequence viewer bundle or render path fails.
- Minimal fix: add a lightweight error boundary around `SeqViz` with "Map could not render" and keep the feature legend visible. Pair this with the right-rail active-job notice from P1.

### P2 - Outcome list empty state exists, but refresh/loading/error states are absent

- References: `apps/web/app/page.tsx:60`, `apps/web/app/page.tsx:88`, `apps/web/app/page.tsx:132-156`, `apps/web/app/page.tsx:422-456`
- Current behavior: `MyOutcomesPanel` has a clear empty state for no locally known reports. The background refresh of known outcomes has no loading state, and refresh failures are swallowed.
- User impact: users cannot tell whether locally cached outcomes are current or whether backend refresh failed.
- Minimal fix: keep the existing empty state. Add a small "Refreshing..." text while known outcomes are being refreshed and a non-blocking "Could not refresh outcomes" message if all refreshes fail.

### P3 - First-run state is functional but uneven against the right rail

- References: `apps/web/app/page.tsx:42-49`, `apps/web/app/page.tsx:355-368`, `apps/web/components/plasmid-map-view.tsx:16-25`, `apps/web/components/export-actions.tsx:17-24`, `apps/web/app/page.tsx:488-510`
- Current behavior: before a session exists, the chat welcome and example prompt chips are helpful. The right rail separately shows disabled map/export/outcome panels.
- User impact: no major blocker, but first-run guidance is fragmented and the disabled controls do not all explain next steps equally.
- Minimal fix: keep the welcome/chips. Consider a single compact first-run helper in the right rail, or align disabled panel copy around one action: "Submit a design to enable this."

## Covered States

- Before any session exists: mostly handled; minor polish recommended.
- Design job running: handled in chat only; right rail needs stale-state protection.
- Plasmid map before rendering: handled; while rendering is basic; render failure missing.
- Zero retrieved templates/corpus no matches: missing.
- Validation report absent/in progress: in-progress is implied by job card; absent after completion is missing.
- Outcome list empty: handled; refresh loading/error missing.
- Export disabled/loading/errors: basic states exist; reset and per-format specificity missing.
- Pending prompts absent/error: absent is intentionally silent; loading/error are missing.

## Recommended Minimal Fix Order

1. Add active-job right-rail stale-state labels and disable/export guard during new jobs.
2. Add explicit completed-result empty states for retrieved templates and missing validation reports.
3. Reset export status on new jobs/design changes and make export errors format-specific.
4. Track pending prompt fetch status and surface only error/retry, not normal empty.
5. Add `SeqViz` render fallback and optional outcome refresh status.
