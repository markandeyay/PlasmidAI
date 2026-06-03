export default function Page() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-panel px-6 py-10 text-ink">
      <section className="w-full max-w-3xl border border-line bg-white p-8 shadow-subtle">
        <p className="text-sm font-semibold uppercase tracking-wide text-action">PlasmidAI</p>
        <h1 className="mt-3 text-3xl font-semibold">Describe a plasmid design</h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-700">
          The Phase 4 frontend scaffold is ready. The next slice wires the chat workflow,
          rendered plasmid map, and export controls to the local API.
        </p>
      </section>
    </main>
  );
}
