/**
 * Production / deployment captures for the CSR route → results/csr-results/
 *
 *   export CAPTURE_CSR_URL="https://….vercel.app/csr-version"
 *   npm run index:csr
 *
 * Legacy env PRODUCTION_CSR_URL still works. Flags: --url=, --wait-for-server, --max-ms=, --step=
 */

import { parseCaptureArgs, runDeploymentCapture } from './deployment-capture';

async function main() {
  const args = parseCaptureArgs(['CAPTURE_CSR_URL', 'PRODUCTION_CSR_URL'], '/csr-version');
  await runDeploymentCapture({
    bundle: 'csr-results',
    targetUrl: args.url,
    waitForServer: args.waitForServer,
    maxMs: args.maxMs,
    stepMs: args.stepMs,
    logPrefix: '[csr-indexing]',
  });
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
