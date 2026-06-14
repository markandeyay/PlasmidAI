# Visual Consistency Audit

Scope: `apps/web` frontend visual consistency only. Audited inferred states for the chat workspace, plasmid map, validation report, export controls, outcome submission UI, pending outcome prompt, and My outcomes panel.

## Highest Impact Findings

1. Button hierarchy varies across adjacent panels and weakens primary actions.

   References: `apps/web/app/page.tsx:386`, `apps/web/app/page.tsx:447`, `apps/web/app/page.tsx:477`, `apps/web/app/page.tsx:502`, `apps/web/components/export-actions.tsx:49`, `apps/web/components/outcome-report-modal.tsx:299`.

   Impact: The same action family appears as filled teal, outlined teal, plain bordered, and text-only across the workspace. Export buttons look less like actions than example prompt chips, while the My outcomes review action uses a full-width outlined style unlike the Lab outcome review action's filled primary style. Users may not immediately understand which action is primary in each state.

   Recommended minimal fix: Standardize local button roles without new tokens: use filled `bg-action text-white` for the single primary action in a panel or modal footer, outlined `border-action text-action bg-white hover:bg-action/5` for secondary action, and neutral bordered buttons only for dismissive or low-emphasis actions. Apply hover/focus affordances consistently to all active buttons.

2. Status badge styling is duplicated but not fully consistent.

   References: `apps/web/app/page.tsx:460`, `apps/web/app/page.tsx:570`, `apps/web/components/plasmid-map-view.tsx:46`, `apps/web/components/outcome-report-modal.tsx:243`.

   Impact: PASS/positive/complete states share similar colors but different text casing and font weight. The outcome modal's `Needs evidence` / `Ready to submit` badge uses neutral gray even though it represents an actionable state. The plasmid map completion badge omits `font-semibold`, making it read differently from validation and outcome badges.

   Recommended minimal fix: Reuse the same badge visual recipe in-place: `border px-2 py-1 text-xs font-semibold` plus the existing action/warning/red/neutral color classes. Keep label casing intentional: uppercase for validation checks only, title/capitalized for product states.

3. Pending outcome prompt competes with the chat composer on small screens.

   References: `apps/web/app/page.tsx:470`, `apps/web/app/page.tsx:348`.

   Impact: The fixed bottom-right prompt is full-width on mobile and sits over the bottom composer area. This can make the first screen feel crowded and can obscure the primary input path, especially when the outcome prompt appears before a user starts a design.

   Recommended minimal fix: On small screens, place the prompt at the top or add bottom spacing when it is visible. Keep desktop bottom-right behavior. If it remains bottom-fixed, increase contrast between prompt and composer with a stronger shadow or top offset from the composer.

4. Similar card panels use inconsistent internal density and footer patterns.

   References: `apps/web/app/page.tsx:400`, `apps/web/app/page.tsx:425`, `apps/web/app/page.tsx:490`, `apps/web/components/export-actions.tsx:13`, `apps/web/components/plasmid-map-view.tsx:19`, `apps/web/components/outcome-report-modal.tsx:315`.

   Impact: Right-rail panels mostly use `p-4`, but nested content alternates between `mt-3` and `mt-4`, `gap-2` and `gap-3`, and full-width actions vs two-column actions. The modal uses `p-5` and a separate top Close link plus sticky footer, which makes it feel like a different UI family from the side panels.

   Recommended minimal fix: Normalize right-rail panel rhythm to header, `mt-4` body/action area, and `gap-2` for compact controls. Keep modal `p-5` if desired, but make its close affordance align with footer button styling or remove visual competition from the top Close link.

## Medium Impact Findings

1. Typography hierarchy is very flat in the right rail.

   References: `apps/web/components/plasmid-map-view.tsx:20`, `apps/web/components/export-actions.tsx:16`, `apps/web/app/page.tsx:428`, `apps/web/app/page.tsx:491`.

   Impact: All right-rail panel headings use `text-sm font-semibold`, while panel descriptions and dense content are mostly `text-xs`. This is consistent but low-contrast; the plasmid map, export, lab outcome, and My outcomes panels compete equally even though the plasmid map is the primary visual artifact.

   Recommended minimal fix: Promote the plasmid map heading or add a stronger metadata row in that panel only. Avoid changing the global type scale unless a broader design pass is planned.

