/**
 * Local captures for the CSR route → results/local-csr/
 *
 *   npm run index:local-csr
 *   npm run index:local-csr -- --url=http://localhost:3000/csr-version
 *
 * Defaults to http://localhost:3000/csr-version. Pass --wait-for-server to
 * poll until the dev server is up. Flags: --url=, --wait-for-server, --max-ms=, --step=
 */

import { parseCaptureArgs, runDeploymentCapture } from './deployment-capture';

async function main() {
  const args = parseCaptureArgs(
    ['LOCAL_CSR_URL', 'CAPTURE_CSR_URL'],
    '/csr-version',
  );
  await runDeploymentCapture({
    bundle: 'local-csr',
    targetUrl: args.url,
    waitForServer: args.waitForServer,
    maxMs: args.maxMs,
    stepMs: args.stepMs,
    logPrefix: '[local-csr-indexing]',
  });
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
