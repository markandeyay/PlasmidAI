# PlasmidAI Web Design System

Scope: visual tokens for `apps/web` redesign. Light mode only. Audience: PhD-track researchers and biotech professionals. Direction: warm cream surfaces, restrained serif-influenced headings, a single coral/terracotta accent used selectively, ample breathing room, serious and confident rather than playful.

This document defines the tokens. IMPL subagents map them verbatim from the Tailwind block at the end. All values are exact.

---

## 1. Color Palette

All tokens are warm-toned. Nothing is pure black or pure white. The palette is organized as: primary/secondary surfaces, deep text, single accent, supporting neutrals, and three semantic validation colors that harmonize with cream + coral rather than using default green/yellow/red.

### Surfaces

| Token | Hex | Usage |
| --- | --- | --- |
| `cream` | `#f7f3ea` | Primary app background. Warm archival-paper cream, slightly more grounded than Anthropic's `#faf9f5` so it reads as a serious scientific tool rather than a marketing page. |

### Text

| Token | Hex | Usage |
| --- | --- | --- |
| `ink` | `#2b2620` | Primary text and deep UI marks. A warm near-black with a faint brown undertone instead of neutral black, so it never feels cold against cream. |
| `slate` | `#6c6354` | Secondary/caption text, metadata, helper copy. Warm taupe grey for hierarchy below `ink` while staying in family. |

### Accent (use SELECTIVELY — primary actions only)

| Token | Hex | Usage |
| --- | --- | --- |
| `coral` | `#c1553c` | The single accent. Terracotta-leaning coral, muted toward seriousness. Reserved for the one primary action in any panel/modal, active focus rings, and key links. Never used as a background fill for large surfaces or as decorative chrome. |

### Supporting neutrals (borders, depth, subtle fills)

| Token | Hex | Usage |
| --- | --- | --- |
| `line` | `#e3dcc8` | Default 1px borders and dividers on `cream`. Subtle warm grey, readable without competing with content. |
| `line-strong` | `#d4caaf` | Stronger borders, focused input borders pre-ring, and section dividers that need more presence than `line`. |
| `mist` | `#ece5d4` | Subtle warm fill for inset wells, hover backgrounds, and selected-row tints. One step warmer/lighter than `cream`-adjacent neutrals, used to lift interactive zones without introducing a new hue. |
| `paper` | `#fefcf6` | Card and panel fill. Near-white with a warm tint so raised surfaces read as clean paper layered on the cream background (paper is lighter than cream, creating gentle elevation without shadow). |

### Semantic validation (PASS / WARN / FAIL)

Chosen to harmonize with cream + coral. None use default green/yellow/red.

| Token | Hex | Usage |
| --- | --- | --- |
| `sage` | `#6e8a5a` | PASS. Muted sage green, desaturated so it coexists with coral and never reads as a consumer "success" green. Used for PASS check badges and positive validation markers. |
| `honey` | `#bd862f` | WARN. Honey/amber, warm and serious rather than caution-yellow. Used for WARN checks and ambiguous warnings. |
| `clay` | `#7e3540` | FAIL. Muted burgundy/oxblood, deep and clearly distinct from the lighter coral accent. Used for FAIL checks and blocking errors only. |

---

## 2. Typography

Two families total: one serif display for headings, one sans for body and UI. Cohesion over variety.

### Families

- **Headings (serif display):** `Newsreader`, Google Fonts.
  - Character without being decorative; a refined editorial serif that signals "this was built by people who care about craft."
  - Google Fonts import: weights 500 and 600, normal + italic for the 500.
  - Fallback stack: `'Newsreader', 'Iowan Old Style', 'Apple Garamond', Georgia, 'Times New Roman', serif`.
- **Body & UI (sans):** `Inter`, self-host or Google Fonts.
  - Pairs cleanly with Newsreader; remains highly readable for dense biological text, sequences, and metadata. Kept (rather than swapping to a more "designed" sans) because scientific UI legibility is non-negotiable and Inter is the safest readable choice in this family.
  - Fallback stack: `'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`.

