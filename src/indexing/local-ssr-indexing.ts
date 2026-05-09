/**
 * Local captures for the SSR route → results/local-ssr/
 *
 *   npm run index:local-ssr
 *   npm run index:local-ssr -- --url=http://localhost:3000/ssr-version
 *
 * Defaults to http://localhost:3000/ssr-version. Pass --wait-for-server to
 * poll until the dev server is up. Flags: --url=, --wait-for-server, --max-ms=, --step=
 */

import { parseCaptureArgs, runDeploymentCapture } from './deployment-capture';

async function main() {
  const args = parseCaptureArgs(
    ['LOCAL_SSR_URL', 'CAPTURE_SSR_URL'],
    '/ssr-version',
  );
  await runDeploymentCapture({
    bundle: 'local-ssr',
    targetUrl: args.url,
    waitForServer: args.waitForServer,
    maxMs: args.maxMs,
    stepMs: args.stepMs,
    logPrefix: '[local-ssr-indexing]',
  });
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
