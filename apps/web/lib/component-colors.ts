import type { FeatureType } from "@/lib/types";

export const componentColors: Record<string, string> = {
  ORI: "#2F80ED",
  promoter: "#27AE60",
  GOI: "#9B51E0",
  marker: "#EB5757",
  MCS: "#F2994A",
  terminator: "#56CCF2",
  other: "#828282"
};

export function componentColor(type: FeatureType): string {
  return componentColors[type] ?? componentColors.other;
}