2. Export feedback is visually under-emphasized compared with errors and success states elsewhere.

   References: `apps/web/components/export-actions.tsx:26`, `apps/web/components/export-actions.tsx:27`, `apps/web/app/page.tsx:295`, `apps/web/components/outcome-report-modal.tsx:295`.

   Impact: Export errors and success messages are plain text while validation and outcome submission use bordered panels or badges. A failed export may be missed in the right rail.

   Recommended minimal fix: Wrap export error/success feedback in compact bordered message rows using existing red/action color classes, matching the tone of validation and modal warnings.

3. Chat result content mixes multiple visual languages inside one bubble.

   References: `apps/web/app/page.tsx:305`, `apps/web/app/page.tsx:323`, `apps/web/app/page.tsx:326`, `apps/web/app/page.tsx:337`, `apps/web/app/page.tsx:542`.

   Impact: Assistant bubbles can contain plain text, a nested validation card, retrieved template list, and a standalone link. The nested validation report has stronger card framing than the parent bubble content, so the response can feel visually fragmented.

   Recommended minimal fix: Give the retrieved templates list and plasmid map link the same `mt-3` compact section treatment as validation metadata, or reduce the nested validation card's background contrast inside chat bubbles.

4. Empty states are visually inconsistent across panels.

   References: `apps/web/components/plasmid-map-view.tsx:21`, `apps/web/app/page.tsx:454`, `apps/web/components/export-actions.tsx:17`, `apps/web/app/page.tsx:493`.

   Impact: Plasmid map empty state uses a large dashed box, My outcomes uses a bordered filled box, Export uses text-only disabled context, and Lab outcome uses body copy plus a disabled button. Each is understandable, but the first impression of the right rail is uneven before a design exists.

   Recommended minimal fix: Use a consistent empty-state recipe for right-rail panels: short muted copy plus either a dashed content well for large visual areas or a disabled action row for action panels. Keep the plasmid map's large dashed well because it reserves space for the eventual map.

## Lower Impact Findings

1. Focus states rely almost entirely on border color changes.

   References: `apps/web/app/page.tsx:373`, `apps/web/components/outcome-report-modal.tsx:260`, `apps/web/components/outcome-report-modal.tsx:327`.

   Impact: Inputs and selects use `outline-none focus:border-action`, which is subtle on the light green panel background and less polished than the rest of the interaction model.

   Recommended minimal fix: Add a consistent visible focus ring using existing action color opacity classes to inputs, selects, textareas, and buttons.

2. First impression is polished but overly flat.

   References: `apps/web/app/page.tsx:294`, `apps/web/app/page.tsx:298`, `apps/web/app/globals.css:20`, `apps/web/tailwind.config.ts:14`.

   Impact: The restrained palette and square cards are coherent, but every surface uses similar borders and a very subtle shadow. The app can read as wireframe-like before the SeqViz map loads.

   Recommended minimal fix: Increase visual emphasis only on the primary workspace/card surfaces, such as the plasmid map panel or active chat card, rather than changing all surfaces.

## Screen And State Coverage Notes

- Chat workspace: welcome, user prompt, assistant result, clarification, error, busy polling, example prompt chips, composer disabled/enabled.
- Plasmid map: empty state, loading state, rendered map, complete/incomplete annotation badge, feature legend.
- Validation report: overall PASS/WARN/FAIL/UNKNOWN, checks list, empty checks.
- Export controls: disabled before design, loading, success, error.
- Outcome submission UI: empty form, validation issues, warnings, API error, submitted confirmation, sticky footer.
- Pending outcome prompt: visible prompt, primary report action, secondary dismiss action.
- My outcomes panel: empty state, populated list, status badge, review/edit action.

## Questions For The Human

1. Should `apps/web` introduce shared local primitives for buttons, badges, cards, and messages, or should Phase 4 visual polish stay as class normalization in existing components only?

2. Should the app adopt a stronger brand treatment, such as rounded cards, larger shadows, or a richer accent palette, or preserve the current sparse scientific-tool aesthetic?

3. Should status colors be formalized as semantic tokens beyond `action` and `warning`, especially for error, neutral, success, and ambiguous states?

4. Should the pending outcome prompt be treated as a toast, a banner, or a right-rail card on desktop? The current toast behavior is functional but may not be the best long-term notification pattern.
