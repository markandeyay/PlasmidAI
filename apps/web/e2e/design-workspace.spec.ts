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
  // Exact match: the left sidebar now exposes a "New design" button whose
  // accessible name contains the substring "Design", which makes the composer
  // submit button ambiguous with the default substring match.
  await page.getByRole("button", { name: "Design", exact: true }).click();
  await expect(page.getByText("Generated annotated circular reporter plasmid.")).toBeVisible();
  await expect(page.getByText("Retrieved template evidence")).toBeVisible();
  await expect(page.getByText("curated:pEGFP-N1")).toBeVisible();
  await expect(page.getByTestId("seqviz-map")).toBeVisible();
  await expect(page.getByText("Accessible map summary")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Feature list" })).toBeVisible();
  await expect(page.getByText("Map could not render")).toBeHidden();
  await expect(page.getByRole("region", { name: "Feature list" }).getByText("CMV promoter", { exact: true })).toBeVisible();

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

test("small viewport keeps map, export, and outcome actions reachable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });

  await page.route("http://127.0.0.1:8000/v1/users/me/pending-outcome-prompts", async (route) => {
    await route.fulfill({ json: { prompts: [] } });
  });

  await page.route("http://127.0.0.1:8000/v1/sessions", async (route) => {
    await route.fulfill({ json: { session_id: "session-mobile" } });
  });

  await page.route("http://127.0.0.1:8000/v1/sessions/session-mobile/design", async (route) => {
    await route.fulfill({ json: { job_id: "job-mobile" } });
  });

  await page.route("http://127.0.0.1:8000/v1/jobs/job-mobile", async (route) => {
    await route.fulfill({
      json: {
        job_id: "job-mobile",
        status: "completed",
        result: {
          design_id: "design-mobile",
          recommendation_text: "Generated mobile-friendly annotated reporter plasmid.",
          annotated_sequence: annotatedSequence,
          retrieved_templates: [{ source_id: "curated:pEGFP-N1", name: "pEGFP-N1", score: 0.97 }]
        }
      }
    });
  });

  await page.route("http://127.0.0.1:8000/v1/designs/design-mobile/outcome", async (route) => {
    await route.fulfill({ status: 404, json: { error: { message: "Outcome not found" } } });
});

  await page.goto("/");
  await page.getByLabel("Experimental goal").fill("build a compact GFP reporter");
  await page.getByRole("button", { name: "Design" }).click();

  // The new mobile layout auto-switches to the Map tab when an annotated
  // sequence result lands (layout_redesign_v2.md §6). The chat result message
  // and "View plasmid map" link live on the Chat tab, so switch there to assert
  // the message and exercise the link's Map-tab hop.
  await page.getByRole("tab", { name: "Chat" }).click();
  await expect(page.getByText("Generated mobile-friendly annotated reporter plasmid.")).toBeVisible();

  await page.getByRole("link", { name: "View plasmid map" }).click();
  await expect(page.getByRole("heading", { name: "Plasmid map" })).toBeVisible();
  await expect(page.getByText("Accessible map summary")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Feature list" })).toBeVisible();
  await expect(page.getByText("Map could not render")).toBeHidden();
  await expect(page.getByRole("region", { name: "Export actions" })).toBeVisible();
  await expect(page.getByRole("button", { name: "GenBank" })).toBeVisible();

  await page.getByRole("button", { name: "Report outcome" }).click();
  await expect(page.getByRole("dialog").getByRole("heading", { name: "What happened in the lab?" })).toBeVisible();
});

test("seqviz content is not clipped at common laptop viewports", async ({ page }) => {
  await page.route("http://127.0.0.1:8000/v1/users/me/pending-outcome-prompts", async (route) => {
    await route.fulfill({ json: { prompts: [] } });
  });
  await page.route("http://127.0.0.1:8000/v1/sessions", async (route) => {
    await route.fulfill({ json: { session_id: "session-map-layout" } });
  });
  await page.route("http://127.0.0.1:8000/v1/sessions/session-map-layout/design", async (route) => {
    await route.fulfill({ json: { job_id: "job-map-layout" } });
  });
  await page.route("http://127.0.0.1:8000/v1/jobs/job-map-layout", async (route) => {
    await route.fulfill({
      json: {
        job_id: "job-map-layout",
        status: "succeeded",
        result: {
          design_id: "design-map-layout",
          recommendation_text: "Generated map layout fixture.",
          annotated_sequence: annotatedSequence,
          retrieved_templates: []
        }
      }
    });
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.getByLabel("Experimental goal").fill("build a map layout fixture");
  await page.getByRole("button", { name: "Design", exact: true }).click();
  await expect(page.getByTestId("seqviz-map")).toBeVisible();

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1280, height: 800 },
    { width: 1366, height: 768 }
  ]) {
    await page.setViewportSize(viewport);
    const metrics = await page.getByTestId("seqviz-map").evaluate((map) => {
      const visual = map.parentElement;
      const rect = map.getBoundingClientRect();
      return {
        width: rect.width,
        height: rect.height,
        mapClientHeight: map.clientHeight,
        mapScrollHeight: map.scrollHeight,
        visualClientHeight: visual?.clientHeight ?? 0,
        visualScrollHeight: visual?.scrollHeight ?? 0
      };
    });

    expect(metrics.width).toBeGreaterThan(500);
    expect(metrics.height).toBeGreaterThanOrEqual(400);
    expect(metrics.mapScrollHeight).toBeLessThanOrEqual(metrics.mapClientHeight + 2);
    expect(metrics.visualScrollHeight).toBeLessThanOrEqual(metrics.visualClientHeight + 2);
  }
});

