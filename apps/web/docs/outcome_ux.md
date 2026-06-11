# Outcome Submission UX Spec

## Purpose

This spec defines the frontend experience for a researcher reporting wet-lab outcomes weeks after receiving a plasmid design. It is a UX contract only. It does not define backend storage, model registry behavior, training jobs, or Phase 2 fine-tuning work.

The experience must collect enough structured evidence to support the current `OutcomeReport` schema while remaining compatible with the richer Phase 5 outcome-capture model:

- `design_id` and `model_version` are shown as immutable context, not user-entered fields.
- `construct_validated` maps to the user's high-level conclusion, but must not be treated as sufficient evidence by itself.
- `sequencing_result`, `expression_result`, and `functional_result` collect plain-language status and optional details.
- `training_consent` is an explicit opt-in checkbox.
- `outcome_label` is derived or previewed as positive, negative, or ambiguous based on reported evidence and consent.
- `provenance`, `notes`, and `reported_at` capture source, collection channel, user edits, and timing.

## User Mental Model

The researcher is not returning to "rate the AI." They are closing the loop on a design they tried in the lab.

The interface should frame the task as:

> Tell us what happened when this design was built or tested. Partial, failed, and inconclusive results are useful.

Core mental model principles:

- Outcome reporting is about the experiment, not about pleasing the system.
- The researcher can report uncertainty without being forced into success or failure.
- Evidence types are separable: sequence verification, digest screening, expression, function, and notes can disagree.
- Consent for training is separate from submitting the outcome.
- The design snapshot is fixed. If the researcher edited the design before testing, they should say so instead of silently reporting against the original design.

## Bias Risks

The phrase "Did your construct validate?" is fast and familiar, but it can bias noisy self-reporting because it sounds like there is a correct answer and implies validation is binary.

Risks to mitigate:

- Social desirability bias: users may over-report success because the generated design is presented as expected to work.
- Confirmation bias: users may choose "validated" after one supportive assay even when sequencing or controls are incomplete.
- Ambiguity bias: users may map "not built," "not tested," and "failed" into the same negative bucket.
- Attribution bias: users may blame the design for protocol deviations, vendor problems, low transformation efficiency, or missing controls.
- Recall bias: users reporting weeks later may compress multiple clones, edits, and assays into one simplified story.
- Training contamination risk: a single self-reported yes/no answer can create a false positive or false negative training signal.

UX mitigations:

- Ask for build/test status before asking for final interpretation.
- Use neutral labels: "What happened?" rather than "Was the design successful?"
- Keep "I don't know yet" and "not tested" as first-class answers.
- Prompt for evidence status separately from interpretation.
- Show that failed and inconclusive reports are useful.
- Do not display a celebratory success state until after submission; during entry, avoid steering copy like "Great, it worked!"
- Derive the training label silently or with neutral wording such as "Likely evidence category," not "model reward."

## Open UX Questions To Log Later

These questions specifically concern asking "did your construct validate" without biasing noisy researcher self-reporting and may need to be copied to `PROGRESS.md` later.

1. Should the first required question be "Was this design built or tested?" instead of "Did your construct validate?"
2. Should the UI avoid the word "validated" entirely in the first screen and reserve it for structured status values?
3. Should "validated" require sequencing evidence in the form before it can be selected, or should users be allowed to self-report it with warnings?
4. Should the form ask "What evidence do you have?" before "What is your overall interpretation?" to reduce anchoring?
5. Should outcome labels be hidden from the user to avoid users optimizing their answer toward positive or negative training impact?
6. Should the consent checkbox explain that uncertain and failed results can be useful for training, or would that increase over-reporting of design-attributed failures?
7. Should the review/edit screen ask users to confirm whether they tested the delivered design exactly, a modified design, or multiple clones?
8. Should a later reviewer adjudicate `construct_validated=true` before it can become a positive training signal?

## Entry Points

### Notification Entry

Timing: send after a configurable delay from design delivery, with a second reminder only if no outcome exists.

Notification card copy:

