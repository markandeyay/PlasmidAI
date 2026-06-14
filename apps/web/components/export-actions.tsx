export type ExportFormat = "genbank" | "fasta";
export type ExportStatus = "idle" | "loading" | "success" | "error";

type ExportActionsProps = {
  designId: string | null;
  status: Record<ExportFormat, ExportStatus>;
  error: string | null;
  onExport: (format: ExportFormat) => Promise<void>;
};

export function ExportActions({ designId, status, error, onExport }: ExportActionsProps) {
  return (
    <section className="border border-line bg-white p-4 shadow-subtle" aria-label="Export actions">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Export</h2>
          <p className="mt-1 text-xs text-slate-600">
            {designId ? `Design ${designId}` : "Complete a design job to enable downloads."}
          </p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <ExportButton designId={designId} format="genbank" label="GenBank" status={status.genbank} onExport={onExport} />
        <ExportButton designId={designId} format="fasta" label="FASTA" status={status.fasta} onExport={onExport} />
      </div>
      {error ? <p className="mt-3 border border-red-200 bg-red-50 p-3 text-xs font-medium text-red-700">{error}</p> : null}
      {status.genbank === "success" || status.fasta === "success" ? (
        <p className="mt-3 border border-action/40 bg-action/10 p-3 text-xs font-semibold text-action">Download started.</p>
      ) : null}
    </section>
  );
}

function ExportButton({
  designId,
  format,
  label,
  status,
  onExport
}: {
  designId: string | null;
  format: ExportFormat;
  label: string;
  status: ExportStatus;
  onExport: (format: ExportFormat) => Promise<void>;
}) {
  const loading = status === "loading";
  return (
    <button
      type="button"
      disabled={!designId || loading}
      onClick={() => void onExport(format)}
      className="border border-action bg-white px-3 py-2 text-sm font-semibold text-action hover:bg-action/5 focus:border-action focus:outline-none focus:ring-2 focus:ring-action/20 disabled:cursor-not-allowed disabled:border-slate-300 disabled:text-slate-400 disabled:hover:bg-white"
    >
      {loading ? "Preparing..." : status === "success" ? `${label} ready` : label}
    </button>
  );
}
