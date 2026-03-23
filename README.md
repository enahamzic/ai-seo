# Thesis Prototype: SSR vs CSR for AI Search Optimization

This project supports the thesis:

**"Evaluating the Impact of Server-Side and Client-Side Rendering on AI Search Optimization"**

It provides two pages with identical article content and styling, but different rendering strategies, so crawl visibility differences can be observed.

## Stack

- Next.js `16.2.1`
- React `19.2.4`
- Pages Router routes in `src/pages`
- Puppeteer `^24.40.0` for automated rendering experiments

## Routes

- `/` → comparison landing page
- `/ssr-version` → **SSR** page using `getServerSideProps`
- `/csr-version` → **CSR** page with initial `Loading...`, then client fetch
- `/api/get-article` → API endpoint returning article JSON

## Project Structure

```text
data/
	articles.json
src/
	indexing/
		test-rendering.ts
	pages/
		index.js
		ssr-version.js
		csr-version.js
		article-shared.module.css
		api/
			get-article.js
results/
	(output from test-rendering.ts, gitignore recommended)
```

## How It Works

### SSR version (`/ssr-version`)

- Reads `data/articles.json` at request time in `getServerSideProps`
- Renders full headings, paragraphs, and lists in the initial HTML
- Supports immediate content visibility for non-JS crawlers

### CSR version (`/csr-version`)

- Starts with a loading state (`Loading...`)
- Fetches `/api/get-article` in `useEffect` after browser mount
- Introduces a visibility gap until JavaScript executes

### Shared visual parity

- Both pages use `src/pages/article-shared.module.css`
- DOM hierarchy and visual structure are intentionally kept equivalent

## Run Locally

```bash
npm install
npm run dev
```

Open:

- `http://localhost:3000/`
- `http://localhost:3000/ssr-version`
- `http://localhost:3000/csr-version`
- `http://localhost:3000/api/get-article`

## Quick Validation

Run lint:

```bash
npm run lint -- src/pages/index.js src/pages/ssr-version.js src/pages/csr-version.js src/pages/api/get-article.js
```

## Notes for Experimentation

- Keep article content identical across both versions when iterating.
- If measuring crawler behavior, record first-response HTML and time-to-content for each route.

## Puppeteer Experiment (`src/indexing/test-rendering.ts`)

`test-rendering.ts` automates two crawler profiles against your local dev server and saves the resulting HTML snapshots to `./results/`.

| Profile | Route | JS enabled | Wait time | Output file |
|---|---|---|---|---|
| A – Search Engine | `/ssr-version` | ✅ | 5 s | `Profile_A_SSR.txt` |
| B – AI Agent | `/csr-version` | ❌ | 2 s | `Profile_B_CSR.txt` |

**Profile A** simulates a crawler that executes JavaScript and waits for network idle — equivalent to Googlebot's second-wave rendering.

**Profile B** simulates a lightweight AI agent that fetches raw HTML without running JavaScript, exposing the CSR visibility gap.

### Prerequisites

Make sure the dev server is running before executing the script:

```bash
npm run dev
```

### Run the experiment

```bash
npx ts-node src/indexing/test-rendering.ts
```

Or compile first and run with Node:

```bash
npx tsc src/indexing/test-rendering.ts --outDir dist --esModuleInterop --skipLibCheck
node dist/indexing/test-rendering.js
```

Results land in `./results/`. Add that folder to `.gitignore` if you don't want raw HTML snapshots committed:

```bash
echo "results/" >> .gitignore
```
