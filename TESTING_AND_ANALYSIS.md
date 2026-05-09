# Testing and Analysis Workflow

This document describes the complete indexing and analysis pipeline for comparing how rendering strategy (SSR vs CSR) affects AI search visibility.

## Project Structure

```
src/
├── indexing/
│   ├── csr-indexing.ts              # Production CSR captures
│   ├── ssr-indexing.ts              # Production SSR captures
│   ├── local-csr-indexing.ts        # Local dev CSR captures
│   ├── local-ssr-indexing.ts        # Local dev SSR captures
│   ├── deployment-capture.ts        # Shared capture logic
│   └── README.md
└── analysis/
    ├── production-csr/
    │   └── production_analysis.py    # Analyzes production CSR results
    ├── production-ssr/
    │   └── production_analysis.py    # Analyzes production SSR results
    └── local/
        ├── local_csr_analysis.py     # Analyzes local CSR results
        ├── local_ssr_analysis.py     # Analyzes local SSR results
        ├── analyze_ttsc.py           # TTSC analysis for local timeseries
        └── analyze-seo.py            # SEO extraction analysis

results/
├── csr-results/                 # Production CSR snapshots
│   ├── baseline/
│   ├── model/
│   └── constrained/
├── ssr-results/                 # Production SSR snapshots
│   ├── baseline/
│   ├── model/
│   └── constrained/
├── local-csr/                   # Local dev CSR snapshots
│   ├── baseline/
│   ├── model/
│   └── constrained/
├── local-ssr/                   # Local dev SSR snapshots
│   ├── baseline/
│   ├── model/
│   └── constrained/
├── timeseries/                  # Deprecated; use local results
└── analysis/
    ├── csr-production/          # Production CSR analysis outputs
    ├── ssr-production/          # Production SSR analysis outputs
    ├── csr-local/               # Local CSR analysis outputs
    └── ssr-local/               # Local SSR analysis outputs
```

## Configuration

### Environment Variables (`.env.local`)

Set your deployment URLs and optional local overrides:

```dotenv
# Production Deployment URLs
CAPTURE_CSR_URL=https://your-csr-deployment.vercel.app/csr-version
CAPTURE_SSR_URL=https://your-ssr-deployment.vercel.app/ssr-version

# Local Dev Server URLs (optional; defaults to localhost:3000)
LOCAL_CSR_URL=http://localhost:3000/csr-version
LOCAL_SSR_URL=http://localhost:3000/ssr-version
```

The `.env.local` file is **git-ignored** for security.

## Capture Scenarios

Each capture runs three scenarios:

| Scenario | Description | Viewport |
|---|---|---|
| **baseline** | Desktop; JavaScript enabled; no throttling | 1280×720 |
| **model** | Mobile; JavaScript enabled; CDP network throttling (Googlebot-like latency) | 390×844 (2× DPR), Mobile User-Agent |
| **constrained** | Desktop; JavaScript disabled | 1280×720 |

Network throttling for `model` scenario uses:
- Latency: `MODEL_NETWORK_LATENCY_MS` (default: 200ms, can be overridden via env)
- Download/Upload: 50 Mbps

## Indexing Workflow

### 1. Production CSR Indexing

Captures the client-side rendered Vercel deployment:

```bash
npm run index:csr
```

**Output:** `results/csr-results/{baseline,model,constrained}/ms_*.txt`

**Optional flags:**
- `--url=https://custom-url.com/csr-version` — Override CAPTURE_CSR_URL
- `--wait-for-server` — Poll until deployment is reachable (useful for fresh deploys)
- `--max-ms=500 --step=10` — Custom time ranges (default: 0–1000 ms in 20 ms steps)

### 2. Production SSR Indexing

Captures the server-side rendered Vercel deployment:

```bash
npm run index:ssr
```

**Output:** `results/ssr-results/{baseline,model,constrained}/ms_*.txt`

**Same flags as CSR indexing.**

### 3. Local CSR Indexing

Captures the dev server's CSR route (requires `npm run dev` running):

```bash
npm run index:local-csr
```

**Output:** `results/local-csr/{baseline,model,constrained}/ms_*.txt`

**Important:** Local captures have **no real network delay**, so CSR hydration appears instantaneous. Use production captures for timing experiments.

### 4. Local SSR Indexing

Captures the dev server's SSR route:

```bash
npm run index:local-ssr
```

**Output:** `results/local-ssr/{baseline,model,constrained}/ms_*.txt`

## Analysis Workflow

Each analysis script reads from its corresponding capture folder and outputs results to a subfolder under `results/analysis/`.

### Production Analysis — CSR

```bash
python3 src/analysis/production-csr/production_analysis.py
```

**Inputs:**
- Ground truth: `data/source_article.json` (or fallback: `data/articles.json`)
- Snapshots: `results/csr-results/{baseline,model,constrained}/ms_*.txt`

**Outputs to:** `results/analysis/csr-production/`
- `production_metrics_summary.csv` — TTSC per scenario
- `production_ttsc_*.png` — Charts

**Optional arguments:**
```bash
python3 src/analysis/production-csr/production_analysis.py \
  --capture-root results/csr-results \
  --ground-truth data/source_article.json \
  --output-dir results/analysis/csr-production \
  --threshold 0.5 \
  --prefix "csr" \
  --plot-title-tag "CSR Production"
```

### Production Analysis — SSR

```bash
python3 src/analysis/production-ssr/production_analysis.py
```

**Inputs:**
- Ground truth: `data/source_article.json` (or fallback: `data/articles.json`)
- Snapshots: `results/ssr-results/{baseline,model,constrained}/ms_*.txt`

**Outputs to:** `results/analysis/ssr-production/`

### Local Analysis — CSR

```bash
python3 src/analysis/local/local_csr_analysis.py
```

**Inputs:**
- Ground truth: `data/source_article.json` (or fallback: `data/articles.json`)
- Snapshots: `results/local-csr/{baseline,model,constrained}/ms_*.txt`

**Outputs to:** `results/analysis/csr-local/`

### Local Analysis — SSR

```bash
python3 src/analysis/local/local_ssr_analysis.py
```

**Inputs:**
- Ground truth: `data/source_article.json` (or fallback: `data/articles.json`)
- Snapshots: `results/local-ssr/{baseline,model,constrained}/ms_*.txt`

**Outputs to:** `results/analysis/ssr-local/`

### TTSC (Time To Semantic Content) — Local

```bash
python3 src/analysis/local/analyze_ttsc.py
```

**Reads:** Timeseries HTML from `results/timeseries/csr_wait_*.txt`  
**Outputs to:** `results/analysis/csr-local/`
- `ttsc_cosine_similarity.png` — Similarity curve over time
- `ttsc_similarity_summary.csv` — Raw data

### SEO Analysis

```bash
python3 src/analysis/local/analyze-seo.py
```

Extracts structured semantic content from HTML files for SEO assessment.

## Complete Workflow — Fresh Start

To clear all results and run a complete fresh analysis:

```bash
# 1. Clear all existing captures and analysis
rm -rf results/csr-results/baseline/* results/csr-results/model/* results/csr-results/constrained/*
rm -rf results/ssr-results/baseline/* results/ssr-results/model/* results/ssr-results/constrained/*
rm -rf results/local-csr/baseline/* results/local-csr/model/* results/local-csr/constrained/*
rm -rf results/local-ssr/baseline/* results/local-ssr/model/* results/local-ssr/constrained/*
rm -rf results/analysis/csr-production/* results/analysis/ssr-production/* results/analysis/csr-local/* results/analysis/ssr-local/*

# 2. Run production indexing
npm run index:csr
npm run index:ssr

# 3. Run production analysis
python3 src/analysis/production-csr/production_analysis.py
python3 src/analysis/production-ssr/production_analysis.py

# 4. (Optional) Local dev testing
npm run dev &
npm run index:local-csr -- --wait-for-server
npm run index:local-ssr -- --wait-for-server
python3 src/analysis/local/local_csr_analysis.py
python3 src/analysis/local/local_ssr_analysis.py
```

## Key Metrics

### TTSC (Time To Semantic Content)

Measures when page content becomes semantically similar to ground truth (via cosine similarity of embeddings). Threshold: **0.5** by default (configurable via `--threshold`).

### Scenarios Measured

1. **Baseline** — Full resources, JavaScript, desktop viewport
   - Establishes upper-bound rendering speed
2. **Model** — Mobile viewport, network throttling, Googlebot UA
   - Simulates AI crawler conditions
3. **Constrained** — No JavaScript
   - Tests pure HTML availability (SSR advantage)

