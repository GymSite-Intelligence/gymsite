const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  page.on('pageerror', err => {
    errors.push(err.message);
  });

  await page.goto('http://localhost:5175/dashboard');
  await page.waitForTimeout(10000);

  console.log('CONSOLE_ERRORS:', JSON.stringify(errors, null, 2));
  await browser.close();
})();
