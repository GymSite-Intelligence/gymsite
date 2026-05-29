const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

// Mock API on port 8000
const mockApi = http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
    res.end(JSON.stringify({ status: 'ok', service: 'gymsite-api' }));
  } else {
    res.writeHead(404);
    res.end();
  }
});
mockApi.listen(8000, () => console.log('Mock API on 8000'));

// Static server on port 5175 with SPA fallback
const distDir = path.join(__dirname, '..', 'dist');
const staticServer = http.createServer((req, res) => {
  const filePath = path.join(distDir, req.url === '/' ? 'index.html' : req.url);
  fs.readFile(filePath, (err, data) => {
    if (err) {
      fs.readFile(path.join(distDir, 'index.html'), (err2, data2) => {
        if (err2) {
          res.writeHead(404);
          res.end('Not found');
        } else {
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(data2);
        }
      });
    } else {
      const ext = path.extname(filePath);
      const ct = ext === '.js' ? 'application/javascript' : ext === '.css' ? 'text/css' : 'application/octet-stream';
      res.writeHead(200, { 'Content-Type': ct });
      res.end(data);
    }
  });
});
staticServer.listen(5175, () => console.log('Static server on 5175'));

(async () => {
  await new Promise(r => setTimeout(r, 1000));
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('http://localhost:5175/dashboard');
  await page.waitForTimeout(10000);

  console.log('CONSOLE_ERRORS:', JSON.stringify(errors, null, 2));
  await browser.close();
  mockApi.close();
  staticServer.close();
  process.exit(errors.length > 0 ? 1 : 0);
})();
