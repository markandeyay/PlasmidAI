type ExportActionsProps = {
  designId: string | null;
  onExport: (format: "genbank" | "fasta") => Promise<void>;
};

export function ExportActions({ designId, onExport }: ExportActionsProps) {
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
        <button
          type="button"
          disabled={!designId}
          onClick={() => void onExport("genbank")}
          className="border border-line px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-slate-400"
        >
          GenBank
        </button>
        <button
          type="button"
          disabled={!designId}
          onClick={() => void onExport("fasta")}
          className="border border-line px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-slate-400"
        >
          FASTA
        </button>
      </div>
    </section>
  );
}
