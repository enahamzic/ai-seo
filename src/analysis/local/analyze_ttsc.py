"""
Time to Semantic Clarity (TTSC) — batch analysis for CSR HTML time-series artifacts.

Compares each captured DOM snapshot (e.g. 20 ms steps in ``test-rendering.ts``) to a ground-truth article using
Sentence-BERT (all-MiniLM-L6-v2, 384-dim) and cosine similarity.

Dependencies (install once, ideally in a venv):

    pip install beautifulsoup4 sentence-transformers matplotlib seaborn

Run from the thesis project root:

    python src/analysis/analyze_ttsc.py

Optional arguments: see ``main()`` / ``argparse`` block at the bottom.

The time-series captures should use ``waitUntil: 'domcontentloaded'`` in Puppeteer (see
``test-rendering.ts``). If you use ``networkidle0`` instead, the CSR page's API call is
already finished before the timer starts, so every snapshot is identical and similarity
is flat near 1.0.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util

# Default paths relative to project root (parent of ``src/``)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIMESERIES_DIR = PROJECT_ROOT / "results" / "timeseries"
DEFAULT_GROUND_TRUTH = PROJECT_ROOT / "data" / "source_article.json"
FALLBACK_GROUND_TRUTH = PROJECT_ROOT / "data" / "articles.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "analysis" / "csr-local"

CSR_WAIT_PATTERN = re.compile(r"csr_wait_(\d+)ms\.txt$", re.IGNORECASE)
MODEL_NAME = "all-MiniLM-L6-v2"
SEMANTIC_THRESHOLD = 0.5


@dataclass(frozen=True)
class IntervalRecord:
    interval_ms: int
    similarity: float
    status: str  # "Pass" if similarity >= threshold else "Fail"


def load_ground_truth_text(json_path: Path) -> str:
    """
    Build a single string from the thesis article JSON (ground truth).

    Expects the same shape as ``data/articles.json``:
    ``article.title``, ``article.summary``, ``article.sections[].paragraphs``,
    and optional ``sections[].list`` items.
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    article = data.get("article", data)
    title = article.get("title", "") or ""
    summary = article.get("summary", "") or ""
    body_parts: list[str] = []

    for section in article.get("sections", []) or []:
        body_parts.extend(p for p in section.get("paragraphs", []) or [] if p)
        body_parts.extend(str(item) for item in section.get("list", []) or [] if item)

    return " ".join(" ".join([title, summary, *body_parts]).split())