test("completed job without sequence shows partial result evidence", async ({ page }) => {
  await page.route("http://127.0.0.1:8000/v1/users/me/pending-outcome-prompts", async (route) => {
    await route.fulfill({ json: { prompts: [] } });
  });

  await page.route("http://127.0.0.1:8000/v1/sessions", async (route) => {
    await route.fulfill({ json: { session_id: "session-partial" } });
  });

  await page.route("http://127.0.0.1:8000/v1/sessions/session-partial/design", async (route) => {
    await route.fulfill({ json: { job_id: "job-partial" } });
  });

  await page.route("http://127.0.0.1:8000/v1/jobs/job-partial", async (route) => {
    await route.fulfill({
      json: {
        job_id: "job-partial",
        status: "completed",
        result: {
          recommendation_text: "Found candidate templates, but the request needs another pass before sequence assembly.",
          annotated_sequence: null,
          retrieved_templates: [
            { source_id: "addgene:12345", name: "Template A", score: 0.91, source: "Addgene", vector_profile: "bacterial_expression" }
          ],
          validation_report: {
            overall: "WARN",
            checks: [{ name: "Assembly completeness", status: "WARN", message: "No annotated sequence returned." }]
          }
        }
      }
    });
  });

  await page.goto("/");
  await page.getByLabel("Experimental goal").fill("find a bacterial reporter template");
  await page.getByRole("button", { name: "Design", exact: true }).click();

  await expect(page.getByText("Found candidate templates, but the request needs another pass before sequence assembly.")).toBeVisible();
  await expect(page.getByText("Partial result")).toBeVisible();
  await expect(page.getByText("Retrieved template evidence")).toBeVisible();
  await expect(page.getByText("Template A")).toBeVisible();
  await expect(page.getByText("Assembly completeness")).toBeVisible();
  await expect(page.getByText("Submit a design to render the annotated plasmid.")).toBeVisible();
});

