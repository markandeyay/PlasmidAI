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

  await page.route("http://127.0.0.1:8000/v1/users/me/pending-outcome-prompts", async (route) => {
    await route.fulfill({ json: { prompts: [] } });
  });

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

test("researcher can submit a prompted outcome report", async ({ page }) => {
  let submittedOutcome: Record<string, unknown> | null = null;

  await page.route("http://127.0.0.1:8000/v1/users/me/pending-outcome-prompts", async (route) => {
    await route.fulfill({
      json: {
        prompts: [
          {
            design_id: "design-prompt-1",
            session_id: "session-prompt-1",
            created_at: "2026-06-01T12:00:00Z",
            days_since_created: 11
          }
        ]
      }
    });
  });

  await page.route("http://127.0.0.1:8000/v1/designs/design-prompt-1/outcome", async (route) => {
    const request = route.request();
    expect(request.headers()["x-user-id"]).toBe("web-demo-user");
    if (request.method() === "GET") {
      if (!submittedOutcome) {
        await route.fulfill({ status: 404, json: { error: { message: "Outcome not found" } } });
        return;
      }
      await route.fulfill({ json: { outcome_id: "outcome-1", report: submittedOutcome, created_at: submittedOutcome.reported_at } });
      return;
    }

    submittedOutcome = request.postDataJSON() as Record<string, unknown>;
    expect(submittedOutcome.design_id).toBe("design-prompt-1");
    expect(submittedOutcome.model_version).toBe("unknown-model");
    expect(submittedOutcome.construct_validated).toBe(true);
    expect(submittedOutcome.sequencing_result).toBe("Matches expected regions");
    expect(submittedOutcome.functional_result).toBe("Met expected function");
    expect(submittedOutcome.training_consent).toBe(true);
    expect(submittedOutcome.outcome_label).toBe("positive");
    expect(submittedOutcome.notes).toBe("Clone 2 matched expected reporter function.");
    expect(submittedOutcome.provenance).toMatchObject({
      reported_via: "web_pending_outcome_prompt",
      prompt_session_id: "session-prompt-1",
      prompt_days_since_created: 11,
      model_version_fallback: "unknown-model"
    });

    await route.fulfill({ json: { outcome_id: "outcome-1", report: submittedOutcome, created_at: submittedOutcome.reported_at } });
  });

  await page.goto("/");
  const prompt = page.getByLabel("Pending outcome prompt");
  await expect(prompt).toContainText("Design design-prompt-1 is ready for lab outcome feedback.");

  await prompt.getByRole("button", { name: "Report outcome" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: "What happened in the lab?" })).toBeVisible();
  await expect(dialog).toContainText("Design ID: design-prompt-1");
  await expect(dialog).toContainText("Model version: unknown-model");

  await dialog.getByLabel("What did you test?").selectOption("Delivered design exactly");
  await dialog.getByLabel("What sequence evidence do you have?").selectOption("Matches expected regions");
  await dialog.getByLabel("What happened in functional testing?").selectOption("Met expected function");
  await dialog.getByLabel("Based on the evidence above, what is your interpretation?").selectOption("Accepted for intended use");
  await dialog.getByLabel("Notes").fill("Clone 2 matched expected reporter function.");
  await dialog.getByRole("checkbox", { name: /I consent to this outcome report/ }).check();
  await dialog.getByRole("button", { name: "Submit outcome" }).click();

  await expect(dialog.getByRole("heading", { name: "Outcome submitted" })).toBeVisible();
  expect(submittedOutcome).not.toBeNull();
  await dialog.getByRole("button", { name: "Back to design" }).click();

  await expect(prompt).toBeHidden();
  await expect(page.getByRole("region", { name: "My reported outcomes" })).toContainText("design-prompt-1");
  await expect(page.getByRole("region", { name: "My reported outcomes" })).toContainText("positive");
});
