import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';

const resultsDir = path.resolve(process.cwd(), 'results');
const timeseriesDir = path.join(resultsDir, 'timeseries');
const CSR_URL = 'http://localhost:3000/csr-version';
/** Local CSR time-series: 0 … 1000 ms, every 20 ms (51 captures). */
const LOCAL_TIMESERIES_MAX_MS = 1000;
const LOCAL_TIMESERIES_STEP_MS = 20;
const GOTO_TIMEOUT_MS = 60_000;
const SERVER_POLL_INTERVAL_MS = 2000;
const SERVER_WAIT_MAX_MS = 120_000;

fs.mkdirSync(resultsDir, { recursive: true });

/** TCP reached; any HTTP status counts (500 still means the server is listening). */
async function waitForDevServer(url: string, maxWaitMs: number): Promise<void> {
  const start = Date.now();
  for (;;) {
    try {
      await fetch(url, { redirect: 'follow', signal: AbortSignal.timeout(8000) });
      return;
    } catch {
      if (maxWaitMs === 0) {
        console.error(
          `[time-series] Cannot reach ${url} (nothing listening or timeout).`,
          'Start the app first (e.g. npm run dev), then re-run.',
          'Or pass --wait-for-server to poll for up to 2 minutes.',
        );
        process.exit(1);
      }
      if (Date.now() - start >= maxWaitMs) {
        console.error(
          `[time-series] Server did not become reachable within ${maxWaitMs}ms: ${url}`,
        );
        process.exit(1);
      }
      console.log(`[time-series] Waiting for dev server… ${url}`);
      await new Promise((r) => setTimeout(r, SERVER_POLL_INTERVAL_MS));
    }
  }
}

export type GotoWaitUntil = 'load' | 'domcontentloaded' | 'networkidle0';

/**
 * Single capture: fresh browser per call (no shared cache).
 * After `page.goto` resolves with the chosen `waitUntil`, waits `waitTimeMs` then saves HTML.
 *
 * Note: `networkidle0` waits until **all** network activity stops. For `/csr-version` that
 * includes `/api/get-article`, so the article is already in the DOM — extra milliseconds
 * change nothing and SBERT scores stay flat. Use `domcontentloaded` for time-series TTSC.
 */
async function runExperiment(
  url: string,
  profileName: string,
  enableJS: boolean,
  waitTimeMs: number,
  outputDir: string = resultsDir,
  gotoWaitUntil: GotoWaitUntil = 'networkidle0',
): Promise<boolean> {
  fs.mkdirSync(outputDir, { recursive: true });

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  await page.setJavaScriptEnabled(enableJS);

  try {
    await page.goto(url, {
      waitUntil: gotoWaitUntil,
      timeout: GOTO_TIMEOUT_MS,
    });

    await new Promise((resolve) => setTimeout(resolve, waitTimeMs));

    const html = await page.content();
    const outputPath = path.join(outputDir, `${profileName}.txt`);
    fs.writeFileSync(outputPath, html);

    console.log(`Saved: ${outputPath}`);
    return true;
  } catch (error) {
    console.error(`Capture failed (${profileName}):`, error);
    return false;
  } finally {
    await browser.close();
  }
}

/** High-resolution time-series DOM snapshots for the CSR route (visibility gap). */
async function runCsrTimeSeriesBatch(waitForServer: boolean) {
  await waitForDevServer(CSR_URL, waitForServer ? SERVER_WAIT_MAX_MS : 0);

  fs.mkdirSync(timeseriesDir, { recursive: true });

  console.log(
    `[time-series] Schedule: 0–${LOCAL_TIMESERIES_MAX_MS} ms every ${LOCAL_TIMESERIES_STEP_MS} ms → results/timeseries/csr_wait_<n>ms.txt`,
  );

  let saved = 0;
  let failed = 0;
  for (let ms = 0; ms <= LOCAL_TIMESERIES_MAX_MS; ms += LOCAL_TIMESERIES_STEP_MS) {
    const profile = `csr_wait_${ms}ms`;
    console.log(
      `[time-series] Capturing ${CSR_URL} — domcontentloaded + ${ms}ms → ${profile}.txt`,
    );
    const ok = await runExperiment(
      CSR_URL,
      profile,
      true,
      ms,
      timeseriesDir,
      'domcontentloaded',
    );
    if (ok) saved += 1;
    else failed += 1;
  }

  console.log(
    `[time-series] Finished: ${saved} saved, ${failed} failed → ${timeseriesDir}`,
  );
}

async function main() {
  const waitForServer = process.argv.includes('--wait-for-server');
  await runCsrTimeSeriesBatch(waitForServer);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});

// --- Previous experimental matrix (uncomment to run alongside / instead of time-series) ---
//
// async function runLegacyMatrix() {
//   await runExperiment('http://localhost:3000/ssr-version', 'Profile_A_SSR', true, 5000);
//   await runExperiment('http://localhost:3000/ssr-version', 'Profile_B_SSR', false, 2000);
//   await runExperiment('http://localhost:3000/csr-version', 'Profile_A_CSR', true, 5000);
//   await runExperiment('http://localhost:3000/csr-version', 'Profile_B_CSR', false, 2000);
// }
