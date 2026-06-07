import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const repoRoot = path.resolve(__dirname, "../..");

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.full-stack.spec.ts",
  timeout: 30000,
  expect: {
    timeout: 10000
  },
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry"
  },
  webServer: [
    {
      command: "python -m uvicorn services.api.e2e_app:app --host 127.0.0.1 --port 8000",
      cwd: repoRoot,
      url: "http://127.0.0.1:8000/v1/metrics",
      reuseExistingServer: false,
      timeout: 120000
    },
    {
      command: "npm run dev",
      cwd: __dirname,
      env: {
        NEXT_PUBLIC_API_URL: "http://127.0.0.1:8000"
      },
      url: "http://127.0.0.1:3000",
      reuseExistingServer: false,
      timeout: 120000
    }
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
