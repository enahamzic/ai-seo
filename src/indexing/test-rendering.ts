import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';

const resultsDir = path.resolve(process.cwd(), 'results');
fs.mkdirSync(resultsDir, { recursive: true });

async function runExperiment(url: string, profileName: string, enableJS: boolean, waitTime: number) {
  // 1. Launch the browser
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  // 2. Set Profile Constraints
  await page.setJavaScriptEnabled(enableJS);

  try {
    // 3. Navigate to your local Next.js page
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 10000 });

    // 4. Wait for the specific "Visibility Gap" time defined in your thesis
    await new Promise(resolve => setTimeout(resolve, waitTime));

    // 5. Capture the resulting HTML
    const html = await page.content();
    const outputPath = path.join(resultsDir, `${profileName}.txt`);
    fs.writeFileSync(outputPath, html);
    
    console.log(`Saved results for ${profileName}`);
  } catch (error) {
    console.error(`Profile ${profileName} failed:`, error);
  } finally {
    await browser.close();
  }
}

// --- THE FULL EXPERIMENTAL MATRIX ---

// 1. SSR + Profile A (High Resource)
runExperiment('http://localhost:3000/ssr-version', 'Profile_A_SSR', true, 5000);

// 2. SSR + Profile B (Constrained Agent)
runExperiment('http://localhost:3000/ssr-version', 'Profile_B_SSR', false, 2000);

// 3. CSR + Profile A (High Resource - Should eventually render)
runExperiment('http://localhost:3000/csr-version', 'Profile_A_CSR', true, 5000);

// 4. CSR + Profile B (Constrained Agent - The "Visibility Gap" target)
runExperiment('http://localhost:3000/csr-version', 'Profile_B_CSR', false, 2000);