## Technical Details

### Capture Tool Stack

- **Puppeteer** — Headless browser automation
- **CDP (Chrome DevTools Protocol)** — Network throttling and JS control
- **Next.js** — Framework for both CSR and SSR pages

### Analysis Tool Stack

- **SentenceTransformers** (`all-MiniLM-L6-v2`) — Embeddings for similarity
- **BeautifulSoup** — HTML parsing and content extraction
- **Pandas / Matplotlib** — CSV output and charting

### Similarity Computation

Cosine similarity between:
- **Ground truth vector** — Embedded text from `source_article.json`
- **Page vector** — Embedded text extracted from each snapshot

Score ranges from 0 (completely different) to 1 (identical).

## Implementation Details

### Rendering Architecture

#### Client-Side Rendering (CSR) — `/csr-version`

**File:** `src/pages/csr-version.js`

The CSR implementation uses React hooks to defer content loading:

1. **Initial HTML Response:** Sends a minimal shell with `<div id="__next">Loading...</div>` placeholder
2. **Hydration:** React mounts and runs `useEffect`
3. **Async Data Fetch:** Calls `GET /api/get-article` to fetch article JSON
4. **Re-render:** Updates state with `setArticle(payload.article)`, rendering full content

**Timing behavior:**
- **DOM Content Loaded:** ~50–100ms (empty shell)
- **API Call Latency:** Network RTT + backend processing
- **Content Visible:** Post-hydration render (total: 50ms + latency)

**For production (Vercel):** API latency is ~100–200ms, so full content appears ~150–300ms after initial request.

**For localhost:** API is on the same machine (~1–2ms), so full content appears ~50ms after load.

#### Server-Side Rendering (SSR) — `/ssr-version`

**File:** `src/pages/ssr-version.js`

The SSR implementation uses Next.js `getServerSideProps` to pre-render:

1. **Server Request:** Incoming request to `/ssr-version`
2. **Data Fetch:** `getServerSideProps` calls `readFile('data/articles.json')` synchronously
3. **HTML Generation:** Next.js renders `<ArticleContent article={payload} />` with data embedded
4. **HTML Response:** Full page HTML sent to client with all article content in initial payload
5. **Hydration:** React hydrates in-place (no re-render needed)

**Timing behavior:**
- **DOM Content Loaded:** Full content immediately available
- **Hydration:** Minimal re-render (interactive after ~50–100ms)

#### Data Source

**File:** `src/pages/api/get-article.js` and `data/articles.json`

Both CSR and SSR read from `data/articles.json`:

```javascript
{
   "article": {
      "title": "How Rendering Strategy Shapes AI Search Visibility",
      "summary": "An evidence-oriented article comparing how server-side and client-side rendering influence what AI-driven crawlers can discover, parse, and cite.",
      "sections": [
         {
            "heading": "Why this comparison matters now",
            "paragraphs": ["...", "..."],
            "list": ["...", "..."]
         },
         // ... more sections
      ]
   }
}
```

The same content structure is used in both rendering strategies to isolate rendering as the independent variable.

### Capture Implementation

#### Scenario Configuration

**File:** `src/indexing/deployment-capture.ts`

Each capture runs three scenarios defined in `SCENARIOS`:

```typescript
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
            latency: MODEL_NETWORK_LATENCY_MS,  // default: 200ms
            downloadThroughput: MODEL_THROUGHPUT_BPS,  // 50 Mbps
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
```

**Scenarios explain:**

1. **Baseline** — Measures best-case CSR performance with full resources
2. **Model** — Simulates Googlebot with throttling; captures mobile rendering with network delays
3. **Constrained** — Disables JavaScript; shows what content is immediately available in HTML (pure SSR advantage)

#### Time-Series Capture

**Function:** `runDeploymentCapture()` in `deployment-capture.ts`

For each scenario, captures are taken at intervals: 0, 20, 40, …, 1000ms (default: 51 snapshots per scenario).

```typescript
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
```

For each time point:
1. Puppeteer navigates to URL with `waitUntil: 'domcontentloaded'`
2. Waits for specified milliseconds (allowing async hydration/rendering)
3. Calls `page.content()` to capture full HTML
4. Saves as `ms_<interval>.txt`

This allows measurement of when semantic content becomes available over time.

### Analysis Implementation

