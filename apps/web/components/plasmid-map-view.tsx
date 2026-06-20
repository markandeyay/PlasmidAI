"use client";

import dynamic from "next/dynamic";
import { Component, type ReactNode } from "react";
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
      <section id="plasmid-map" className="border border-line bg-white p-4 shadow-subtle" aria-labelledby="plasmid-map-title-empty">
        <h2 id="plasmid-map-title-empty" className="text-sm font-semibold">Plasmid map</h2>
        <div className="mt-4 flex h-64 flex-col items-center justify-center gap-2 border border-dashed border-line bg-panel px-6 text-center sm:h-80 lg:h-96">
          <p className="text-sm font-semibold text-slate-700">No construct loaded</p>
          <p className="text-xs leading-5 text-slate-500">Submit a design to render the annotated plasmid.</p>
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
    <section id="plasmid-map" className="border border-line bg-white p-4 shadow-subtle" aria-labelledby="plasmid-map-title">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 id="plasmid-map-title" className="text-sm font-semibold">Plasmid map</h2>
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

      <div className="mt-4 border border-line bg-panel p-3 text-xs leading-5 text-slate-700">
        <p className="font-semibold text-slate-800">Accessible map summary</p>
        <dl className="mt-2 grid gap-1 sm:grid-cols-2">
          <div><dt className="inline font-semibold">Name: </dt><dd className="inline">{annotatedSequence.vector_profile ?? "Plasmid design"}</dd></div>
          <div><dt className="inline font-semibold">Topology: </dt><dd className="inline">{annotatedSequence.topology}</dd></div>
          <div><dt className="inline font-semibold">Length: </dt><dd className="inline">{annotatedSequence.sequence.length.toLocaleString()} bp</dd></div>
          <div><dt className="inline font-semibold">Annotations: </dt><dd className="inline">{annotatedSequence.annotation_complete ? "complete" : "incomplete"}</dd></div>
          <div><dt className="inline font-semibold">Feature count: </dt><dd className="inline">{annotatedSequence.features.length}</dd></div>
        </dl>
        <p className="mt-2 text-slate-600">The interactive plasmid map is visual; use the feature list below for the accessible annotation summary.</p>
      </div>

      <MapErrorBoundary fallback={<MapFallback annotatedSequence={annotatedSequence} />}>
        <div className="mt-4 overflow-auto border border-line" aria-label="Visual interactive plasmid map">
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
      </MapErrorBoundary>

      <FeatureLegend features={annotatedSequence.features} sequenceLength={annotatedSequence.sequence.length} />
    </section>
  );
}

class MapErrorBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function MapFallback({ annotatedSequence }: { annotatedSequence: AnnotatedSequence }) {
  return (
    <div className="mt-4 border border-warning/40 bg-amber-50 p-4 text-sm text-slate-700" data-testid="map-fallback">
      <p className="font-semibold text-warning">Map could not render</p>
      <p className="mt-1 text-xs leading-5">
        The sequence and feature table are still available below: {annotatedSequence.sequence.length.toLocaleString()} bp {annotatedSequence.topology} sequence with {annotatedSequence.features.length} returned features.
      </p>
    </div>
  );
}

function FeatureLegend({ features, sequenceLength }: { features: AnnotatedFeature[]; sequenceLength: number }) {
  if (!features.length) {
    return <p className="mt-3 text-xs text-slate-500">No annotated features returned.</p>;
  }

  return (
    <section className="mt-4 border border-line" aria-labelledby="feature-list-title">
      <div className="border-b border-line bg-panel px-3 py-2">
        <h3 id="feature-list-title" className="text-xs font-semibold uppercase text-slate-600">Feature list</h3>
      </div>
      <ul className="max-h-56 overflow-y-auto">
      {features.map((feature, index) => (
        <li
          key={`${feature.name}-${feature.start}-${index}`}
          className="grid grid-cols-[12px_minmax(0,1fr)_auto] items-center gap-3 border-b border-line px-3 py-2 last:border-b-0"
          title={`${feature.name} (${feature.type}) ${feature.start + 1}..${feature.end}`}
        >
          <span className="h-3 w-3" style={{ backgroundColor: componentColor(feature.type) }} aria-hidden />
          <div className="min-w-0">
            <p className="break-words text-xs font-medium text-slate-800">{feature.name}</p>
            <p className="text-xs text-slate-500">
              Type: {feature.type} · Coordinates: {feature.start + 1}..{Math.min(feature.end, sequenceLength)} · Strand: {strandLabel(feature.strand)}
            </p>
          </div>
          <span className="text-xs tabular-nums text-slate-500" aria-label={`Confidence ${Math.round(feature.confidence * 100)} percent`}>{Math.round(feature.confidence * 100)}%</span>
        </li>
      ))}
      </ul>
    </section>
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