- Title: "Report what happened with your plasmid design"
- Body: "If you built, sequenced, expressed, or tested this design, share the outcome. Failed and inconclusive results are useful too."
- Primary action: "Report outcome"
- Secondary action: "Not built yet"
- Tertiary action: "Remind me later"

The notification should include enough context for recognition:

- Design name or generated design ID.
- Date delivered.
- Organism/vector summary if available.
- Small static plasmid/sequence summary, not an editable sequence view.

Click behavior:

- "Report outcome" opens the outcome form with the design context pinned at top.
- "Not built yet" opens a one-question lightweight modal and can submit `construct_validated=null`, evidence fields empty, note optional, and a provenance status indicating not built if the API later supports it. If current schema validation requires one observation, submit a notes-only draft is not sufficient; use the full form path until backend support exists.
- "Remind me later" dismisses the notification without creating an outcome.

### Design Detail Entry

On a completed design page, show a persistent panel:

- If no outcome exists: "Have lab results for this design?" with "Report outcome."
- If an outcome exists: "Outcome reported" with status, reported date, consent state, and "Review or edit."
- If outcome is ambiguous or missing evidence: "Outcome needs review" with "Add evidence."

## Prompt-To-Submission-To-Confirmation Journey

1. Prompt: researcher sees a reminder or returns to the design detail page.
2. Context check: form opens with immutable design context and asks whether this exact delivered design was tested.
3. Build/test status: researcher says whether it was built, not built, partially tested, modified before testing, or tested across multiple clones.
4. Evidence capture: researcher answers the easiest accurate questions about sequencing, expression, function, and optional digest evidence.
5. Overall interpretation: researcher selects the closest interpretation after evidence fields are visible.
6. Consent: researcher chooses whether this outcome may be used for training.
7. Review: a compact summary shows the design, evidence, interpretation, notes, and consent.
8. Submit: validation runs inline; blocking issues are shown at the relevant section.
9. Confirmation: the user sees a neutral success state with the outcome status and next actions.
10. Review/edit path: user can reopen the submitted report, edit fields, update consent, and resubmit.

## Form Mockup Description

Use a single responsive page or modal-sheet route. Desktop can use a two-column layout; mobile should use one column with sticky bottom actions.

Header area:

- Page title: "Report outcome"
- Subtitle: "Share what happened after this design left the app. Partial, failed, and uncertain results are useful."
- Right-side status pill: "Draft," "Ready to submit," "Submitted," or "Needs evidence."

Pinned design context card:

- Design ID, creation date, model version, session/job references if available.
- Short design summary: vector profile, organism, relevant genes/tags, validation report overall status.
- "View original design" expandable link.
- Warning copy: "Report outcomes for the delivered design. If you changed the sequence before testing, mark that below."

Section 1, Tested material:

- Question: "What did you test?"
- Options: "Delivered design exactly," "A modified version," "Multiple clones from this design," "Not built or not tested," "I'm not sure."
- If modified: show text field "What changed?" and state that the result may be reviewed before training use.
- If multiple clones: show optional number of clones screened.

Section 2, Sequencing or sequence verification:

- Question: "What sequence evidence do you have?"
- Options: "Matches expected regions," "Mismatch found," "Partial match," "Mixed or low quality," "Sequencing not performed," "Not applicable," "Inconclusive."
- Optional fields: method, covered regions, percent identity, coverage fraction, variant summary, notes, upload/report pointer if supported.
- Helper text: "Choose the closest evidence status. Do not paste sensitive raw sequence unless the product policy explicitly allows it."

Section 3, Digest or screening evidence, optional:

- Question: "Did a diagnostic digest or screen match expectations?"
- Options: "Pattern matched," "Pattern differed," "Partial or unclear," "Not performed," "Not applicable."
- Optional fields: enzymes, expected/observed band sizes, interpretation, notes.

Section 4, Expression or functional evidence:

- Question: "What happened in expression or functional testing?"
- Options: "Met expected function," "Below expected," "Absent," "Wrong product/localization," "Toxic or growth defect," "Not tested," "Not applicable," "Inconclusive."
- Optional fields: assay type, host/cell line, replicate count, controls used, normalized value, units, threshold, qualitative observation, notes.
- If design goal appears expression/function-related, "Not applicable" should trigger a non-blocking warning asking the user to confirm.