test("clarification question leads to a refinement and rendered design", async ({ page }) => {
  let refinementBody: { instruction: string } | null = null;

  await page.route("http://127.0.0.1:8000/v1/users/me/pending-outcome-prompts", async (route) => {
    await route.fulfill({ json: { prompts: [] } });
  });
  await page.route("http://127.0.0.1:8000/v1/sessions", async (route) => {
    await route.fulfill({ json: { session_id: "session-clarification" } });
  });
  await page.route("http://127.0.0.1:8000/v1/sessions/session-clarification/design", async (route) => {
    await route.fulfill({ json: { job_id: "job-clarification" } });
  });
  await page.route("http://127.0.0.1:8000/v1/sessions/session-clarification/refine", async (route) => {
    refinementBody = route.request().postDataJSON() as { instruction: string };
    await route.fulfill({ json: { job_id: "job-refined" } });
  });
  await page.route("http://127.0.0.1:8000/v1/jobs/*", async (route) => {
    const refined = route.request().url().endsWith("/job-refined");
    await route.fulfill({
      json: refined
        ? {
            job_id: "job-refined",
            status: "succeeded",
            result: {
              design_id: "design-clarified",
              recommendation_text: "Generated the clarified mammalian reporter design.",
              annotated_sequence: annotatedSequence,
              retrieved_templates: []
            }
          }
        : {
            job_id: "job-clarification",
            status: "succeeded",
            result: {
              design_id: null,
              design_spec: {
                clarification_needed: true,
                clarification_question: "Which mammalian cell line should this target?"
              },
              clarification_question: "Which mammalian cell line should this target?",
              annotated_sequence: null,
              retrieved_templates: []
            }
          }
    });
  });

  await page.goto("/");
  await page.getByLabel("Experimental goal").fill("make me a mammalian reporter");
  await page.getByRole("button", { name: "Design", exact: true }).click();

  await expect(page.getByText("To design this for you, I need to know: Which mammalian cell line should this target?")).toBeVisible();
  await expect(page.getByText("Waiting for your answer", { exact: true })).toBeVisible();
  await expect(page.getByText("Answer the clarification question to render the design map.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Answer" })).toBeVisible();

  await page.getByLabel("Experimental goal").fill("HEK293");
  await page.getByRole("button", { name: "Answer" }).click();

  expect(refinementBody).toEqual({ instruction: "HEK293" });
  await expect(page.getByText("Generated the clarified mammalian reporter design.")).toBeVisible();
  await expect(page.getByTestId("seqviz-map")).toBeVisible();
});

test("retryable model failure restores the prompt and offers try again", async ({ page }) => {
  await page.route("http://127.0.0.1:8000/v1/users/me/pending-outcome-prompts", async (route) => {
    await route.fulfill({ json: { prompts: [] } });
  });
  await page.route("http://127.0.0.1:8000/v1/sessions", async (route) => {
    await route.fulfill({ json: { session_id: "session-retry" } });
  });
  await page.route("http://127.0.0.1:8000/v1/sessions/session-retry/design", async (route) => {
    await route.fulfill({ json: { job_id: "job-unavailable" } });
  });
  await page.route("http://127.0.0.1:8000/v1/sessions/session-retry/refine", async (route) => {
    expect((route.request().postDataJSON() as { instruction: string }).instruction).toBe("build an ampicillin cloning vector");
    await route.fulfill({ json: { job_id: "job-retry-success" } });
  });
  await page.route("http://127.0.0.1:8000/v1/jobs/*", async (route) => {
    const succeeded = route.request().url().endsWith("/job-retry-success");
    await route.fulfill({
      json: succeeded
        ? {
            job_id: "job-retry-success",
            status: "succeeded",
            result: {
              design_id: "design-after-retry",
              recommendation_text: "Generated the design after retrying.",
              annotated_sequence: annotatedSequence,
              retrieved_templates: []
            }
          }
        : {
            job_id: "job-unavailable",
            status: "failed",
            result: null,
            error: "provider unavailable",
            error_detail: {
              code: "language_model_unavailable",
              message: "The language model is temporarily unavailable. Please try again in a moment.",
              retryable: true,
              details: {}
            }
          }
    });
  });

  await page.goto("/");
  await page.getByLabel("Experimental goal").fill("build an ampicillin cloning vector");
  await page.getByRole("button", { name: "Design", exact: true }).click();

  await expect(page.getByText("The language model is temporarily unavailable. Please try again in a moment.", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Experimental goal")).toHaveValue("build an ampicillin cloning vector");
  await page.getByRole("button", { name: "Try again" }).click();

  await expect(page.getByLabel("Conversation history").getByText("Generated the design after retrying.")).toBeVisible();
  await expect(page.getByTestId("seqviz-map")).toBeVisible();
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