### Type scale

All sizes in `rem`. Line-heights chosen for the serifs' looser display needs and the body's denser reading rhythm.

| Token | Size | Line height | Weight | Face | Used for |
| --- | --- | --- | --- | --- | --- |
| `display` (h1) | `2.25rem` (36px) | `1.2` | 600 | Newsreader | Page titles, primary workspace banner. Use sparingly — at most one per screen. |
| `h2` | `1.625rem` (26px) | `1.25` | 600 | Newsreader | Section heads, modal titles. |
| `h3` | `1.25rem` (20px) | `1.3` | 600 | Newsreader | Panel headings, card titles. |
| `body` | `1rem` (16px) | `1.6` | 400 | Inter | Default reading text, paragraphs, list rows. |
| `small` | `0.875rem` (14px) | `1.5` | 400 | Inter | Caption-adjacent prose, dense metadata rows, secondary controls. |
| `caption` | `0.75rem` (12px) | `1.4` | 500 | Inter | Labels, badges, table headers. Optional uppercase with `letter-spacing: 0.06em` for uppercase-only labels (e.g. validation check badges). |

Weight usage: Newsreader 600 for headings, Inter 400 for body, Inter 500 for UI labels and small interactive text. Inter 600 is reserved for inline emphasis inside body (e.g. a key term in a paragraph); headings should stay on Newsreader so the serif/sans split carries hierarchy.

---

## 3. Spacing Scale

4px base throughout. Named tokens reduce ad-hoc values in components.

| Token | Value |
| --- | --- |
| `2xs` | `4px` |
| `xs` | `8px` |
| `sm` | `12px` |
| `md` | `16px` |
| `lg` | `24px` |
| `xl` | `32px` |
| `2xl` | `48px` |
| `3xl` | `64px` |

Defaults for the redesign: panel padding `lg` (24px), gap between stacked controls `sm` (12px), internal component padding `xs`–`md`. The "breathing room" target is achieved by leaning on `lg`/`xl` for section separation rather than by adding shadows.

---

## 4. Border Radius

Moderate rounding in the Anthropic range (8–12px) for primary surfaces, smaller for controls.

| Token | Value | Used for |
| --- | --- | --- |
| `sm` | `6px` | Inputs, selects, buttons, chips, small badges. |
| `md` | `10px` | Cards, panels, right-rail surfaces. |
| `lg` | `14px` | Modals, large floating surfaces, the primary workspace card. |
| `pill` | `9999px` | Status badges only (PASS/WARN/FAIL pills). |

Do not round corners of full-bleed surfaces (e.g. the app shell). `md` (10px) is the default for any new card-like element unless it is explicitly a modal or a control.

---

## 5. Shadows

Warm-toned. Shadow color is derived from `ink` (`#2b2620` → `rgba(43, 38, 32, …)`) rather than pure black, so shadows never read cold against the cream background. Three elevation levels only.

| Token | Value | Usage |
| --- | --- | --- |
| `rest` | `0 1px 2px rgba(43, 38, 32, 0.06)` | Resting surfaces, subtle separation where a border alone would flatten. The default-light shadow. |
| `raised` | `0 2px 4px rgba(43, 38, 32, 0.07), 0 1px 2px rgba(43, 38, 32, 0.05)` | Cards and panels that sit above `cream`, especially when their fill is `paper`. |
| `floating` | `0 12px 28px rgba(43, 38, 32, 0.10), 0 4px 10px rgba(43, 38, 32, 0.06)` | Modals, popovers, and the floating pending-outcome prompt. |

Elevation should be earned: most surfaces use border + `rest` at most. Only the primary workspace card and modals reach `raised`/`floating`. This directly addresses the audit's "first impression is polished but overly flat / wireframe-like" finding by giving the few important surfaces clear lift without blanketing everything in shadow.

---

## 6. Tailwind Mapping (for IMPL-1)

