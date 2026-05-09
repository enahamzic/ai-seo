/**
 * Shared Puppeteer time-series capture for deployed CSR or SSR routes.
 * Outputs under results/{csr-results|ssr-results}/{baseline|model|constrained}/ms_<n>.txt
 */

import puppeteer, { type Browser, type Page } from 'puppeteer';
import fs from 'fs';
import path from 'path';

export const resultsDir = path.resolve(process.cwd(), 'results');

export const GOTO_TIMEOUT_MS = 120_000;
export const SERVER_POLL_MS = 2000;
export const SERVER_WAIT_MAX_MS = 120_000;

/** Default grid: 0 … 1000 ms in 20 ms steps (51 captures). */
export const STEP_MS = 20;
export const MAX_MS = 1000;

const MODEL_NETWORK_LATENCY_MS = Math.max(
  0,
  Number.parseInt(
    process.env.MODEL_NETWORK_LATENCY_MS ??
      process.env.MOBILE_CRAWLER_LATENCY_MS ??
      '200',
    10,
  ) || 200,
);

const MODEL_THROUGHPUT_BPS = 50 * 1024 * 1024;

const MOBILE_GOOGLEBOT_UA =
  'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Chrome/121.0.6167.85 Mobile Safari/537.36 ' +
  '(compatible; Googlebot/2.1; +http://www.google.com/bot.html)';

export type ScenarioKey = 'baseline' | 'model' | 'constrained';
export type CaptureBundle = 'csr-results' | 'ssr-results' | 'local-csr' | 'local-ssr';

export interface Scenario {
  key: ScenarioKey;
  label: string;
  enableJS: boolean;
  preparePage: (page: Page) => Promise<void>;
}

export const SCENARIOS: Scenario[] = [
  {
    key: 'baseline',
    label: 'Baseline',
    enableJS: true,
    preparePage: async (page) => {
      await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
    },
  },
  {
    key: 'model',
    label: 'Model',
    enableJS: true,
    preparePage: async (page) => {
      await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true });
      await page.setUserAgent(MOBILE_GOOGLEBOT_UA);
      const client = await page.createCDPSession();
      await client.send('Network.enable');
      await client.send('Network.emulateNetworkConditions', {
        offline: false,
        latency: MODEL_NETWORK_LATENCY_MS,
        downloadThroughput: MODEL_THROUGHPUT_BPS,
        uploadThroughput: MODEL_THROUGHPUT_BPS,
      });
    },
  },
  {
    key: 'constrained',
    label: 'Constrained',
    enableJS: false,
    preparePage: async (page) => {
      await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
    },
  },
];

export function buildSampleTimes(maxMs: number, stepMs: number): number[] {
  const times: number[] = [];
  for (let ms = 0; ms <= maxMs; ms += stepMs) {
    times.push(ms);
  }
  const last = times[times.length - 1];
  if (last !== maxMs) {
    times.push(maxMs);
  }
  return times;
}

export interface ParsedCaptureArgs {
  url: string;
  waitForServer: boolean;
  maxMs: number;
  stepMs: number;
}

export function parseCaptureArgs(urlEnvVars: string[], routeHint: string): ParsedCaptureArgs {
  let url = '';
  for (const k of urlEnvVars) {
    const v = process.env[k]?.trim();
    if (v) {
      url = v;
      break;
    }
  }
  let waitForServer = false;
  let maxMs = MAX_MS;
  let stepMs = STEP_MS;

  for (const arg of process.argv.slice(2)) {
    if (arg === '--wait-for-server') waitForServer = true;
    else if (arg.startsWith('--url=')) url = arg.slice('--url='.length).trim();
    else if (arg.startsWith('--max-ms='))
      maxMs = Math.max(0, parseInt(arg.slice('--max-ms='.length), 10) || MAX_MS);
    else if (arg.startsWith('--step='))
      stepMs = Math.max(1, parseInt(arg.slice('--step='.length), 10) || STEP_MS);
  }

  if (!url) {
    console.error(
      `Set one of: ${urlEnvVars.join(', ')} or pass --url=...`,
      `\nExample: --url=https://your-app.vercel.app${routeHint}`,
    );
    process.exit(1);
  }

  try {
    const u = new URL(url);
    if (u.protocol !== 'https:' && u.protocol !== 'http:') throw new Error('bad protocol');
  } catch {
    console.error(`Invalid URL: ${url}`);
    process.exit(1);
  }

  return { url, waitForServer, maxMs, stepMs };
}

