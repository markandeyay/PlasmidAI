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
    <section aria-label="Export actions" aria-busy={loading} className="flex min-h-0 flex-col justify-center gap-2xs">
      <p className="text-caption text-slate">
        {designId ? `Design ${designId}` : "Complete a design job to enable downloads."}
      </p>
      {designId ? (
        <div className="flex flex-wrap gap-xs">
          <ExportButton designId={designId} disabled={Boolean(disabledReason)} format="genbank" label="GenBank" status={status.genbank} onExport={onExport} />
          <ExportButton designId={designId} disabled={Boolean(disabledReason)} format="fasta" label="FASTA" status={status.fasta} onExport={onExport} />
        </div>
      ) : null}
      {loading ? <p className="sr-only" role="status" aria-live="polite">Preparing export.</p> : null}
      {disabledReason ? <p className="text-caption text-slate">{disabledReason}</p> : null}
      {error.genbank ? <p className="text-caption text-clay" role="alert">{error.genbank}</p> : null}
      {error.fasta ? <p className="text-caption text-clay" role="alert">{error.fasta}</p> : null}
      {successLabel ? <p className="text-caption text-sage" role="status" aria-live="polite">{successLabel}</p> : null}
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
      className="relative overflow-hidden rounded-md border border-line-strong bg-paper px-sm py-2xs text-sm font-semibold text-ink hover:bg-mist focus:border-coral focus:outline-none focus:ring-2 focus:ring-coral/40 disabled:cursor-not-allowed disabled:border-line disabled:bg-paper disabled:text-slate disabled:hover:bg-paper"
    >
      <span className="relative z-10">{buttonLabel}</span>
      {loading ? <span className="absolute inset-x-0 bottom-0 z-0 h-2xs w-2/3 origin-left animate-pulse rounded-pill bg-coral/40" aria-hidden="true" /> : null}
    </button>
  );
}
