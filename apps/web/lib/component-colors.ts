import type { FeatureType } from "@/lib/types";

// Warm, muted annotation palette tuned for the cream (#f7f3ea) + coral (#c1553c)
// layout. Cool/saturated SeqViz defaults are replaced with earth-tones drawn from
// the design system (coral, clay, honey, sage, ink, slate) plus two complementary
// warm hues, so every feature reads on a paper/cream canvas and pairs with coral
// chrome. Each type keeps a consistent, distinguishable, color-blind-thoughtful hue.
export const componentColors: Record<string, string> = {
  promoter: "#c1553c", // coral — the accent; promoters are the primary regulatory element
  GOI: "#7e3540", // clay burgundy — gene of interest, deep and serious
  terminator: "#2b2620", // ink near-black — stop signals, grounded
  ORI: "#bd862f", // honey ochre — replication origin, warm metallic
  marker: "#6e8a5a", // muted sage — selection markers, calm
  MCS: "#a8783a", // warm bronze — multiple cloning site, distinct from honey
  other: "#6c6354" // slate taupe — neutral fallback
};

export function componentColor(type: FeatureType): string {
  return componentColors[type] ?? componentColors.other;
}