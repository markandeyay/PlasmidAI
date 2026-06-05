import { expect, test } from "@playwright/test";

const annotatedSequence = {
  sequence: "atgc".repeat(300),
  topology: "circular",
  annotation_complete: true,
  vector_profile: "mammalian_reporter_vector",
  features: [
    { start: 0, end: 180, type: "promoter", strand: 1, name: "CMV promoter", confidence: 0.95 },
    { start: 210, end: 780, type: "GOI", strand: 1, name: "EGFP", confidence: 0.98 },
    { start: 820, end: 980, type: "terminator", strand: 1, name: "SV40 polyA", confidence: 0.91 },
    { start: 1000, end: 1160, type: "ORI", strand: 1, name: "pUC origin", confidence: 0.93 }
  ]
};

test("researcher can design, refine, view map, and export files", async ({ page }) => {
  const requests: string[] = [];
  let jobPolls = 0;

  await page.route("http://127.0.0.1:8000/v1/sessions", async (route) => {
    requests.push("POST /v1/sessions");
    await route.fulfill({ json: { session_id: "session-1" } });
  });

  await page.route("http://127.0.0.1:8000/v1/sessions/session-1/design", async (route) => {
    const body = route.request().postDataJSON() as { goal: string };
    expect(body.goal).toBe("build a GFP reporter");
    requests.push("POST /v1/sessions/session-1/design");
    await route.fulfill({ json: { job_id: "job-1" } });
  });

  await page.route("http://127.0.0.1:8000/v1/sessions/session-1/refine", async (route) => {
    const body = route.request().postDataJSON() as { instruction: string };
    expect(body.instruction).toBe("switch the backbone to pLenti-CMV");
    requests.push("POST /v1/sessions/session-1/refine");
    await route.fulfill({ json: { job_id: "job-2" } });
  });

  await page.route("http://127.0.0.1:8000/v1/jobs/*", async (route) => {
    const url = route.request().url();
    jobPolls += 1;
    requests.push(`GET ${new URL(url).pathname}`);
    const isRefine = url.endsWith("/job-2");
    await route.fulfill({
      json: {
        job_id: isRefine ? "job-2" : "job-1",
        status: "completed",
        result: {
          design_id: "design-1",
          recommendation_text: isRefine
            ? "Refined design completed with the lentiviral backbone request captured."
            : "Generated annotated circular reporter plasmid.",
          annotated_sequence: annotatedSequence,
          retrieved_templates: [{ source_id: "curated:pEGFP-N1", name: "pEGFP-N1", score: 0.97 }]
        }
      }
    });
  });

  await page.route("http://127.0.0.1:8000/v1/designs/design-1/export?format=genbank", async (route) => {
    requests.push("GET /v1/designs/design-1/export?format=genbank");
    await route.fulfill({
      body: "LOCUS       design-1 1200 bp DNA circular\nORIGIN\n//\n",
      contentType: "application/genbank"
    });
  });

  await page.route("http://127.0.0.1:8000/v1/designs/design-1/export?format=fasta", async (route) => {
    requests.push("GET /v1/designs/design-1/export?format=fasta");
    await route.fulfill({ body: ">design-1\nATGC\n", contentType: "text/plain" });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Design workspace" })).toBeVisible();

  await page.getByLabel("Experimental goal").fill("build a GFP reporter");
  await page.getByRole("button", { name: "Design" }).click();
  await expect(page.getByText("Generated annotated circular reporter plasmid.")).toBeVisible();
  await expect(page.getByTestId("seqviz-map")).toBeVisible();
  await expect(page.getByText("CMV promoter")).toBeVisible();

  await page.getByLabel("Experimental goal").fill("switch the backbone to pLenti-CMV");
  await page.getByRole("button", { name: "Refine" }).click();
  await expect(page.getByText("Refined design completed with the lentiviral backbone request captured.")).toBeVisible();

  const genbankDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "GenBank" }).click();
  expect((await genbankDownload).suggestedFilename()).toBe("design-1.gb");

  const fastaDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "FASTA" }).click();
  expect((await fastaDownload).suggestedFilename()).toBe("design-1.fasta");

  expect(requests.filter((request) => request === "POST /v1/sessions")).toHaveLength(1);
  expect(requests).toContain("POST /v1/sessions/session-1/design");
  expect(requests).toContain("POST /v1/sessions/session-1/refine");
  expect(jobPolls).toBeGreaterThanOrEqual(2);
  expect(requests).toContain("GET /v1/designs/design-1/export?format=genbank");
  expect(requests).toContain("GET /v1/designs/design-1/export?format=fasta");
});
