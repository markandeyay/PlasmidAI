"use client";

import dynamic from "next/dynamic";
import { componentColor } from "@/lib/component-colors";
import type { AnnotatedFeature, AnnotatedSequence } from "@/lib/types";

const SeqViz = dynamic(() => import("seqviz").then((module) => module.SeqViz), {
  ssr: false,
  loading: () => <div className="flex h-80 items-center justify-center text-sm text-slate-500">Loading map...</div>
});

type PlasmidMapViewProps = {
  annotatedSequence: AnnotatedSequence | null;
};

export function PlasmidMapView({ annotatedSequence }: PlasmidMapViewProps) {
  if (!annotatedSequence) {
    return (
      <section id="plasmid-map" className="border border-line bg-white p-4 shadow-subtle" aria-label="Plasmid map">
        <h2 className="text-sm font-semibold">Plasmid map</h2>
        <div className="mt-4 flex h-64 items-center justify-center border border-dashed border-line bg-panel px-6 text-center text-sm text-slate-500 sm:h-80 lg:h-96">
          Submit a design to render the annotated plasmid.
        </div>
      </section>
    );
  }

  const annotations = annotatedSequence.features.map((feature) => ({
    name: feature.name,
    start: clampCoordinate(feature.start, annotatedSequence.sequence.length),
    end: clampCoordinate(feature.end, annotatedSequence.sequence.length),
    direction: feature.strand === 0 ? 0 : feature.strand,
    type: feature.type,
    color: componentColor(feature.type)
  }));

  return (
    <section id="plasmid-map" className="border border-line bg-white p-4 shadow-subtle" aria-label="Plasmid map">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold">Plasmid map</h2>
          <p className="mt-1 text-xs text-slate-600">
            {annotatedSequence.sequence.length.toLocaleString()} bp {annotatedSequence.topology} sequence
          </p>
        </div>
        <span
          className={`border px-2 py-1 text-xs font-semibold ${
            annotatedSequence.annotation_complete
              ? "border-action/40 bg-action/10 text-action"
              : "border-warning/40 bg-amber-50 text-warning"
          }`}
        >
          {annotatedSequence.annotation_complete ? "Complete" : "Incomplete"}
        </span>
      </div>

      <div className="mt-4 overflow-auto border border-line">
        <div data-testid="seqviz-map" className="h-[360px] min-w-[320px] bg-white sm:h-[440px] lg:h-[520px]">
          <SeqViz
            name={annotatedSequence.vector_profile ?? "Plasmid design"}
            seq={annotatedSequence.sequence}
            annotations={annotations}
            disableExternalFonts
            primers={[]}
            viewer={annotatedSequence.topology === "circular" ? "both" : "linear"}
          />
        </div>
      </div>

      <FeatureLegend features={annotatedSequence.features} sequenceLength={annotatedSequence.sequence.length} />
    </section>
  );
}

function FeatureLegend({ features, sequenceLength }: { features: AnnotatedFeature[]; sequenceLength: number }) {
  if (!features.length) {
    return <p className="mt-3 text-xs text-slate-500">No annotated features returned.</p>;
  }

  return (
    <div className="mt-4 max-h-56 overflow-y-auto border border-line">
      {features.map((feature, index) => (
        <div
          key={`${feature.name}-${feature.start}-${index}`}
          className="grid grid-cols-[12px_minmax(0,1fr)_auto] items-center gap-3 border-b border-line px-3 py-2 last:border-b-0"
          title={`${feature.name} (${feature.type}) ${feature.start + 1}..${feature.end}`}
        >
          <span className="h-3 w-3" style={{ backgroundColor: componentColor(feature.type) }} aria-hidden />
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-slate-800">{feature.name}</p>
            <p className="text-xs text-slate-500">
              {feature.type} · {feature.start + 1}..{Math.min(feature.end, sequenceLength)} · {strandLabel(feature.strand)}
            </p>
          </div>
          <span className="text-xs tabular-nums text-slate-500">{Math.round(feature.confidence * 100)}%</span>
        </div>
      ))}
    </div>
  );
}

function strandLabel(strand: -1 | 0 | 1): string {
  if (strand === 1) {
    return "forward";
  }
  if (strand === -1) {
    return "reverse";
  }
  return "none";
}

function clampCoordinate(value: number, sequenceLength: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.min(value, sequenceLength));
}
