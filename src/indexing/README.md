# Experiment README

## Bachelor Thesis

**Title:** *Evaluating the Impact of SSR and CSR Rendering on AI Search Optimization*

This document explains the experimental workflow used to quantify the **Visibility Gap** (also called a hydration-time semantic gap) between Server-Side Rendering (SSR) and Client-Side Rendering (CSR).

## 1) Project Overview

Modern AI-driven search systems (often discussed in the context of GEO, Generative Engine Optimization) rely on extracting semantically coherent text from crawled pages. If meaningful content is unavailable in the initial HTML payload, AI agents may index incomplete or noisy content.

- **SSR path (`/ssr-version`)**: delivers complete content in first response HTML.
- **CSR path (`/csr-version`)**: initially returns a loading state, then injects content after JavaScript execution.

The resulting delay is the operational **Hydration Gap / Visibility Gap**: a window where constrained crawlers can observe less semantic content than high-resource crawlers.

## 2) System Architecture

The experiment is structured in three layers:

1. **Application Layer (Next.js)**
   - Serves identical article content through two rendering strategies.
   - Routes:
     - SSR: `/ssr-version`
     - CSR: `/csr-version`
     - API: `/api/get-article`

2. **Observation Layer (Puppeteer)**
   - Script: `src/indexing/test-rendering.ts`
   - Simulates crawler capabilities by toggling JavaScript and wait budget.
   - Stores raw HTML captures in `results/`.

3. **Analysis Layer (Python + SBERT)**
   - Script: `src/analysis/analyze-seo.py`
   - Extracts readable text from captured HTML.
   - Computes cosine similarity between source article and each captured variant using SBERT embeddings.

## 3) Experimental Setup

### Agent Profiles

- **Profile A (Standard Crawler / High Resource)**
  - JavaScript: **Enabled**
  - Wait budget: **5 seconds**

- **Profile B (Constrained AI Agent)**
  - JavaScript: **Disabled**
  - Wait budget: **2 seconds**

### Full Matrix

| Variant | Profile | JS | Wait | Output |
|---|---|---|---:|---|
| SSR | A | Enabled | 5s | `results/Profile_A_SSR.txt` |
| SSR | B | Disabled | 2s | `results/Profile_B_SSR.txt` |
| CSR | A | Enabled | 5s | `results/Profile_A_CSR.txt` |
| CSR | B | Disabled | 2s | `results/Profile_B_CSR.txt` |

## 4) Key Results

Representative Semantic Fidelity scores (SBERT cosine similarity):

| Variant | Profile | Semantic Fidelity |
|---|---|---:|
| SSR | Profile A | ~0.98 |
| SSR | Profile B | ~0.98 |
| CSR | Profile A | ~0.98 |
| CSR | Profile B | **0.0644** |

Interpretation:

- SSR remains semantically stable for both crawler profiles.
- CSR is semantically recoverable for high-resource crawlers (Profile A).
- CSR collapses under constrained conditions (Profile B), empirically exposing the Visibility Gap.

## 5) Installation & Usage

### Prerequisites

- Node.js + npm
- Python 3.9+
- Local Chromium dependencies (handled by Puppeteer install)

### Install JavaScript dependencies

```bash
npm install
```

### Start the Next.js app

```bash
npm run dev
```

### Run rendering capture (Puppeteer)

```bash
npx tsx src/indexing/test-rendering.ts
```

### Install Python dependencies (analysis layer)

```bash
python3 -m pip install sentence-transformers beautifulsoup4
```

### Run semantic analysis

```bash
python3 src/analysis/analyze-seo.py
```

## 6) Technologies Used

- **Next.js 14** (project methodology target; repository currently runs Next.js `16.2.1` with equivalent Pages Router behavior)
- **TypeScript**
- **Puppeteer**
- **Python 3.9**
- **Sentence-Transformers** (`all-MiniLM-L6-v2`)
- **BeautifulSoup4**

## Notes

- Ensure `npm run dev` is active before running `test-rendering.ts`.
- The script auto-creates `results/` if missing.
- For reproducibility, keep article content and DOM structure identical across SSR and CSR variants.
