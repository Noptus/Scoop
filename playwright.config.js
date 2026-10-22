const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  use: { baseURL: 'http://127.0.0.1:8087' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 900 } } },
    { name: 'mobile', use: { viewport: { width: 360, height: 800 } } }
  ],
  webServer: {
    command: 'python3 -m http.server 8087 --bind 127.0.0.1',
    url: 'http://127.0.0.1:8087',
    reuseExistingServer: !process.env.CI
  }
});
