# Frontend Accessibility Audit

Scope: `apps/web` manual WCAG 2.1 AA audit for the design workspace, outcome submission flow, plasmid visualization, dynamic chat updates, and export controls.

Method: manual source review only. No axe-style accessibility tooling is currently present in `apps/web/package.json`, and no dependencies were installed.

## Executive Summary

The core design and outcome submission flows are keyboard-reachable because native form controls and buttons are used throughout `apps/web/app/page.tsx`, `apps/web/components/outcome-report-modal.tsx`, and `apps/web/components/export-actions.tsx`. The highest-risk gaps are modal focus management, under-announced dynamic status updates, focus visibility/contrast consistency, and insufficient non-visual accommodations around the `seqviz` plasmid map.

## Prioritized Findings

### P1: Outcome Modal Does Not Manage Focus Or Escape Semantics

Reference: `apps/web/components/outcome-report-modal.tsx:312-324`

WCAG: 2.1.1 Keyboard, 2.4.3 Focus Order, 2.4.7 Focus Visible, 4.1.2 Name, Role, Value

Impact: When the modal opens, focus is not moved into the dialog, focus is not trapped inside it, `Escape` does not close it, and focus is not restored to the triggering button on close. Keyboard and screen reader users can remain positioned behind the modal or tab into background controls while the dialog is visually active.

Recommended minimal fix: In `ModalFrame`, add a labeled dialog heading via `aria-labelledby`, focus the first meaningful control or heading on mount, trap `Tab` within the modal while open, close on `Escape`, and restore focus to the opener when `OutcomeReportModal` closes. Keep the existing modal layout; this does not require a navigation restructure.

### P1: Modal Dialog Has No Programmatic Name

Reference: `apps/web/components/outcome-report-modal.tsx:204-240`, `apps/web/components/outcome-report-modal.tsx:312-314`

WCAG: 4.1.2 Name, Role, Value

Impact: The dialog uses `role="dialog"` and `aria-modal="true"` but is not associated with either `What happened in the lab?` or `Outcome submitted`. Screen reader users may hear a generic dialog without useful context.

Recommended minimal fix: Pass a title ID into `ModalFrame` and set `aria-labelledby` to the active `h2`. Optionally add `aria-describedby` pointing to the short explanatory paragraph.

### P1: Dynamic Chat And Job Updates Are Not Reliably Announced

Reference: `apps/web/app/page.tsx:305-346`, `apps/web/app/page.tsx:514-535`

WCAG: 4.1.3 Status Messages, 2.2.2 Pause, Stop, Hide

Impact: The message list has `aria-live="polite"`, but whole message history is inside the live region, which can produce noisy or inconsistent announcements when messages are appended. The busy progress card updates elapsed seconds every second but is mostly visual and not exposed as a status. Users relying on assistive tech may miss design completion, clarification requests, errors, or export readiness.

Recommended minimal fix: Add a dedicated visually hidden live region that announces only state transitions such as `Starting design job`, `Design complete`, `Clarification needed`, and `Design failed`. Mark the elapsed timer itself `aria-hidden` or avoid announcing every second. Give `JobProgressCard` `role="status"` with stable text that does not churn.

### P1: Plasmid Visualization Needs Explicit Non-Visual Accommodation

Reference: `apps/web/components/plasmid-map-view.tsx:57-70`, `apps/web/components/plasmid-map-view.tsx:75-99`

WCAG: 1.1.1 Non-text Content, 1.3.1 Info and Relationships, 1.4.1 Use of Color, 2.1.1 Keyboard

Impact: `seqviz` is an interactive/visual plasmid map, and its SVG/canvas internals should not be assumed screen-reader-friendly. The existing feature legend provides useful text, but the map is not explicitly described as decorative/visual nor paired with a concise textual summary of topology, length, annotation completeness, and feature count.

Recommended minimal fix: Treat `seqviz` as a visual aid and provide a first-class text alternative nearby: sequence length, topology, annotation completeness, number of features, and a table/list of features with name, type, coordinates, strand, and confidence. Add a short note such as `Interactive plasmid map is visual; use the feature list below for the accessible annotation summary.` If possible, wrap the `SeqViz` container with `aria-hidden="true"` or an `aria-label` that directs users to the feature list, depending on whether any internal controls must remain keyboard-accessible.

