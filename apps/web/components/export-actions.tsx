export type ExportFormat = "genbank" | "fasta";
export type ExportStatus = "idle" | "loading" | "success" | "error";

type ExportActionsProps = {
  designId: string | null;
  status: Record<ExportFormat, ExportStatus>;
  error: Record<ExportFormat, string | null>;
  disabledReason?: string | null;
  onExport: (format: ExportFormat) => Promise<void>;
};

export function ExportActions({ designId, status, error, disabledReason, onExport }: ExportActionsProps) {
  const loading = status.genbank === "loading" || status.fasta === "loading";
  const successLabel = status.genbank === "success" ? "GenBank download started." : status.fasta === "success" ? "FASTA download started." : null;

  return (
    <section className="rounded-md border border-line bg-paper p-md shadow-rest" aria-label="Export actions" aria-busy={loading}>
      <div className="flex items-start justify-between gap-sm">
        <div>
          <h2 className="font-serif text-h3 text-ink">Export</h2>
          <p className="mt-2xs text-small text-slate">
            {designId ? `Design ${designId}` : "Complete a design job to enable downloads."}
          </p>
        </div>
      </div>
      <div className="mt-md grid grid-cols-2 gap-sm">
        <ExportButton designId={designId} disabled={Boolean(disabledReason)} format="genbank" label="GenBank" status={status.genbank} onExport={onExport} />
        <ExportButton designId={designId} disabled={Boolean(disabledReason)} format="fasta" label="FASTA" status={status.fasta} onExport={onExport} />
      </div>
      {loading ? <p className="sr-only" role="status" aria-live="polite">Preparing export.</p> : null}
      {disabledReason ? <p className="mt-sm rounded-md border border-line bg-mist p-sm text-small text-slate">{disabledReason}</p> : null}
      {error.genbank ? <p className="mt-sm rounded-md border border-clay/40 bg-clay/10 p-sm text-small font-medium text-clay" role="alert">{error.genbank}</p> : null}
      {error.fasta ? <p className="mt-sm rounded-md border border-clay/40 bg-clay/10 p-sm text-small font-medium text-clay" role="alert">{error.fasta}</p> : null}
      {successLabel ? (
        <p className="mt-sm rounded-md border border-sage/40 bg-sage/10 p-sm text-small font-semibold text-sage" role="status" aria-live="polite">{successLabel}</p>
      ) : null}
    </section>
  );
}

function ExportButton({
  designId,
  disabled,
  format,
  label,
  status,
  onExport
}: {
  designId: string | null;
  disabled: boolean;
  format: ExportFormat;
  label: string;
  status: ExportStatus;
  onExport: (format: ExportFormat) => Promise<void>;
}) {
  const loading = status === "loading";
  const buttonLabel = loading ? "Preparing..." : status === "success" ? `${label} ready` : label;
  return (
    <button
      type="button"
      disabled={!designId || disabled || loading}
      onClick={() => void onExport(format)}
      aria-busy={loading || undefined}
      className="relative overflow-hidden rounded-md border border-line-strong bg-paper px-md py-sm text-sm font-semibold text-ink hover:bg-mist focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40 disabled:cursor-not-allowed disabled:border-line disabled:bg-paper disabled:text-slate disabled:hover:bg-paper"
    >
      <span className="relative z-10">{buttonLabel}</span>
      {loading ? <span className="absolute inset-x-0 bottom-0 z-0 h-2xs w-2/3 origin-left animate-pulse rounded-pill bg-coral/40" aria-hidden="true" /> : null}
    </button>
  );
}