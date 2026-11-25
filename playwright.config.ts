import { existsSync } from "node:fs";
import { defineConfig } from "@playwright/test";

// Playwright can't download its own Chromium on Debian 11 (the dev container),
// so use the system Chromium installed with apt when it's there.
const systemChromium = "/usr/bin/chromium";

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/test-results",
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
    launchOptions: existsSync(systemChromium)
      ? { executablePath: systemChromium }
      : {},
  },
  webServer: [
    {
      command: "uv run -m uvicorn backend.main:app --port 8000",
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: true,
    },
    {
      command: "npx vite dashboard --port 5173 --strictPort",
      url: "http://localhost:5173",
      reuseExistingServer: true,
    },
  ],
});