Specific accommodation: Do not try to make every graphical segment of the plasmid map screen-reader-friendly. Preserve `seqviz` for sighted users, then expose the annotated feature data as semantic HTML with stable text and exportable formats. The current `FeatureLegend` is a good base but should avoid truncating the accessible text and should expose it as a list or table with a heading.

### P2: Focus Indicators Are Mostly Color-Only And Sometimes Browser-Default

Reference: `apps/web/app/page.tsx:373-390`, `apps/web/components/outcome-report-modal.tsx:260-303`, `apps/web/components/export-actions.tsx:49-56`, `apps/web/app/globals.css:27-31`

WCAG: 2.4.7 Focus Visible, 1.4.11 Non-text Contrast

Impact: Textareas and selects remove outline and use only `focus:border-action`. Buttons often rely on default focus styling or no explicit focus styling. Keyboard users may have difficulty locating focus, especially on low-contrast borders and dense panels.

Recommended minimal fix: Add a shared focus-visible treatment to interactive controls, for example `focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action`, while retaining existing color styling.

### P2: Status And Validation Meaning Relies Partly On Color

Reference: `apps/web/app/page.tsx:570-580`, `apps/web/app/page.tsx:460-467`, `apps/web/components/plasmid-map-view.tsx:46-54`, `apps/web/components/outcome-report-modal.tsx:290-297`

WCAG: 1.4.1 Use of Color, 1.3.1 Info and Relationships

Impact: Status badges include visible text, which is good, but warning/error panels and color-coded feature swatches depend on color to quickly convey meaning. The feature legend swatch is `aria-hidden`, so non-visual users receive type/name/coordinates, but sighted low-vision or color-blind users may have difficulty differentiating feature categories by color alone.

Recommended minimal fix: Keep text labels adjacent to all status colors. For feature legend entries, ensure type text remains visible and not truncated. Consider adding simple shape/pattern-independent labels or grouping features by type in text.

### P2: Export Status Messages Are Not Announced

Reference: `apps/web/components/export-actions.tsx:26-29`, `apps/web/app/page.tsx:218-240`

WCAG: 4.1.3 Status Messages

Impact: Export buttons change label from `GenBank` to `Preparing...` to `GenBank ready`, and a `Download started.` message appears visually. These updates are not in a status/live region, so screen reader users may not know whether an export is preparing, succeeded, or failed.

Recommended minimal fix: Wrap export error and success text in `role="status"` or `aria-live="polite"`. Consider `aria-busy` on the export section while a format is loading.

### P2: Form Validation Messages Are Not Programmatically Associated With Fields

Reference: `apps/web/components/outcome-report-modal.tsx:123-138`, `apps/web/components/outcome-report-modal.tsx:254-297`

WCAG: 3.3.1 Error Identification, 3.3.2 Labels or Instructions, 4.1.3 Status Messages

Impact: Outcome validation issues are collected in a general list. The fields have labels, but required/review states are not expressed with `aria-required`, `aria-invalid`, or `aria-describedby`. Users may need to infer which field needs action.

Recommended minimal fix: Add IDs to validation and helper text, then connect relevant fields with `aria-describedby`. Use `role="alert"` or `aria-live="polite"` for validation changes after submit attempts. Mark fields invalid only when a user attempts submission or leaves a required section incomplete.

### P2: Pending Outcome Toast May Not Be Announced When It Appears

Reference: `apps/web/app/page.tsx:293-297`, `apps/web/app/page.tsx:470-485`

WCAG: 4.1.3 Status Messages, 2.4.3 Focus Order

Impact: The fixed pending outcome prompt appears visually after async loading but is only an `aside` with `aria-label`. Screen reader users may not be notified that a new actionable prompt exists.

Recommended minimal fix: Add `role="status"` or `aria-live="polite"` to the toast container, or announce `Outcome follow-up available for design ...` through the app-level live region. Do not automatically move focus to the toast unless the flow is intentionally interruptive.