#### Text Extraction

**Function:** `extract_clean_text_from_html()` in analysis scripts

Removes noise to isolate article content:

```python
def extract_clean_text_from_html(html: str) -> str:
      """Remove script/style/nav noise, then take article/main text when possible."""
      soup = BeautifulSoup(html, "html.parser")
      for tag in soup(["script", "style", "nav"]):
            tag.decompose()

      main_content = soup.find("article") or soup.find("main")
      if main_content:
            text = main_content.get_text(separator=" ")
      else:
            text = soup.get_text(separator=" ")

      return " ".join(text.split())
```

**Strategy:**
- Removes `<script>`, `<style>`, `<nav>` tags (inline JS/CSS and navigation)
- Prefers `<article>` or `<main>` tags for content extraction
- Falls back to full page text if semantic tags are missing
- Normalizes whitespace to single spaces

#### Semantic Similarity Measurement

**Function:** `run_ttsc_analysis()` in analysis scripts

For each snapshot, computes cosine similarity to ground truth:

```python
def run_ttsc_analysis(...):
      gt_path = resolve_ground_truth_path(ground_truth_path)
      ground_truth_text = load_ground_truth_text(gt_path)

      model = SentenceTransformer(MODEL_NAME)  # 'all-MiniLM-L6-v2'
      gt_vec = model.encode(ground_truth_text, convert_to_tensor=True)

      for interval_ms, path in pairs:
            html = path.read_text(encoding="utf-8", errors="replace")
            text = extract_clean_text_from_html(html)
            doc_vec = model.encode(text, convert_to_tensor=True)
            sim = float(util.cos_sim(gt_vec, doc_vec).item())
            status = "Pass" if sim > threshold else "Fail"
            intervals.append((interval_ms, sim))
```

**Model:** `all-MiniLM-L6-v2` (384-dimensional embeddings)
- **Why:** Fast inference (~1ms per document), reliable for semantic similarity, compact
- **Seed:** Set to 42 for reproducibility

**Similarity Threshold:** 0.5 (default)
- Scores ≥ 0.5 → "TTSC reached" (content is substantially similar to source)
- Scores < 0.5 → "Not ready" (content still missing or incomplete)

#### TTSC (Time To Semantic Content) Computation

**Definition:**

TTSC is the **first time point where similarity exceeds the threshold**, measured in milliseconds.

**Example output:**

| Scenario | TTSC (ms) |
|---|---|
| baseline (CSR) | 180 |
| baseline (SSR) | 0 |
| model (CSR) | 280 |
| model (SSR) | 0 |
| constrained (CSR) | — (never ≥ 0.5) |
| constrained (SSR) | 0 |

**Interpretation:**
- **0ms:** Content available immediately (SSR strength)
- **>0ms:** Content delayed by hydration/rendering (CSR cost)
- **Never:** Content unavailable without JavaScript (constrained penalty for CSR)

#### CSV Output

**Format:** `*_metrics_summary.csv`

```csv
Scenario,Interval (ms),Similarity,Status
baseline,0,0.32,Fail
baseline,20,0.45,Fail
baseline,40,0.52,Pass
...
model,0,0.30,Fail
model,20,0.41,Fail
model,40,0.48,Fail
model,60,0.51,Pass
...
constrained,0,0.08,Fail
constrained,20,0.08,Fail
...
```

#### Visualization

**Output:** `*_ttsc_*.png` charts

Plots similarity vs. time for each scenario:
- X-axis: Interval (milliseconds)
- Y-axis: Cosine similarity (0–1)
- Horizontal line at threshold (0.5) marks TTSC boundary
- Curves show rendering progression

**Key visual patterns:**
- **SSR:** Flat horizontal line at ~1.0 (instant complete content)
- **CSR baseline:** Steep rise ~100–200ms, then plateaus
- **CSR model:** Steeper rise ~200–400ms (throttled network delays hydration)
- **CSR constrained:** Flat near 0 (no JS = no hydration)

## Experimental Methodology

### Variables

**Independent Variable:** Rendering strategy (CSR vs SSR)

**Control Variables (held constant):**
- Article content and structure (identical JSON)
- DOM hierarchy and semantic markup
- CSS styling (visual only, no layout changes)
- Deployment infrastructure (same Vercel instance)
- Capture methodology (Puppeteer + CDP)

