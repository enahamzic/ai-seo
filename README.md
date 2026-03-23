# Thesis Prototype: SSR vs CSR for AI Search Optimization

This project supports the thesis:

**"Evaluating the Impact of Server-Side and Client-Side Rendering on AI Search Optimization"**

It provides two pages with identical article content and styling, but different rendering strategies, so crawl visibility differences can be observed.

## Stack

- Next.js `16.2.1`
- React `19.2.4`
- Pages Router routes in `src/pages`

## Routes

- `/` → comparison landing page
- `/ssr-version` → **SSR** page using `getServerSideProps`
- `/csr-version` → **CSR** page with initial `Loading...`, then client fetch
- `/api/get-article` → API endpoint returning article JSON

## Project Structure

```text
data/
	articles.json
src/pages/
	index.js
	ssr-version.js
	csr-version.js
	article-shared.module.css
	api/
		get-article.js
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
