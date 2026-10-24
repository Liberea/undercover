import { defineConfig } from "@playwright/test";

// The tests change claims, so they get their own backend on a fresh database
// and their own dashboard, apart from the dev servers on 8000 and 5173.
export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/test-results",
  reporter: "list",
  use: { baseURL: "http://localhost:5180" },
  webServer: [
    {
      command:
        "uv run -m backend.seed && uv run -m uvicorn backend.main:app --port 8100",
      env: { UNDERCOVER_DB: "e2e/e2e.db" },
      url: "http://127.0.0.1:8100/api/health",
      reuseExistingServer: false,
    },
    {
      command: "npx vite dashboard --port 5180 --strictPort",
      env: { BACKEND_URL: "http://127.0.0.1:8100" },
      url: "http://localhost:5180",
      reuseExistingServer: false,
    },
  ],
});
