import type { FeatureType } from "@/lib/types";

// Muted annotation palette tuned for the cooler near-white + green interface.
// SeqViz defaults are replaced with restrained product colors so the biological
// feature map stays integrated with the surrounding workspace chrome.
export const componentColors: Record<string, string> = {
  promoter: "#365f43",
  GOI: "#7b3d45",
  terminator: "#1f2320",
  ORI: "#a9782c",
  marker: "#6f7f68",
  MCS: "#556b74",
  other: "#5f665f"
};

export function componentColor(type: FeatureType): string {
  return componentColors[type] ?? componentColors.other;
}
