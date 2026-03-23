import puppeteer from 'puppeteer';
import fs from 'fs';

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
    fs.writeFileSync(`./results/${profileName}.txt`, html);
    
    console.log(`Saved results for ${profileName}`);
  } catch (error) {
    console.error(`Profile ${profileName} failed:`, error);
  } finally {
    await browser.close();
  }
}

// Run Profile A: "The Search Engine" (JS Enabled, 5s wait)
runExperiment('http://localhost:3000/ssr-version', 'Profile_A_SSR', true, 5000);

// Run Profile B: "The AI Agent" (JS Disabled, 2s wait)
runExperiment('http://localhost:3000/csr-version', 'Profile_B_CSR', false, 2000);