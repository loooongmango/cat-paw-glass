// Frame-by-frame capture of index.html for README GIFs.
// usage: node capture.js <index.html> <outDir>
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const PAGE = 'file://' + path.resolve(process.argv[2]);
const OUT = path.resolve(process.argv[3]);

// Google Fonts is unreachable from this machine: map the page's families to local stand-ins.
const FONT_CSS = `
@font-face{font-family:'Anton';src:local('Inter Display Black'),local('InterDisplay-Black');}
@font-face{font-family:'IBM Plex Mono';font-weight:400;src:local('DejaVu Sans Mono'),local('DejaVuSansMono');}
@font-face{font-family:'IBM Plex Mono';font-weight:500;src:local('DejaVu Sans Mono'),local('DejaVuSansMono');}
@font-face{font-family:'Noto Sans SC';font-weight:300;src:local('Noto Sans CJK SC Light'),local('NotoSansCJKsc-Light');}
@font-face{font-family:'Noto Sans SC';font-weight:400;src:local('Noto Sans CJK SC'),local('NotoSansCJKsc-Regular');}
@font-face{font-family:'Noto Sans SC';font-weight:500;src:local('Noto Sans CJK SC Medium'),local('NotoSansCJKsc-Medium');}
`;

function hhmmss(sec) {
  const s = Math.floor(sec) % 86400;
  const p = (n) => String(n).padStart(2, '0');
  return p(Math.floor(s / 3600)) + ':' + p(Math.floor(s / 60) % 60) + ':' + p(s % 60);
}

async function shoot(browser, job) {
  const ctx = await browser.newContext({ viewport: job.viewport, deviceScaleFactor: job.dsf });
  const page = await ctx.newPage();
  await page.route(/fonts\.googleapis\.com/, (r) => r.fulfill({ status: 200, contentType: 'text/css', body: FONT_CSS }));
  await page.route(/fonts\.gstatic\.com/, (r) => r.abort());
  await page.goto(PAGE);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(800);
  // freeze: stop the live clock and pause every CSS animation on one shared timeline
  await page.evaluate(() => {
    for (let i = 1; i < 5000; i++) { clearInterval(i); clearTimeout(i); }
    document.getAnimations().forEach((a) => a.pause());
  });
  const dir = path.join(OUT, job.name);
  fs.mkdirSync(dir, { recursive: true });
  const n = Math.round(job.seconds * job.fps);
  for (let f = 0; f < n; f++) {
    const t = job.t0 + f / job.fps;
    await page.evaluate(({ ms, clock }) => {
      document.getAnimations().forEach((a) => { a.currentTime = ms; });
      const c = document.getElementById('clock');
      if (c) c.textContent = clock;
    }, { ms: t * 1000, clock: hhmmss(job.clockBase + f / job.fps) });
    await page.screenshot({ path: path.join(dir, String(f).padStart(4, '0') + '.png'), clip: job.clip });
  }
  await ctx.close();
  console.log(job.name, n, 'frames');
}

(async () => {
  const browser = await chromium.launch();
  const jobs = (process.argv[4] || 'hero,knead').split(',');
  if (jobs.includes('hero')) {
    // 9 s loop + 1 s extra for the crossfade seam
    await shoot(browser, { name: 'hero', viewport: { width: 1440, height: 900 }, dsf: 1, t0: 69.5, seconds: 10, fps: 12, clockBase: 21 * 3600 + 47 * 60 + 12 });
  }
  if (jobs.includes('knead')) {
    // both kneading paws share a 12 s period, so 12 s loops exactly
    await shoot(browser, { name: 'knead', viewport: { width: 2000, height: 1000 }, dsf: 2, t0: 0, seconds: 12, fps: 15, clockBase: 0,
      clip: { x: 1238, y: 70, width: 560, height: 420 } });
  }
  await browser.close();
})();
