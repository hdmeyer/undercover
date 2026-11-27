import { defineConfig } from "@playwright/test";

const BACKEND_PORT = 8100;
const DASHBOARD_PORT = 5174;

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/test-results",
  reporter: "list",
  use: { baseURL: `http://localhost:${String(DASHBOARD_PORT)}` },
  webServer: [
    {
      command: `node e2e/reset-db.js && uv run -m uvicorn backend.main:app --port ${String(BACKEND_PORT)}`,
      url: `http://127.0.0.1:${String(BACKEND_PORT)}/api/health`,
      env: { DATABASE_PATH: "e2e/test.db" },
      reuseExistingServer: false,
    },
    {
      command: `npx vite dashboard --port ${String(DASHBOARD_PORT)} --strictPort`,
      url: `http://localhost:${String(DASHBOARD_PORT)}`,
      env: { API_PROXY: `http://127.0.0.1:${String(BACKEND_PORT)}` },
      reuseExistingServer: false,
    },
  ],
});