def extract_clean_text_from_html(html: str) -> str:
    """
    Strip boilerplate tags, then extract human-readable text.

    Removes ``<script>``, ``<style>``, and ``<nav>`` (per thesis protocol),
    then prefers ``<article>`` or ``<main>`` if present (CSR shells often lack them).
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav"]):
        tag.decompose()

    main_content = soup.find("article") or soup.find("main")
    if main_content:
        text = main_content.get_text(separator=" ")
    else:
        text = soup.get_text(separator=" ")

    return " ".join(text.split())


def discover_interval_files(timeseries_dir: Path) -> list[tuple[int, Path]]:
    """Return sorted (interval_ms, path) pairs for ``csr_wait_{ms}ms.txt`` files."""
    pairs: list[tuple[int, Path]] = []
    if not timeseries_dir.is_dir():
        return pairs

    for path in sorted(timeseries_dir.glob("csr_wait_*ms.txt")):
        m = CSR_WAIT_PATTERN.match(path.name)
        if m:
            pairs.append((int(m.group(1)), path))

    pairs.sort(key=lambda x: x[0])
    return pairs


def resolve_ground_truth_path(preferred: Path) -> Path:
    if preferred.is_file():
        return preferred
    if FALLBACK_GROUND_TRUTH.is_file():
        print(
            f"[ttsc] Ground-truth file not found at {preferred}; "
            f"using {FALLBACK_GROUND_TRUTH}"
        )
        return FALLBACK_GROUND_TRUTH
    raise FileNotFoundError(
        f"No ground-truth JSON found. Expected {preferred} "
        f"or {FALLBACK_GROUND_TRUTH}"
    )


def compute_ttsc(records: list[IntervalRecord], threshold: float) -> int | None:
    """
    First interval (ms) where cosine similarity is at or above ``threshold``.

    If no interval reaches the threshold, returns ``None``.
    """
    for r in records:
        if r.similarity >= threshold:
            return r.interval_ms
    return None


def run_ttsc_analysis(
    timeseries_dir: Path,
    ground_truth_path: Path,
    output_dir: Path,
    threshold: float = SEMANTIC_THRESHOLD,
) -> tuple[list[IntervalRecord], int | None]:
    output_dir.mkdir(parents=True, exist_ok=True)

    gt_path = resolve_ground_truth_path(ground_truth_path)
    ground_truth_text = load_ground_truth_text(gt_path)

    pairs = discover_interval_files(timeseries_dir)
    if not pairs:
        raise FileNotFoundError(
            f"No csr_wait_*ms.txt files under {timeseries_dir}. "
            "Run the Puppeteer capture script first."
        )

    print(f"[ttsc] Loading model {MODEL_NAME!r} …")
    model = SentenceTransformer(MODEL_NAME)

    gt_vec = model.encode(ground_truth_text, convert_to_tensor=True)

    records: list[IntervalRecord] = []
    for interval_ms, path in pairs:
        html = path.read_text(encoding="utf-8", errors="replace")
        text = extract_clean_text_from_html(html)
        doc_vec = model.encode(text, convert_to_tensor=True)
        sim = float(util.cos_sim(gt_vec, doc_vec).item())
        status = "Pass" if sim >= threshold else "Fail"
        records.append(
            IntervalRecord(interval_ms=interval_ms, similarity=sim, status=status)
        )
        print(f"[ttsc] {interval_ms:5d} ms → cosine = {sim:.4f} ({status})")

    ttsc_ms = compute_ttsc(records, threshold)

    csv_path = output_dir / "ttsc_similarity_summary.csv"
    _write_csv(csv_path, records)
    print(f"[ttsc] Wrote {csv_path}")

    plot_path = output_dir / "ttsc_cosine_similarity.png"
    _plot_similarity(records, ttsc_ms, threshold, plot_path)
    print(f"[ttsc] Wrote {plot_path}")

    if ttsc_ms is None:
        print(
            f"[ttsc] TTSC: not reached — no interval had similarity ≥ {threshold} "
            f"within {records[-1].interval_ms} ms."
        )
    else:
        ttsc_score = next(r.similarity for r in records if r.interval_ms == ttsc_ms)
        print(
            f"[ttsc] TTSC ≈ {ttsc_ms} ms "
            f"(first interval with similarity ≥ {threshold}; score {ttsc_score:.4f})"
        )

    return records, ttsc_ms


def _write_csv(path: Path, records: list[IntervalRecord]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Interval", "Similarity_Score", "Status"])
        for r in records:
            w.writerow([r.interval_ms, f"{r.similarity:.6f}", r.status])


def _plot_similarity(
    records: list[IntervalRecord],
    ttsc_ms: int | None,
    threshold: float,
    out_path: Path,
) -> None:
    sns.set_theme(style="whitegrid", context="talk")
    fig, ax = plt.subplots(figsize=(11, 6))

    xs = [r.interval_ms for r in records]
    ys = [r.similarity for r in records]

    ax.plot(xs, ys, color="#2c7bb6", linewidth=2.2, marker="o", markersize=6)
    ax.axhline(
        threshold,
        color="#d7191c",
        linestyle="--",
        linewidth=1.5,
        label=f"Semantic threshold ({threshold})",
    )

    ax.set_xlabel("Extra wait after domcontentloaded (ms)")
    ax.set_ylabel("Cosine similarity to ground truth")
    ax.set_title("CSR visibility gap — similarity vs. time (post–DOMContentLoaded)")
    ax.set_xlim(min(xs) - 100, max(xs) + 100)
    ax.set_ylim(0, 1.02)
    ax.legend(loc="lower right")

    if ttsc_ms is not None:
        ttsc_y = next(r.similarity for r in records if r.interval_ms == ttsc_ms)
        ax.scatter([ttsc_ms], [ttsc_y], s=140, c="#fdae61", edgecolors="black", zorder=5)
        ax.annotate(
            f"TTSC ≈ {ttsc_ms} ms\n(similarity = {ttsc_y:.3f})",
            xy=(ttsc_ms, ttsc_y),
            xytext=(ttsc_ms + 350, ttsc_y - 0.12),
            textcoords="data",
            arrowprops=dict(arrowstyle="->", color="0.3"),
            fontsize=11,
        )
    else:
        ax.text(
            0.02,
            0.08,
            "TTSC: threshold not reached in this window",
            transform=ax.transAxes,
            fontsize=11,
            color="#d7191c",
        )

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="TTSC analysis for CSR HTML time-series.")
    parser.add_argument(
        "--timeseries-dir",
        type=Path,
        default=DEFAULT_TIMESERIES_DIR,
        help="Directory with csr_wait_*ms.txt files",
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=DEFAULT_GROUND_TRUTH,
        help="Ground-truth JSON (defaults to data/source_article.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Where to write CSV and PNG",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=SEMANTIC_THRESHOLD,
        help="Cosine similarity threshold for TTSC and Pass/Fail (default 0.5)",
    )
    args = parser.parse_args()

    run_ttsc_analysis(
        timeseries_dir=args.timeseries_dir.resolve(),
        ground_truth_path=args.ground_truth.resolve(),
        output_dir=args.output_dir.resolve(),
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