Drop-in `theme.extend` for `apps/web/tailwind.config.ts`. The IMPL-1 subagent should use this verbatim and not invent additional tokens.

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Surfaces
        cream: "#f7f3ea",
        paper: "#fefcf6",
        // Text
        ink: "#2b2620",
        slate: "#6c6354",
        // Accent (use selectively)
        coral: "#c1553c",
        // Supporting neutrals
        line: "#e3dcc8",
        "line-strong": "#d4caaf",
        mist: "#ece5d4",
        // Semantic validation
        sage: "#6e8a5a",
        honey: "#bd862f",
        clay: "#7e3540",
      },
      fontFamily: {
        serif: [
          "Newsreader",
          "Iowan Old Style",
          "Apple Garamond",
          "Georgia",
          "Times New Roman",
          "serif",
        ],
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      fontSize: {
        display: ["2.25rem", { lineHeight: "1.2", fontWeight: "600" }],
        h2: ["1.625rem", { lineHeight: "1.25", fontWeight: "600" }],
        h3: ["1.25rem", { lineHeight: "1.3", fontWeight: "600" }],
        body: ["1rem", { lineHeight: "1.6" }],
        small: ["0.875rem", { lineHeight: "1.5" }],
        caption: ["0.75rem", { lineHeight: "1.4", fontWeight: "500" }],
      },
      spacing: {
        "2xs": "4px",
        xs: "8px",
        sm: "12px",
        md: "16px",
        lg: "24px",
        xl: "32px",
        "2xl": "48px",
        "3xl": "64px",
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
        pill: "9999px",
      },
      boxShadow: {
        rest: "0 1px 2px rgba(43, 38, 32, 0.06)",
        raised:
          "0 2px 4px rgba(43, 38, 32, 0.07), 0 1px 2px rgba(43, 38, 32, 0.05)",
        floating:
          "0 12px 28px rgba(43, 38, 32, 0.10), 0 4px 10px rgba(43, 38, 32, 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
```

Usage conventions to document for IMPL subagents (not enforced by config):
- Headings use `font-serif`; body and UI use the default `font-sans`.
- Primary action button: `bg-coral text-paper rounded-md shadow-rest hover:shadow-raised`.
- Secondary action: `border border-line-strong text-ink bg-paper rounded-md hover:bg-mist`.
- Panel/card surface: `bg-paper rounded-md border border-line shadow-rest`.
- PASS/WARN/FAIL badges: `rounded-pill` with `sage` / `honey` / `clay` text and a matching `border` + faint `bg-<token>/10` fill.
- Focus ring: `outline-none focus:ring-2 focus:ring-coral/40 focus:border-coral` on inputs, selects, textareas, and buttons. This replaces the audit's "focus relies only on border color" pattern with a visible warm ring.

---

## Notes on Judgment Calls

- **Cream `#f7f3ea` vs Anthropic `#faf9f5`:** Chose a marginally warmer/tanner cream because a biotech tool should read as archival lab-notebook paper rather than a marketing site; `#faf9f5` drifts too close to neutral white for this audience.
- **Corral `#c1553c` vs Anthropic `#d97757`:** Pulled the accent toward terracotta and slightly darker/muted. Anthropic's coral is lively; a plasmid design tool's accent should feel chosen, not energetic.
- **FAIL `#7e3540` (burgundy) instead of coral-adjacent clay:** The coral accent already occupies the warm-red register. FAIL needed to stay clearly distinct and serious, so I deepened it to an oxblood that reads as "stop" while remaining in the warm family.
- **Kept Inter for body despite "more personality" option:** Dense sequence/metadata text in this app makes readability non-negotiable. Newsreader supplies the personality at the heading level; Inter keeps body safe. One serif + one sans keeps cohesion.
- **Paper lighter than cream:** Reversed the common "card darker than bg" instinct so paper cards read as clean sheets lifted off a cream desk, using fill value rather than heavy shadows to create depth (addresses the audit's "flat/wireframe-like" note without a shadow-heavy fix).