Section 5, Overall interpretation:

- Question: "Based on the evidence above, what is your interpretation?"
- Options mapped to `construct_validated` and future richer statuses:
- "Accepted for intended use" maps to `construct_validated=true` and future `validated`.
- "Did not validate" maps to `construct_validated=false` and future `failed`.
- "Partially validated" maps to `construct_validated=null` with notes and future `partially_validated`.
- "Attempted, but inconclusive" maps to `construct_validated=null` and future `inconclusive`.
- "Not built or not tested" maps to `construct_validated=null` and future `not_built`.
- Copy: "This is your interpretation. The evidence above determines whether the report is eligible for training or review."

Section 6, Notes:

- Optional multiline field.
- Prompt: "Add anything that would help interpret this outcome, such as protocol deviations, vendor issues, changed sequence, weak controls, or clone-specific details."
- Provide examples of useful notes without suggesting success or failure.

Section 7, Consent for training:

- Required unchecked checkbox.
- Label: "I consent to this outcome report and non-sensitive linked design metadata being used to improve future design models."
- Body copy: "Submitting an outcome does not require this consent. If unchecked, your report can still be saved for your records, support, audit, and aggregate product metrics according to policy, but it must not be used for model training or preference optimization."
- Secondary link: "What data is included?" expands concise details: outcome fields, design ID, model version, evidence summaries, provenance; uploaded artifacts only if a later policy explicitly includes them.
- Consent version should be captured in provenance when implemented.

Review footer:

- Primary action: "Review report" until all required fields are valid.
- Secondary action: "Save draft" if drafts are supported; otherwise "Close."
- Final action on review screen: "Submit outcome."

## Validation States

Use validation to protect data quality without forcing false certainty.

Blocking validation:

- The design context cannot be loaded.
- `design_id` or `model_version` is missing from the immutable context.
- No observed result is provided. Current `OutcomeReport` requires at least one of `construct_validated`, `sequencing_result`, `expression_result`, or `functional_result`.
- Consent checkbox has not been explicitly reviewed. The value may be false, but the user must make or confirm the choice.
- A required review confirmation is missing on the final review screen.

Non-blocking warnings:

- User selects "Accepted for intended use" but sequencing is not performed, low quality, partial, or inconclusive.
- User selects "Accepted for intended use" while expression/function evidence is absent for a function-oriented design.
- User selects "Did not validate" but also reports sequence match and expected function.
- User reports a modified design; explain that model-training eligibility may require review or a derived design ID.
- User reports protocol deviation or weak controls; explain that the outcome may be saved but not treated as design-attributable without review.
- User leaves notes empty on failed, partial, or inconclusive outcomes.

Inline validation language examples:

- "This report can be submitted, but it may be marked ambiguous because sequencing evidence is incomplete."
- "Training consent is optional. Please choose whether this report may be used for model improvement."
- "A failed cloning attempt without sequence or assay evidence may not be enough to classify the generated design as a negative training signal."

Derived status preview:

- Show a neutral panel titled "Evidence category" on the review screen only.
- Possible values: "Likely positive evidence," "Likely negative evidence," "Ambiguous evidence," "Not eligible for training."
- If `training_consent=false`, preview should say "Not eligible for training because consent was not granted" regardless of biological outcome.
- Avoid terms like "reward," "punish," or "AI score."

## Success States

Submission success page or modal:

- Title: "Outcome submitted"
- Body: "Your report was saved for this design. Thank you for sharing what happened."
- Status summary: interpretation, key evidence statuses, consent state, reported timestamp.
- If consent true: "This report may be reviewed for use in model improvement according to policy."
- If consent false: "This report will not be used for model training."
- Primary action: "Back to design"
- Secondary action: "Review report"
- Optional action: "Report another clone" if multiple outcome rows are later supported.

Avoid success-state bias:

- Do not use different emotional tone for positive versus negative outcomes.
- Do not say "Your design worked" unless the user is viewing their own chosen interpretation in the summary.
- Thank users equally for failed and inconclusive reports.

## Error Handling

Load errors:

- If design context fails to load, show a blocking error: "We could not load the design needed for this outcome report." Provide retry and back actions.
- If the outcome already exists but cannot be loaded, allow retry but do not open a blank overwrite form.

Submit errors:

- Keep all entered values in the form.
- Show a top-level error banner and field-level errors where possible.
- If the server rejects schema validation, translate to user language: "Add at least one observation before submitting" instead of exposing Pydantic or API internals.
- If the server reports stale outcome data, show a conflict state with "Review latest report" and "Apply my edits" only if safe merge exists.

Offline or timeout state:

- Keep local unsent draft in memory for the session.
- Show "Connection lost. Your answers are still on this page." Do not claim persistence unless local draft storage is implemented.

Consent errors:

- If consent text version cannot load, disable submission and show "Consent text could not be loaded. Try again before submitting."
- If consent is withdrawn during edit, require final confirmation before saving the changed consent state.

## Review And Edit Path

Review page layout:

- Summary card: design ID, model version, report timestamp, reporter/source if available.
- Evidence summary: sequencing, digest, expression/function, overall interpretation, notes.
- Consent summary: granted or not granted, consent text version if available.
- Provenance summary: collection channel, report version, uploaded artifact count if available.
- Actions: "Edit report," "Change training consent," "Back to design."

Editing behavior:

- Editing reopens the same form with submitted values prefilled.
- The design context remains locked.
- Any change to evidence or interpretation requires a new review step before resubmission.
- Changing only consent can use a shorter confirmation modal, but should still record updated provenance when implemented.
- If audit/revision support is not implemented, the UI should avoid promising version history.

Review copy:

- "Review your report before submitting. You can edit this later if you discover new evidence."
- "Changing consent affects future training eligibility. It may not remove data from already released aggregate analyses unless policy says so."

## Accessibility And Responsive Behavior

- All radio groups must have visible labels and support keyboard navigation.
- Warnings must not rely on color alone; include icon text or status labels.
- Mobile layout should keep "Save" or "Review report" visible in a sticky footer without covering fields.
- Long design IDs and model versions should wrap or truncate with copy controls.
- Upload controls, if later added, must support descriptive file status and removal before submission.

## Data Mapping Notes

Current `OutcomeReport` mapping:

- `design_id`: from immutable design context.
- `model_version`: from generated sequence model version; fallback to validation report model version only if generation version is unavailable.
- `construct_validated`: derived from overall interpretation where true means accepted for intended use, false means did not validate, and null means partial, inconclusive, not built, or not reported.
- `sequencing_result`: selected sequencing status plus optional compact details serialized as a string until structured fields exist.
- `expression_result`: selected expression evidence status plus optional compact details.
- `functional_result`: selected functional evidence status plus optional compact details.
- `training_consent`: explicit checkbox value.
- `outcome_label`: derived as `positive`, `negative`, or `ambiguous`; do not let the user directly set this.
- `provenance`: collection channel, form version, source type, design snapshot references, consent version, and edit metadata.
- `notes`: user-entered interpretation context.
- `reported_at`: server or client submission timestamp, preferably server-derived.

Future richer model compatibility:

- Preserve distinctions between not built, not applicable, not tested, and inconclusive even if current schema compresses them.
- Preserve digest evidence in provenance or notes until a first-class field exists.
- Preserve modified-design and multiple-clone flags for later review workflows.
- Treat positive/negative training labels as eligibility outputs, not UI-entered outcomes.

## Acceptance Criteria

- The user can submit an outcome without granting training consent.
- The form can capture positive, negative, partial, inconclusive, and not-built experiences without forcing a binary answer.
- The easiest accurate path is evidence first, interpretation second, consent last.
- Bias risks around "did your construct validate" are explicitly mitigated in copy and ordering.
- Validation blocks only missing context, missing observations, unreviewed consent, and final review omissions.
- Success states are neutral and equally appreciative for failed, ambiguous, and positive outcomes.
- Review/edit paths preserve the immutable design context and require confirmation before resubmission.
- The spec remains frontend-only and does not require changes to generation, registry, API fine-tuning, model-serving, or Phase 2 training code.