export async function waitForReachable(
  url: string,
  maxWaitMs: number,
  logPrefix: string,
): Promise<void> {
  const start = Date.now();
  for (;;) {
    try {
      await fetch(url, { redirect: 'follow', signal: AbortSignal.timeout(15_000) });
      return;
    } catch {
      if (maxWaitMs === 0) {
        console.error(`${logPrefix} Cannot reach ${url}. Check the URL and deployment.`);
        process.exit(1);
      }
      if (Date.now() - start >= maxWaitMs) {
        console.error(`${logPrefix} Timeout waiting for ${url}`);
        process.exit(1);
      }
      console.log(`${logPrefix} Waiting for ${url} …`);
      await new Promise((r) => setTimeout(r, SERVER_POLL_MS));
    }
  }
}

async function captureOnce(
  targetUrl: string,
  scenario: Scenario,
  waitAfterGotoMs: number,
  outDir: string,
  logPrefix: string,
): Promise<boolean> {
  fs.mkdirSync(outDir, { recursive: true });

  let browser: Browser | undefined;
  try {
    browser = await puppeteer.launch({ headless: true });
    const context = await browser.createBrowserContext();
    try {
      const page = await context.newPage();

      await scenario.preparePage(page);
      await page.setJavaScriptEnabled(scenario.enableJS);

      await page.goto(targetUrl, {
        waitUntil: 'domcontentloaded',
        timeout: GOTO_TIMEOUT_MS,
      });

      await new Promise((r) => setTimeout(r, waitAfterGotoMs));

      const html = await page.content();
      const filename = `ms_${waitAfterGotoMs}.txt`;
      const outputPath = path.join(outDir, filename);
      fs.writeFileSync(outputPath, html);
      console.log(`${logPrefix} saved ${outputPath}`);
      return true;
    } finally {
      await context.close();
    }
  } catch (err) {
    console.error(
      `${logPrefix} FAILED scenario=${scenario.key} interval=${waitAfterGotoMs}ms`,
      err,
    );
    return false;
  } finally {
    if (browser) await browser.close();
  }
}

async function runScenario(
  captureRoot: string,
  targetUrl: string,
  scenario: Scenario,
  sampleMs: number[],
  logPrefix: string,
): Promise<{ saved: number; failed: number }> {
  const outDir = path.join(captureRoot, scenario.key);
  let saved = 0;
  let failed = 0;

  if (scenario.key === 'model') {
    console.log(
      `${logPrefix} model: CDP network latency +${MODEL_NETWORK_LATENCY_MS} ms RTT (env MODEL_NETWORK_LATENCY_MS or MOBILE_CRAWLER_LATENCY_MS)`,
    );
  }

  for (const ms of sampleMs) {
    console.log(`${logPrefix} scenario=${scenario.label} (${scenario.key}) interval=${ms}ms`);
    const ok = await captureOnce(targetUrl, scenario, ms, outDir, logPrefix);
    if (ok) saved += 1;
    else failed += 1;
  }

  console.log(
    `${logPrefix} ${scenario.key} done → ${outDir} (${saved} saved, ${failed} failed)`,
  );
  return { saved, failed };
}

export async function runDeploymentCapture(options: {
  bundle: CaptureBundle;
  targetUrl: string;
  waitForServer: boolean;
  maxMs: number;
  stepMs: number;
  logPrefix: string;
}): Promise<void> {
  const captureRoot = path.join(resultsDir, options.bundle);
  fs.mkdirSync(captureRoot, { recursive: true });

  await waitForReachable(
    options.targetUrl,
    options.waitForServer ? SERVER_WAIT_MAX_MS : 0,
    options.logPrefix,
  );

  const sampleMs = buildSampleTimes(options.maxMs, options.stepMs);

  console.log(`${options.logPrefix} Target: ${options.targetUrl}`);
  console.log(
    `${options.logPrefix} Output: ${captureRoot} ({baseline,model,constrained}/ms_<n>.txt)`,
  );
  console.log(
    `${options.logPrefix} Sample times (ms): ${sampleMs.join(', ')} (${sampleMs.length} per scenario)`,
  );

  let totalSaved = 0;
  let totalFailed = 0;

  for (const scenario of SCENARIOS) {
    const { saved, failed } = await runScenario(
      captureRoot,
      options.targetUrl,
      scenario,
      sampleMs,
      options.logPrefix,
    );
    totalSaved += saved;
    totalFailed += failed;
  }

  console.log(
    `${options.logPrefix} Finished: ${totalSaved} saved, ${totalFailed} failed → ${captureRoot}`,
  );
}
