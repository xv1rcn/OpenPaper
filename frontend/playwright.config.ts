import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8765",
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
  },
  webServer: {
    command: `${process.env.OPENPAPER_TEST_PYTHON || "../.venv/bin/python"} e2e/server.py`,
    url: "http://127.0.0.1:8765/api/ping",
    reuseExistingServer: false,
    timeout: 60000,
  },
});
