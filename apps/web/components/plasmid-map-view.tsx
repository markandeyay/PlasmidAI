"use client";

import dynamic from "next/dynamic";
import { Component, type ReactNode } from "react";
import { componentColor } from "@/lib/component-colors";
import type { AnnotatedFeature, AnnotatedSequence } from "@/lib/types";

const SeqViz = dynamic(() => import("seqviz").then((module) => module.SeqViz), {
  ssr: false,
  loading: () => (
    <div className="flex h-80 items-center justify-center" aria-busy="true" aria-label="Loading plasmid map">
      <div className="flex flex-col items-center gap-sm">
        <span className="h-10 w-10 animate-pulse rounded-pill bg-coral/30" aria-hidden="true" />
        <p className="text-small text-slate">Loading map...</p>
      </div>
    </div>
  )
});

type PlasmidMapViewProps = {
  annotatedSequence: AnnotatedSequence | null;
};

export function PlasmidMapView({ annotatedSequence }: PlasmidMapViewProps) {
  if (!annotatedSequence) {
    return (
      <section id="plasmid-map" className="flex h-full min-h-0 flex-col rounded-md border border-line bg-paper p-lg shadow-raised" aria-labelledby="plasmid-map-title-empty">
        <h2 id="plasmid-map-title-empty" className="font-serif text-h3 text-ink">Plasmid map</h2>
        <div className="mt-md flex h-full min-h-0 flex-1 flex-col items-center justify-center gap-sm rounded-md border border-dashed border-line-strong bg-mist px-lg text-center">
          <p className="font-serif text-h3 text-ink">No construct loaded</p>
          <p className="text-small leading-5 text-slate">Submit a design to render the annotated plasmid.</p>
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
    <section id="plasmid-map" className="flex h-full min-h-0 flex-col rounded-md border border-line bg-paper p-lg shadow-raised" aria-labelledby="plasmid-map-title">
      <div className="flex items-start justify-between gap-md">
        <div>
          <h2 id="plasmid-map-title" className="font-serif text-h3 text-ink">Plasmid map</h2>
          <p className="mt-2xs text-caption uppercase tracking-[0.06em] text-slate">
            {annotatedSequence.sequence.length.toLocaleString()} bp · {annotatedSequence.topology} sequence
          </p>
        </div>
        <span
          className={`rounded-pill border px-xs py-2xs text-caption font-semibold uppercase tracking-[0.06em] ${
            annotatedSequence.annotation_complete
              ? "border-sage/40 bg-sage/10 text-sage"
              : "border-honey/40 bg-honey/10 text-honey"
          }`}
        >
          {annotatedSequence.annotation_complete ? "Complete" : "Incomplete"}
        </span>
      </div>

      <div className="mt-md rounded-md border border-line bg-mist p-md text-small leading-5 text-slate">
        <p className="text-caption font-semibold uppercase tracking-[0.06em] text-slate">Accessible map summary</p>
        <dl className="mt-sm grid gap-2xs sm:grid-cols-2">
          <div><dt className="inline font-semibold text-ink">Name: </dt><dd className="inline">{annotatedSequence.vector_profile ?? "Plasmid design"}</dd></div>
          <div><dt className="inline font-semibold text-ink">Topology: </dt><dd className="inline">{annotatedSequence.topology}</dd></div>
          <div><dt className="inline font-semibold text-ink">Length: </dt><dd className="inline">{annotatedSequence.sequence.length.toLocaleString()} bp</dd></div>
          <div><dt className="inline font-semibold text-ink">Annotations: </dt><dd className="inline">{annotatedSequence.annotation_complete ? "complete" : "incomplete"}</dd></div>
          <div><dt className="inline font-semibold text-ink">Feature count: </dt><dd className="inline">{annotatedSequence.features.length}</dd></div>
        </dl>
        <p className="mt-sm text-slate">The interactive plasmid map is visual; use the feature list below for the accessible annotation summary.</p>
      </div>

      <MapErrorBoundary fallback={<MapFallback annotatedSequence={annotatedSequence} />}>
        <div
          className="mt-md flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-line bg-paper shadow-rest"
          aria-label="Visual interactive plasmid map"
        >
          <div data-testid="seqviz-map" className="h-full min-h-[280px] min-w-[320px] bg-paper p-sm">
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
    <div className="mt-md rounded-md border border-honey/40 bg-honey/10 p-md text-sm text-slate" data-testid="map-fallback">
      <p className="font-semibold text-honey">Map could not render</p>
      <p className="mt-2xs text-xs leading-5">
        The sequence and feature table are still available below: {annotatedSequence.sequence.length.toLocaleString()} bp {annotatedSequence.topology} sequence with {annotatedSequence.features.length} returned features.
      </p>
    </div>
  );
}

function FeatureLegend({ features, sequenceLength }: { features: AnnotatedFeature[]; sequenceLength: number }) {
  if (!features.length) {
    return (
      <section className="mt-md rounded-md border border-line bg-paper p-md" aria-label="Feature list">
        <h3 className="text-caption font-semibold uppercase tracking-[0.06em] text-slate">Feature list</h3>
        <p className="mt-2xs text-small leading-5 text-slate">No annotated features returned.</p>
      </section>
    );
  }

  return (
    <section className="mt-md rounded-md border border-line bg-paper" aria-labelledby="feature-list-title">
      <div className="border-b border-line bg-mist px-md py-sm">
        <h3 id="feature-list-title" className="text-caption font-semibold uppercase tracking-[0.06em] text-slate">Feature list</h3>
      </div>
      <ul className="max-h-56 overflow-y-auto">
      {features.map((feature, index) => (
        <li
          key={`${feature.name}-${feature.start}-${index}`}
          className="grid grid-cols-[12px_minmax(0,1fr)_auto] items-center gap-md border-b border-line px-md py-sm last:border-b-0"
          title={`${feature.name} (${feature.type}) ${feature.start + 1}..${feature.end}`}
        >
          <span className="h-3 w-3 rounded-pill border border-line" style={{ backgroundColor: componentColor(feature.type) }} aria-hidden />
          <div className="min-w-0">
            <p className="break-words text-small font-medium text-ink">{feature.name}</p>
            <p className="text-caption text-slate">
              Type: {feature.type} · Coordinates: {feature.start + 1}..{Math.min(feature.end, sequenceLength)} · Strand: {strandLabel(feature.strand)}
            </p>
          </div>
          <span className="text-small tabular-nums text-slate" aria-label={`Confidence ${Math.round(feature.confidence * 100)} percent`}>{Math.round(feature.confidence * 100)}%</span>
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