**Dependent Variables (measured):**
- TTSC per scenario (time to semantic readiness)
- Similarity curve shape (how quickly content stabilizes)
- Availability in constrained mode (JS-disabled snapshot)

### Capture Strategy

**Why time-series?**
- Single snapshot cannot show rendering progression
- Different crawlers wait different amounts of time
- Time-series reveals when content "settles" (becomes semantically stable)

**Why three scenarios?**
- **Baseline:** Measures intrinsic rendering speed
- **Model:** Simulates realistic crawler conditions (throttled, mobile)
- **Constrained:** Tests static HTML availability (SSR's inherent advantage)

### Statistical Approach

**TTSC Metric:** Simple threshold crossing
- **Reproducible:** Same snapshots → same TTSC (deterministic)
- **Interpretable:** "When is content ready?" is a business-relevant question
- **Threshold choice:** 0.5 balances sensitivity (catch early completeness) with specificity (avoid false positives from partial content)

**No averaging across runs:** Production captures are performed once per condition (not repeated). Local captures can be repeated for sanity checks.

## Limitations and Considerations

### Known Limitations

1. **Single article:** Experiment uses one article; findings may not generalize to other content types
2. **Similarity metric:**  Cosine distance is rough proxy for "crawler readiness"; doesn't capture actual extraction accuracy
3. **Crawler variance:** Real AI crawlers vary in rendering support, caching, and scheduling; `model` scenario is simplified approximation
4. **Local vs production:** Local dev server has no real latency; use production for timing conclusions
5. **Deterministic rendering:** Next.js/React produce consistent DOM; real-world dynamic content may vary

### Future Extensions

1. **Multiple articles:** Repeat experiment across different content types, lengths, and structures
2. **Multiple crawlers:** Capture with different headless browsers (Playwright, Puppeteer, native Chrome)
3. **API latency variation:** Test with different backend response times (50ms, 200ms, 500ms, 1000ms)
4. **Real crawler data:** Compare against actual search engine indexing logs if available
5. **Rendering metrics:** Add Core Web Vitals, LCP (Largest Contentful Paint), interaction time

## Reproducibility

### Environment Specifications

- **Node.js:** 20+ (required for `--env-file` flag)
- **Python:** 3.9+
- **Next.js:** 16.2.1
- **Puppeteer:** 24.40.0
- **SentenceTransformers:** Latest via pip

### Data Sources

- Ground truth article: `data/source_article.json`
- Fallback article (if source missing): `data/articles.json`
- Article content is deterministic (same JSON = same embeddings)

### Deployment Requirements

- **CSR deployment:** Must be accessible at `CAPTURE_CSR_URL` (e.g., Vercel with CSR bundle)
- **SSR deployment:** Must be accessible at `CAPTURE_SSR_URL` (e.g., Vercel with SSR bundle)
- Both must serve identical article content

### Replication Steps

1. Clone repository
2. Set `CAPTURE_CSR_URL` and `CAPTURE_SSR_URL` in `.env.local`
3. Verify both deployments are live
4. Run `npm run index:csr && npm run index:ssr`
5. Run `python3 src/analysis/production-csr/production_analysis.py && python3 src/analysis/production-ssr/production_analysis.py`
6. Compare outputs in `results/analysis/{csr,ssr}-production/`

**Expected outcome:** CSR shows increasing similarity over time; SSR shows near-instant availability.

## Notes

- **Local captures lack network delay:** Use production URLs for timing experiments.
- **API calls are analyzed server-side:** Check `src/pages/api/get-article.js` for the data source.
- **Both deployments must be up:** Use `--wait-for-server` if deploying fresh.
- **Analysis is deterministic:** Same snapshots will always produce the same metrics (model is seeded).

## Troubleshooting

### `npm run dev` fails

Check Node.js version (should be 20+) and npm dependencies:
```bash
npm install
npm run dev
```

### Capture commands hang

Ensure the URL is reachable:
```bash
curl -s https://your-url.vercel.app/csr-version | head -c 100
```

### Analysis shows "No snapshot .txt files"

Verify capture output exists:
```bash
ls results/csr-results/baseline/ | wc -l
# Should show 51+ files (for default 20ms steps over 1000ms)
```

### Python venv issues

Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # if it exists
```

Or let the analysis scripts auto-install via pip on first run.

---

**Last Updated:** May 10, 2026
