import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    viewport: { width: 1440, height: 1100 },
    launchOptions: {
      args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
    },
  },
  webServer: [
    {
      command: "uv run --locked python tests/web_server.py",
      cwd: "..",
      url: "http://127.0.0.1:8000/healthz",
      timeout: 60000,
      reuseExistingServer: false,
    },
    {
      command: "npm run build && npm run preview -- --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      timeout: 30000,
      reuseExistingServer: false,
    },
  ],
});
