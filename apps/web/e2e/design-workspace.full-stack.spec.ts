import { expect, test } from "@playwright/test";

test("researcher completes a real API-backed design and export journey", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Design workspace" })).toBeVisible();

  await page.getByLabel("Experimental goal").fill("build a deterministic E2E GFP reporter");
  await page.getByRole("button", { name: "Design", exact: true }).click();

  await expect(page.getByText("Generated deterministic full-stack E2E reporter plasmid.")).toBeVisible();
  await expect(page.getByText("Retrieved template evidence")).toBeVisible();
  await expect(page.getByText("curated:e2e-template")).toBeVisible();
  await expect(page.getByTestId("seqviz-map")).toBeVisible();
  await expect(page.getByText("CMV promoter")).toBeVisible();
  await expect(page.getByText("Sequence assembly")).toBeVisible();

  const genbankDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "GenBank" }).click();
  expect((await genbankDownload).suggestedFilename()).toBe("e2e-design.gb");
});
