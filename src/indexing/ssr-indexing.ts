/**
 * Production / deployment captures for the SSR route → results/ssr-results/
 *
 *   export CAPTURE_SSR_URL="https://….vercel.app/ssr-version"
 *   npm run index:ssr
 *
 * Same three scenarios (baseline, model, constrained) for side-by-side analysis.
 * Flags: --url=, --wait-for-server, --max-ms=, --step=
 */

import { parseCaptureArgs, runDeploymentCapture } from './deployment-capture';

async function main() {
  const args = parseCaptureArgs(['CAPTURE_SSR_URL'], '/ssr-version');
  await runDeploymentCapture({
    bundle: 'ssr-results',
    targetUrl: args.url,
    waitForServer: args.waitForServer,
    maxMs: args.maxMs,
    stepMs: args.stepMs,
    logPrefix: '[ssr-indexing]',
  });
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
