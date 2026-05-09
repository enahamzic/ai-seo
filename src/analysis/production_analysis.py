"""
Time to Semantic Clarity (TTSC) — deployment time-series (CSR and/or SSR).

Compares three scenarios — baseline, model, constrained — against ``source_article.json``
using SBERT (all-MiniLM-L6-v2) cosine similarity.

Dependencies::

    python3 -m pip install beautifulsoup4 sentence-transformers matplotlib seaborn

Run from project root::

    python3 src/analysis/production_analysis.py
    python3 src/analysis/production_analysis.py --capture-root results/ssr-results --prefix ssr

Input layout::

    results/csr-results/{baseline,model,constrained}/*.txt
    results/ssr-results/{baseline,model,constrained}/*.txt

Expected filenames: ``ms_<interval>.txt`` or legacy ``csr_wait_<n>ms.txt``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message=".*urllib3 v2 only supports OpenSSL.*",
)

import matplotlib.pyplot as plt
import seaborn as sns
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAPTURE_ROOT = PROJECT_ROOT / "results" / "csr-results"
DEFAULT_GROUND_TRUTH = PROJECT_ROOT / "data" / "source_article.json"
FALLBACK_GROUND_TRUTH = PROJECT_ROOT / "data" / "articles.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "analysis"
DEFAULT_FILE_PREFIX = "csr"

SCENARIOS: tuple[tuple[str, str], ...] = (
    ("baseline", "Baseline"),
    ("model", "Model"),
    ("constrained", "Constrained"),
)

MS_FILE_PATTERN = re.compile(r"^ms_(\d+)\.txt$", re.IGNORECASE)
CSR_WAIT_PATTERN = re.compile(r"csr_wait_(\d+)ms\.txt$", re.IGNORECASE)

MODEL_NAME = "all-MiniLM-L6-v2"
SEMANTIC_THRESHOLD = 0.5
X_AXIS_MAX_MS_CAP = 10_000

# Line styling: Baseline green, Model (mobile+latency) orange, Constrained red
SCENARIO_STYLE: dict[str, dict[str, object]] = {
    "baseline": {"label": "Baseline", "color": "#2ca02c"},
    "model": {"label": "Model", "color": "#ff7f0e"},
    "constrained": {"label": "Constrained", "color": "#d62728"},
}


@dataclass(frozen=True)
class IntervalRow:
    scenario_key: str
    scenario_label: str
    interval_ms: int
    similarity: float
    status: str


def load_ground_truth_text(json_path: Path) -> str:
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


def discover_interval_files(folder: Path) -> list[tuple[int, Path]]:
    """Sorted (interval_ms, path) for ``ms_*.txt`` or ``csr_wait_*ms.txt``."""
    pairs: list[tuple[int, Path]] = []
    if not folder.is_dir():
        return pairs

    for path in folder.iterdir():
        if not path.is_file():
            continue
        m = MS_FILE_PATTERN.match(path.name)
        if m:
            pairs.append((int(m.group(1)), path))
            continue
        m2 = CSR_WAIT_PATTERN.match(path.name)
        if m2:
            pairs.append((int(m2.group(1)), path))

    pairs.sort(key=lambda x: x[0])
    return pairs


def resolve_ground_truth_path(preferred: Path) -> Path:
    if preferred.is_file():
        return preferred
    if FALLBACK_GROUND_TRUTH.is_file():
        print(
            f"[ttsc] Ground truth not at {preferred}; using {FALLBACK_GROUND_TRUTH}",
        )
        return FALLBACK_GROUND_TRUTH
    raise FileNotFoundError(
        f"No ground-truth JSON at {preferred} or {FALLBACK_GROUND_TRUTH}",
    )


def first_ttsc_ms(intervals: list[tuple[int, float]], threshold: float) -> int | None:
    for ms, sim in intervals:
        if sim > threshold:
            return ms
    return None


def _ensure_capture_layout(capture_root: Path) -> None:
    capture_root.mkdir(parents=True, exist_ok=True)
    for folder_key, _ in SCENARIOS:
        (capture_root / folder_key).mkdir(parents=True, exist_ok=True)


def _snapshot_count(capture_root: Path) -> int:
    return sum(
        len(discover_interval_files(capture_root / folder_key))
        for folder_key, _ in SCENARIOS
    )


def _abort_if_no_snapshots(capture_root: Path, file_prefix: str) -> None:
    n = _snapshot_count(capture_root)
    if n > 0:
        return
    print(f"[{file_prefix}] ERROR: No snapshot .txt files under {capture_root}/")
    print("  Expected subfolders: baseline/, model/, constrained/")
    print("  Run: npm run index:csr   or   npm run index:ssr")
    print("  Then: python3 src/analysis/production_analysis.py --capture-root … --prefix …")
    sys.exit(1)


def run_ttsc_analysis(
    capture_root: Path,
    ground_truth_path: Path,
    output_dir: Path,
    threshold: float,
    file_prefix: str,
    plot_title_tag: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _ensure_capture_layout(capture_root)
    _abort_if_no_snapshots(capture_root, file_prefix)

    gt_path = resolve_ground_truth_path(ground_truth_path)
    ground_truth_text = load_ground_truth_text(gt_path)

    print(f"[{file_prefix}] Loading {MODEL_NAME!r} …")
    model = SentenceTransformer(MODEL_NAME)
    gt_vec = model.encode(ground_truth_text, convert_to_tensor=True)

    all_rows: list[IntervalRow] = []
    series: dict[str, list[tuple[int, float]]] = {}

    for folder_key, label in SCENARIOS:
        sub = production_root / folder_key
        pairs = discover_interval_files(sub)
        if not pairs:
            print(
                f"[{file_prefix}] WARN: no snapshots in {sub} "
                f"(add ms_<interval>.txt or csr_wait_*ms.txt)",
            )
            series[folder_key] = []
            continue

        intervals: list[tuple[int, float]] = []
        for interval_ms, path in pairs:
            html = path.read_text(encoding="utf-8", errors="replace")
            text = extract_clean_text_from_html(html)
            doc_vec = model.encode(text, convert_to_tensor=True)
            sim = float(util.cos_sim(gt_vec, doc_vec).item())
            status = "Pass" if sim > threshold else "Fail"
            intervals.append((interval_ms, sim))
            all_rows.append(
                IntervalRow(
                    scenario_key=folder_key,
                    scenario_label=label,
                    interval_ms=interval_ms,
                    similarity=sim,
                    status=status,
                ),
            )
            print(
                f"[{file_prefix}] {label:<20} {interval_ms:5d} ms → "
                f"similarity={sim:.4f} ({status})",
            )

        series[folder_key] = intervals

    csv_path = output_dir / f"{file_prefix}_metrics_summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "Scenario_Key",
                "Scenario_Label",
                "Interval_ms",
                "Similarity_Score",
                "Status",
                "Threshold",
            ],
        )
        for row in sorted(all_rows, key=lambda r: (r.scenario_key, r.interval_ms)):
            w.writerow(
                [
                    row.scenario_key,
                    row.scenario_label,
                    row.interval_ms,
                    f"{row.similarity:.6f}",
                    row.status,
                    f"{threshold}",
                ],
            )
        w.writerow([])
        w.writerow(["# Summary: TTSC = first interval_ms with Similarity_Score > Threshold"])
        w.writerow(["Scenario_Label", "TTSC_ms", "Threshold_Crossed"])
        for folder_key, label in SCENARIOS:
            ttsc = first_ttsc_ms(series.get(folder_key, []), threshold)
            w.writerow(
                [
                    label,
                    ttsc if ttsc is not None else "not_reached",
                    "yes" if ttsc is not None else "no",
                ],
            )

    print(f"[{file_prefix}] Wrote {csv_path}")

    _print_visibility_gap_table(
        series, threshold, label_by_key=dict(SCENARIOS), run_label=file_prefix.upper()
    )
    _plot_per_scenario_charts(
        series, threshold, output_dir, file_prefix=file_prefix, plot_title_tag=plot_title_tag
    )


def _print_visibility_gap_table(
    series: dict[str, list[tuple[int, float]]],
    threshold: float,
    label_by_key: dict[str, str],
    run_label: str,
) -> None:
    """TTSC interprets visibility gap as time until semantic clarity (lower = faster)."""
    print()
    print(f"Visibility gap ({run_label}) — Time to Semantic Clarity (TTSC)")
    print(f"Threshold: cosine similarity > {threshold}")
    print("-" * 72)
    print(f"{'Scenario':<22} {'TTSC (ms)':<14} {'Crossed?':<10} {'Last sample (ms)'}")
    print("-" * 72)

    for key, _folder in SCENARIOS:
        label = label_by_key[key]
        pts = series.get(key, [])
        ttsc = first_ttsc_ms(pts, threshold)
        crossed = "yes" if ttsc is not None else "no"
        ttsc_str = str(ttsc) if ttsc is not None else "— (> window)"
        last_ms = pts[-1][0] if pts else "—"
        print(f"{label:<22} {ttsc_str:<14} {crossed:<10} {last_ms}")
    print("-" * 72)
    print(
        "Interpretation: larger TTSC ⇒ longer interval before text aligns with ground "
        "truth (wider visibility / semantic gap).",
    )
    print()


def _x_axis_upper_ms(series: dict[str, list[tuple[int, float]]]) -> int:
    """Upper x-limit in ms, capped and rounded up to a multiple of 50 for tick alignment."""
    max_ms_in_data = max((x for pts in series.values() for x, _ in pts), default=0)
    if max_ms_in_data == 0:
        return min(1000, X_AXIS_MAX_MS_CAP)
    raw = max(400, min(X_AXIS_MAX_MS_CAP, int(max_ms_in_data * 1.08 + 150)))
    return min(X_AXIS_MAX_MS_CAP, int(math.ceil(raw / 50) * 50))


def _set_xticks_every_50ms(ax: plt.Axes, x_upper: int) -> None:
    ticks = list(range(0, x_upper + 1, 50))
    ax.set_xticks(ticks)
    ax.set_xlim(0, x_upper)
    ax.tick_params(axis="x", labelsize=9)
    for label in ax.get_xticklabels():
        label.set_rotation(45)
        label.set_ha("right")


def _plot_per_scenario_charts(
    series: dict[str, list[tuple[int, float]]],
    threshold: float,
    output_dir: Path,
    file_prefix: str,
    plot_title_tag: str,
) -> None:
    """One PNG per scenario; x ticks every 50 ms."""
    sns.set_theme(style="whitegrid", context="talk")
    x_upper = _x_axis_upper_ms(series)

    for folder_key, _human_label in SCENARIOS:
        pts = series.get(folder_key, [])
        style = SCENARIO_STYLE[folder_key]
        out_path = output_dir / f"{file_prefix}_ttsc_{folder_key}.png"

        fig, ax = plt.subplots(figsize=(11, 6.5))

        if pts:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            ax.plot(
                xs,
                ys,
                color=str(style["color"]),
                linewidth=2.2,
                marker="o",
                markersize=5,
                label=str(style["label"]),
            )
            ttsc = first_ttsc_ms(pts, threshold)
            if ttsc is not None:
                y_at = next((y for x, y in pts if x == ttsc), None)
                if y_at is not None:
                    ax.scatter(
                        [ttsc],
                        [y_at],
                        s=130,
                        c=str(style["color"]),
                        edgecolors="black",
                        zorder=5,
                    )
                    ax.annotate(
                        f"TTSC ≈ {ttsc} ms\n(similarity = {y_at:.3f})",
                        xy=(ttsc, y_at),
                        xytext=(
                            min(ttsc + 120, x_upper - 60),
                            min(0.92, max(0.18, y_at + 0.1)),
                        ),
                        fontsize=10,
                        arrowprops=dict(arrowstyle="->", color="0.35"),
                    )
        else:
            ax.text(
                0.5,
                0.5,
                "No snapshot data for this scenario",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=12,
                color="0.45",
            )

        ax.axhline(
            threshold,
            color="#7f7f7f",
            linestyle="--",
            linewidth=1.5,
            label=f"Failure threshold ({threshold})",
        )

        _set_xticks_every_50ms(ax, x_upper)
        ax.set_ylim(0, 1.02)
        ax.set_xlabel("Time (ms)")
        ax.set_ylabel("SBERT cosine similarity")
        ax.set_title(f"{plot_title_tag} TTSC — {style['label']}")
        ax.legend(loc="lower right")

        fig.tight_layout()
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"[{file_prefix}] Wrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TTSC analysis for deployment captures (csr-results or ssr-results).",
    )
    parser.add_argument(
        "--capture-root",
        type=Path,
        default=DEFAULT_CAPTURE_ROOT,
        help="Folder containing baseline/, model/, constrained/ (default: results/csr-results)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=DEFAULT_FILE_PREFIX,
        help="Output file prefix, e.g. csr or ssr (default: csr)",
    )
    parser.add_argument(
        "--plot-title-tag",
        type=str,
        default="",
        help="Chart title prefix (default: uppercased --prefix)",
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=DEFAULT_GROUND_TRUTH,
        help="Path to source_article.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for CSV and PNG",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=SEMANTIC_THRESHOLD,
        help="TTSC when similarity first exceeds this value (default 0.5)",
    )
    args = parser.parse_args()

    file_prefix = args.prefix.strip().lower().replace(" ", "_")
    if not file_prefix:
        file_prefix = DEFAULT_FILE_PREFIX
    plot_title_tag = (args.plot_title_tag.strip() or file_prefix.upper())

    run_ttsc_analysis(
        capture_root=args.capture_root.resolve(),
        ground_truth_path=args.ground_truth.resolve(),
        output_dir=args.output_dir.resolve(),
        threshold=args.threshold,
        file_prefix=file_prefix,
        plot_title_tag=plot_title_tag,
    )


if __name__ == "__main__":
    main()