### P3: Landmark And Region Naming Can Be Improved

Reference: `apps/web/app/page.tsx:298-407`, `apps/web/components/plasmid-map-view.tsx:38-71`, `apps/web/components/export-actions.tsx:13-30`

WCAG: 1.3.1 Info and Relationships, 2.4.1 Bypass Blocks, 2.4.6 Headings and Labels

Impact: The page has a `main`, several labeled sections, and headings, but the left design conversation section and right workspace aside are not explicitly named. Repeated panels can be harder to navigate by screen reader landmarks/regions.

Recommended minimal fix: Add `aria-labelledby` to major sections using existing headings, such as the design workspace conversation, plasmid map, export, outcome reporting, and my outcomes panels.

### P3: Button Labels Are Understandable But Could Be More Contextual

Reference: `apps/web/app/page.tsx:356-365`, `apps/web/app/page.tsx:386-392`, `apps/web/components/export-actions.tsx:49-56`

WCAG: 2.4.6 Headings and Labels, 2.5.3 Label in Name

Impact: Example prompt buttons use long visible text and are keyboard-accessible. Export buttons say `GenBank` and `FASTA`, which is acceptable in the export panel but less descriptive when navigating by button list.

Recommended minimal fix: Add `aria-label="Download GenBank export"` and `aria-label="Download FASTA export"` or change visible labels to `Download GenBank` and `Download FASTA`.

## Keyboard Flow Review

Design flow: Users can tab to example prompts, the `Experimental goal` textarea, submit button, message links, plasmid map anchor, export buttons, and outcome controls. Main gap is focus visibility and dynamic status announcement, not basic keyboard reachability.

Outcome submission flow: Native selects, textarea, checkbox, and buttons are keyboard-operable. Main gap is modal focus containment/restoration and associating validation guidance with fields.

Export flow: Export buttons are keyboard-operable and disabled until `designId` exists. Main gap is announcing loading/success/error state.

## Contrast Risks

The configured palette in `apps/web/tailwind.config.ts` uses dark text on light backgrounds for most content. Likely risks are small text using `text-slate-500` on `bg-panel`/white, disabled text on disabled gray buttons, thin `border-line` controls, and warning/action variants at small sizes. These should be checked with a contrast calculator during visual QA, especially `text-warning` on amber backgrounds and `text-action` on action-tint backgrounds.

## Seqviz And Plasmid Map Accommodations

Use `seqviz` as the visual map for sighted users and keyboard users who can operate it, but do not make full graphical parity the accessibility goal. The accessible equivalent should be a semantic annotation summary derived from the same `annotatedSequence` object.

Minimum accommodation set:

- Add a textual map summary: vector/profile name, topology, length, annotation completeness, and feature count.
- Promote `FeatureLegend` to an accessible list or table with a heading and complete, untruncated text.
- Include columns or labels for feature name, type, start/end coordinates, strand, and confidence.
- Avoid relying on swatch color as the only way to identify feature classes.
- Provide export controls for GenBank/FASTA as the detailed machine-readable alternative.
- If `SeqViz` internals are noisy to screen readers, hide the graphical container from assistive tech and point users to the feature summary.

## Questions For The Human

- Should the app add a global skip link and explicit two-region layout navigation for the conversation and right-side design panels? This is a small layout/navigation restructure and should be confirmed before implementation.
- Should the plasmid map receive a separate accessible detail route or expandable table for long annotations, rather than expanding the current side panel? This may affect layout and information architecture.
- Should outcome reporting remain a modal, or should it become a dedicated route/page for long-form accessibility and mobile ergonomics? A dedicated route could simplify focus management but changes navigation behavior.

## Positive Observations

- Most interactive controls are semantic `button`, `textarea`, `select`, and `input` elements.
- The main input has a real label via `htmlFor="goal"`, even though it is visually hidden.
- Outcome form select and notes controls are visibly labeled.
- Export buttons correctly use `disabled` when no design exists or an export is loading.
- Status badges include text labels rather than color alone.
- The feature legend already exposes core annotation text outside the graphical map.
